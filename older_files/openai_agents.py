from openai import OpenAI
from pydantic import BaseModel
from typing import Type, TypeVar, Optional, Union, Dict, Any, Callable, List
# Tools and function calling utilities
import inspect
import json
import subprocess
import sys

T = TypeVar('T', bound=BaseModel)

class StructuredOutputAgent:
    """
    OpenAI agent that generates structured outputs using Pydantic schemas.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the agent with OpenAI client.
        
        Args:
            api_key: OpenAI API key. If None, will use environment variable.
        """
        print(api_key)
        self.client = OpenAI(api_key=api_key)
    
    def chat(
        self, 
        message: str, 
        schema: Type[T], 
        model: str = "gpt-4.1-mini",
        system_prompt: Optional[str] = None,
        temperature: float = 0.0
    ) -> Union[Dict[str, Any], str]:
        """
        Generate a structured response using the provided Pydantic schema.
        
        Args:
            message: User message to send to the model
            schema: Pydantic model class defining the expected response structure
            model: OpenAI model to use (default: gpt-4o-2024-08-06)
            system_prompt: Optional system prompt to set context
            temperature: Temperature for response generation (default: 0.0)
            
        Returns:
            Python dictionary if successful, or refusal string if refused
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": message})
        
        try:
            completion = self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=schema,
                temperature=temperature
            )
            
            # Check for refusal
            if completion.choices[0].message.refusal:
                return completion.choices[0].message.refusal
            
            # Return parsed structured output as dictionary
            return completion.choices[0].message.parsed.model_dump()
            
        except Exception as e:
            raise Exception(f"Error generating structured output: {str(e)}")


class ToolAgent:
    """
    OpenAI agent that executes tool calls using the OpenAI function calling API.
    """

    def __init__(
        self,
        tools: List[Callable],
        api_key: Optional[str] = None,
        model: str = "gpt-4.1-mini",
        temperature: float = 0.0,
    ):
        """
        Initialize the agent with OpenAI client and provided tools.

        Args:
            tools: List of callable functions to expose as tools.
            api_key: OpenAI API key. If None, will use environment variable.
            model: OpenAI model to use for function calling.
            temperature: Sampling temperature for the model.
        """
        self.client = OpenAI(api_key=api_key)
        self.tools = tools
        self.model = model
        self.temperature = temperature
        self.tool_schemas = self._generate_tool_schemas()

    def _generate_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Generate function schemas from provided tool functions based on their
        signature and docstring, using JSON Schema for parameters.
        """
        schemas: List[Dict[str, Any]] = []
        for tool in self.tools:
            name = tool.__name__
            description = inspect.getdoc(tool) or ""
            sig = inspect.signature(tool)
            properties: Dict[str, Any] = {}
            required: List[str] = []
            for param_name, param in sig.parameters.items():
                annotation = param.annotation
                if annotation is int:
                    p_type = "integer"
                elif annotation is float:
                    p_type = "number"
                elif annotation is bool:
                    p_type = "boolean"
                elif annotation is list:
                    p_type = "array"
                else:
                    p_type = "string"
                properties[param_name] = {"type": p_type, "description": param_name}
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)
            schemas.append({
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            })
        return schemas

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute the tool function by name with the given arguments.
        """
        for tool in self.tools:
            if tool.__name__ == name:
                try:
                    return tool(**arguments)
                except Exception as e:
                    return f"Error executing tool {name}: {e}"
        return f"Tool {name} not found"

    def run(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a prompt to the model, allow it to call tools, execute those calls,
        and return a mapping of tool names to their outputs as JSON.
        """
        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        tool_outputs: Dict[str, Any] = {}

        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=self.tool_schemas,
                function_call="auto",
                temperature=self.temperature,
            )
            message = response.choices[0].message
            if not getattr(message, "function_call", None):
                break
            name = message.function_call.name
            args_str = message.function_call.arguments
            try:
                arguments = json.loads(args_str)
            except json.JSONDecodeError:
                arguments = {}
            result = self._execute_tool(name, arguments)
            tool_outputs[name] = result
            messages.append(message)
            messages.append({"role": "function", "name": name, "content": json.dumps(result)})

        return tool_outputs


