import os, json, inspect
from typing import List, Callable, Optional, Any, Dict
from dotenv import load_dotenv
from pydantic import BaseModel
from groq import Groq

load_dotenv()

class GroqAgent:
    """
    A simple agent for interacting with Groq API with tool support and structured output.
    """
    def __init__(
        self,
        model_name: str = "llama-3.3-70b-versatile",
        tools: List[Callable] = [],
        output_schema: Optional[BaseModel] = None,
    ):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key)
        self.model_name = model_name
        self.tools = tools
        self.output_schema = output_schema
        self.tool_schemas = self._generate_tool_schemas()
        self.conversation_history = []  # Store conversation history

    def _generate_tool_schemas(self) -> List[Dict[str, Any]]:
        schemas = []
        for tool in self.tools:
            sig = inspect.signature(tool)
            doc = inspect.getdoc(tool) or ""
            schema = {
                "type": "function",
                "function": {
                    "name": tool.__name__,
                    "description": doc.splitlines()[0] if doc else f"Function {tool.__name__}",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }
            for name, param in sig.parameters.items():
                prop = {"type": "string", "description": f"Parameter {name}"}
                if param.annotation == int: prop["type"] = "integer"
                elif param.annotation == float: prop["type"] = "number"
                elif param.annotation == bool: prop["type"] = "boolean"
                elif param.annotation == list: prop["type"] = "array"
                schema["function"]["parameters"]["properties"][name] = prop
                if param.default == inspect.Parameter.empty:
                    schema["function"]["parameters"]["required"].append(name)
            schemas.append(schema)
        return schemas

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        for tool in self.tools:
            if tool.__name__ == tool_name:
                try:
                    return tool(**arguments)
                except Exception as e:
                    return f"Error executing {tool_name}: {e}"
        return f"Tool {tool_name} not found"

    def invoke(self, prompt: str) -> Dict[str, Any]:
        messages = [{"role": "user", "content": prompt}]
        params = {"model": self.model_name, "messages": messages}
        if self.tool_schemas:
            params.update({"tools": self.tool_schemas, "tool_choice": "auto"})
        if self.output_schema:
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "schema": self.output_schema.model_json_schema()
                }
            }
        response = self.client.chat.completions.create(**params)

        result = {"message": response.choices[0].message.content, "tool_calls": [], "structured_output": None}
        calls = getattr(response.choices[0].message, "tool_calls", [])
        if calls:
            for call in calls:
                args = json.loads(call.function.arguments)
                res = self._execute_tool(call.function.name, args)
                result["tool_calls"].append({"tool": call.function.name, "arguments": args, "result": res})
            # follow-up for final response
            messages.append(response.choices[0].message)
            for call, entry in zip(calls, result["tool_calls"]):
                messages.append({
                    "role": "tool",
                    "content": str(entry["result"]),
                    "tool_call_id": call.id
                })
            follow = self.client.chat.completions.create(model=self.model_name, messages=messages)
            result["message"] = follow.choices[0].message.content

        if self.output_schema and result["message"]:
            try:
                result["structured_output"] = self.output_schema(**json.loads(result["message"]))
            except Exception as e:
                result["structured_output"] = f"Failed to parse structured output: {e}"

        return result

    def invoke_plus_next_call(
        self,
        first_prompt: str,
        second_prompt: str,
        overall_task_prompt: str
    ) -> Dict[str, Any]:
        first = self.invoke(first_prompt)
        first_out = first.get("tool_calls", first.get("message", ""))
        combined_input = (
            f"{overall_task_prompt}\n"
            f"<user>{first_prompt}</user>\n"
            f"<assistant>Output of first LLM Call: {first_out}</assistant>\n"
            f"<user>{second_prompt}</user>"
        )
        orig_schemas = self.tool_schemas
        self.tool_schemas = []
        second = self.invoke(combined_input)
        self.tool_schemas = orig_schemas

        return {
            "first_result": first,
            "second_result": second,
            "combined_input": combined_input,
            "final_message": second.get("message") if "error" not in second else second.get("error")
        }

    def invoke_plus_history(self, prompt: str, reset_history: bool = False) -> Dict[str, Any]:
        """
        Invoke the agent with conversation history tracking.
        
        Args:
            prompt: The user's input prompt
            reset_history: Whether to reset the conversation history before this call
            
        Returns:
            Dict containing the response with history maintained
        """
        if reset_history:
            self.conversation_history = []
            
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": prompt})
        
        # Prepare parameters with full conversation history
        params = {"model": self.model_name, "messages": self.conversation_history.copy()}
        if self.tool_schemas:
            params.update({"tools": self.tool_schemas, "tool_choice": "auto"})
        if self.output_schema:
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "schema": self.output_schema.model_json_schema()
                }
            }
        
        response = self.client.chat.completions.create(**params)
        
        result = {"message": response.choices[0].message.content, "tool_calls": [], "structured_output": None}
        
        # Handle tool calls
        calls = getattr(response.choices[0].message, "tool_calls", [])
        if calls:
            # Add assistant message with tool calls to history
            self.conversation_history.append(response.choices[0].message)
            
            for call in calls:
                args = json.loads(call.function.arguments)
                res = self._execute_tool(call.function.name, args)
                result["tool_calls"].append({"tool": call.function.name, "arguments": args, "result": res})
                
                # Add tool response to history
                self.conversation_history.append({
                    "role": "tool",
                    "content": str(res),
                    "tool_call_id": call.id
                })
            
            # Get follow-up response with updated history
            follow = self.client.chat.completions.create(model=self.model_name, messages=self.conversation_history)
            result["message"] = follow.choices[0].message.content
            
            # Add final assistant response to history
            self.conversation_history.append({"role": "assistant", "content": result["message"]})
        else:
            # Add assistant response to history for non-tool calls
            self.conversation_history.append({"role": "assistant", "content": result["message"]})

        # Handle structured output
        if self.output_schema and result["message"]:
            try:
                result["structured_output"] = self.output_schema(**json.loads(result["message"]))
            except Exception as e:
                result["structured_output"] = f"Failed to parse structured output: {e}"

        # Add history to result for debugging/inspection
        result["conversation_history"] = self.conversation_history.copy()
        
        return result

    def help(self):
        """
        Print usage examples for GroqAgent.
        """
        print("GroqAgent usage examples:")
        print("1) Instantiate the agent:")
        print("   agent = GroqAgent(model_name='llama-3.3-70b-versatile', tools=[...], output_schema=None)")
        print("2) Simple chat (invoke):")
        print("   result = agent.invoke('Hello, how are you?')")
        print("   print(result['message'])")
        print("3) Two-step workflow (invoke_plus_next_call):")
        print("   result = agent.invoke_plus_next_call(")
        print("       'First prompt', 'Second prompt', 'Overall task prompt')")
        print("""Here, the input to the LLM which produces the final output is: combined_input = (
            f"{overall_task_prompt}\n"
            f"<user>{first_prompt}</user>\n"
            f"<assistant>Output of first LLM Call: {first_out}</assistant>\n"
            f"<user>{second_prompt}</user>"
        )""")
        print("   print(result['final_message'])")
        print("4) Conversation with history (invoke_plus_history):")
        print("   result = agent.invoke_plus_history('Hello, who won the world series in 2020?')")
        print("   print(result['message'])")
        print("   result = agent.invoke_plus_history('Tell me more about him.', reset_history=False)")
        print("   print(result['message'])")