# -----------------------------------------------------------------------------
# Python execution tool for dynamic code execution
# -----------------------------------------------------------------------------
def python_execution_tool(code: str) -> str:
    """
    Executes arbitrary Python code in a subprocess and returns its stdout and stderr.

    Args:
        code: A string of Python code to execute.

    Returns:
        Combined stdout and stderr output from running the code.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        output = result.stdout or ""
        if result.stderr:
            output += "\n" + result.stderr
        return output.strip()
    except Exception as e:
        return f"Error running python code: {e}"


# -----------------------------------------------------------------------------
# ReAct (Reasoning and Acting) agent definitions
# -----------------------------------------------------------------------------
class ReActStep(BaseModel):
    thought: str
    action: Optional[str]
    action_input: Optional[Dict[str, Any]]


class ReActFinish(BaseModel):
    final_answer: str


class OpenAIReActAgent:
    """
    Implements a ReAct (Reasoning and Acting) agent using StructuredOutputAgent
    for reasoning steps and ToolAgent for executing actions/functions.
    """

    def __init__(
        self,
        tools: List[Callable],
        api_key: Optional[str] = None,
        model: str = "gpt-4.1-mini",
        temperature: float = 0.0,
    ):
        """
        Initialize the ReAct agent with the given tools and OpenAI configuration.

        Args:
            tools: List of Python callables exposed as tools.
            api_key: OpenAI API key (uses env var if None).
            model: OpenAI model name for both reasoning and function calling.
            temperature: Sampling temperature for LLM responses.
        """
        # Core agents
        self.structured = StructuredOutputAgent(api_key=api_key)
        self.tool_agent = ToolAgent(
            tools=tools + [python_execution_tool],
            api_key=api_key,
            model=model,
            temperature=temperature,
        )
        # Schemas for parsing LLM outputs
        self._step_schema = ReActStep
        self._finish_schema = ReActFinish

    def run(
        self,
        prompt: str,
        iterations: int,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the ReAct loop for a fixed number of iterations, performing
        reasoning and actions (tool calls) at each step, then returning a
        trace of steps along with the final answer.

        Args:
            prompt: Initial user question or task description.
            iterations: Number of reasoning-action cycles to run.
            system_prompt: Optional system-level prompt for context.

        Returns:
            A dict with 'trace' (list of steps) and 'final_answer'.
        """
        trace: List[Dict[str, Any]] = []

        # Run the ReAct loop
        for i in range(iterations):
            # Build context from trace
            trace_text = ""
            for step in trace:
                trace_text += (
                    f"Thought: {step['thought']}\n"
                    f"Action: {step['action']}\n"
                    f"Observation: {step['observation']}\n\n"
                )

            # Ask the LLM for next thought/action
            message = (
                prompt
                + "\n\n"
                + trace_text
                + "Based on the above, provide the next 'thought', 'action',"
                + " and 'action_input' in JSON format."
            )
            output = self.structured.chat(
                message=message,
                schema=self._step_schema,
                system_prompt=system_prompt,
            )

            thought = output.get("thought")
            action = output.get("action")
            action_input = output.get("action_input") or {}

            # Execute the selected tool/action
            observation = None
            if action:
                observation = self.tool_agent._execute_tool(action, action_input)

            # Record the step
            trace.append({
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": observation,
            })

        # After iterations, ask for the final answer
        trace_text = ""
        for step in trace:
            trace_text += (
                f"Thought: {step['thought']}\n"
                f"Action: {step['action']}\n"
                f"Observation: {step['observation']}\n\n"
            )

        final_message = (
            prompt
            + "\n\n"
            + trace_text
            + "Based on the above reasoning and observations, provide the 'final_answer' in JSON format."
        )
        final_output = self.structured.chat(
            message=final_message,
            schema=self._finish_schema,
            system_prompt=system_prompt,
        )

        return {"trace": trace, "final_answer": final_output.get("final_answer")}
