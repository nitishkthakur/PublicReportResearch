import os, json, inspect, logging, datetime, time
from typing import List, Callable, Optional, Any, Dict
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import OpenAI
import functools
import traceback

load_dotenv()

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f'openrouter_agent_{timestamp}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('OpenRouterAgent')

# Function decorator for logging
def log_function_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"CALLING: {func.__name__}")
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"COMPLETED: {func.__name__} in {execution_time:.2f}s")
            # Log result summary or truncated version to avoid excessive logs
            if isinstance(result, dict):
                log_result = {k: str(v)[:500] + '...' if isinstance(v, str) and len(str(v)) > 500 else v 
                            for k, v in result.items()}
                logger.info(f"RESULT: {json.dumps(log_result, default=str)[:1000]}")
            else:
                logger.info(f"RESULT: {str(result)[:1000]}")
            return result
        except Exception as e:
            logger.error(f"ERROR in {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            raise
    return wrapper

class OpenRouterAgent:
    """
    A simple agent for interacting with OpenRouter API with tool support and structured output.
    """
    @log_function_call
    def __init__(
        self,
        model_name: str = "deepseek/deepseek-r1-0528:free",  # Default to a powerful model
        tools: List[Callable] = [],
        output_schema: Optional[BaseModel] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        logger.info(f"Initializing OpenRouterAgent with model: {model_name}")
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning("OPENROUTER_API_KEY not found in environment variables")
            
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model_name = model_name
        self.tools = tools
        logger.info(f"Loaded {len(tools)} tools: {[t.__name__ for t in tools]}")
        self.output_schema = output_schema
        if output_schema:
            logger.info(f"Using output schema: {output_schema.__name__}")
        self.tool_schemas = self._generate_tool_schemas()
        self.headers = headers or {}
        
    @log_function_call
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
            logger.debug(f"Generating schema for tool: {tool.__name__}")
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
        logger.info(f"Generated {len(schemas)} tool schemas")
        return schemas

    @log_function_call
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        logger.info(f"Executing tool: {tool_name} with arguments: {json.dumps(arguments, default=str)}")
        for tool in self.tools:
            if tool.__name__ == tool_name:
                try:
                    result = tool(**arguments)
                    logger.info(f"Tool {tool_name} execution successful")
                    return result
                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {e}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    return error_msg
        error_msg = f"Tool {tool_name} not found"
        logger.error(error_msg)
        return error_msg

    @log_function_call
    def invoke(self, prompt: str) -> Dict[str, Any]:
        logger.info(f"Invoking model: {self.model_name}")
        logger.debug(f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")
        
        messages = [{"role": "user", "content": prompt}]
        params = {
            "model": self.model_name, 
            "messages": messages,
            "extra_headers": self.headers
        }
        
        if self.tool_schemas:
            logger.info(f"Using {len(self.tool_schemas)} tool schemas")
            params.update({"tools": self.tool_schemas, "tool_choice": "auto"})
            
        if self.output_schema:
            logger.info(f"Using output schema: {self.output_schema.__name__}")
            # Format according to OpenRouter structured outputs docs
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "strict": True,
                    "schema": self.output_schema.model_json_schema()
                }
            }
        
        logger.info("Sending request to OpenRouter API")
        start_time = time.time()
        response = self.client.chat.completions.create(**params)
        api_time = time.time() - start_time
        logger.info(f"API response received in {api_time:.2f}s")
        
        result = {"message": response.choices[0].message.content, "tool_calls": [], "structured_output": None}
        calls = getattr(response.choices[0].message, "tool_calls", [])
        
        logger.debug(f"Initial response: {result['message'][:100]}..." if result['message'] and len(result['message']) > 100 else f"Initial response: {result['message']}")
        
        if calls:
            logger.info(f"Model requested {len(calls)} tool calls")
            for i, call in enumerate(calls):
                logger.info(f"Tool call {i+1}: {call.function.name}")
                args = json.loads(call.function.arguments)
                logger.debug(f"Tool arguments: {json.dumps(args, default=str)}")
                res = self._execute_tool(call.function.name, args)
                result["tool_calls"].append({"tool": call.function.name, "arguments": args, "result": res})
            
            # follow-up for final response after tool execution
            logger.info("Sending follow-up request with tool results")
            messages.append(response.choices[0].message)
            for call, entry in zip(calls, result["tool_calls"]):
                messages.append({
                    "role": "tool",
                    "content": str(entry["result"]),
                    "tool_call_id": call.id
                })
            
            start_time = time.time()
            follow = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                extra_headers=self.headers
            )
            follow_time = time.time() - start_time
            logger.info(f"Follow-up API response received in {follow_time:.2f}s")
            result["message"] = follow.choices[0].message.content
            logger.debug(f"Final response: {result['message'][:100]}..." if result['message'] and len(result['message']) > 100 else f"Final response: {result['message']}")

        if self.output_schema and result["message"]:
            logger.info("Attempting to parse structured output")
            try:
                # Get content from the message
                message = result["message"]
                
                # Some models may still return formatted JSON with markdown code blocks
                # despite using the structured output format
                if "```json" in message or "```" in message:
                    import re
                    logger.debug("Detected code block in response, extracting JSON")
                    json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', message)
                    if json_match:
                        message = json_match.group(1).strip()
                        logger.debug("Extracted JSON from code block")
                
                # Parse the JSON response
                try:
                    logger.debug("Attempting to parse JSON directly")
                    parsed_data = json.loads(message)
                    result["structured_output"] = self.output_schema(**parsed_data)
                    logger.info("Successfully parsed structured output")
                except json.JSONDecodeError:
                    # Try to find any JSON-like structure in the response
                    logger.warning("JSON decode error, trying to extract JSON-like structure")
                    import re
                    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
                    match = re.search(json_pattern, message)
                    if match:
                        try:
                            logger.debug("Found potential JSON structure, attempting to parse")
                            json_str = match.group(0)
                            parsed_data = json.loads(json_str)
                            result["structured_output"] = self.output_schema(**parsed_data)
                            logger.info("Successfully parsed JSON from extracted structure")
                        except Exception as inner_e:
                            error_msg = f"Found JSON-like structure but failed to parse: {inner_e}"
                            logger.error(error_msg)
                            raise Exception(error_msg)
                    else:
                        error_msg = "No valid JSON structure found in response"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                        
            except Exception as e:
                error_msg = f"Failed to parse structured output: {e}"
                logger.error(error_msg)
                logger.error(f"Original message: {result['message'][:500]}" + ("..." if len(result['message']) > 500 else ""))
                result["structured_output"] = error_msg

        return result

    @log_function_call
    def invoke_plus_next_call(
        self,
        first_prompt: str,
        second_prompt: str,
        overall_task_prompt: str
    ) -> Dict[str, Any]:
        logger.info("Starting two-step invoke workflow")
        logger.debug(f"First prompt: {first_prompt[:100]}..." if len(first_prompt) > 100 else first_prompt)
        logger.debug(f"Second prompt: {second_prompt[:100]}..." if len(second_prompt) > 100 else second_prompt)
        
        first = self.invoke(first_prompt)
        first_out = first.get("tool_calls", first.get("message", ""))
        logger.info("First invoke call completed")
        
        combined_input = (
            f"{overall_task_prompt}\n"
            f"<user>{first_prompt}</user>\n"
            f"<assistant>Output of first LLM Call: {first_out}</assistant>\n"
            f"<user>{second_prompt}</user>"
        )
        logger.debug(f"Combined input for second call: {combined_input[:200]}...")
        
        # Temporarily disable tools for second call
        logger.info("Temporarily disabling tools for second call")
        orig_schemas = self.tool_schemas
        self.tool_schemas = []
        second = self.invoke(combined_input)
        self.tool_schemas = orig_schemas
        logger.info("Second invoke call completed, tools restored")

        result = {
            "first_result": first,
            "second_result": second,
            "combined_input": combined_input,
            "final_message": second.get("message") if "error" not in second else second.get("error")
        }
        logger.info("Two-step invoke workflow completed")
        return result

    @log_function_call
    def help(self):
        """
        Print usage examples for OpenRouterAgent.
        """
        logger.info("Displaying help information")
        help_text = [
            "OpenRouterAgent usage examples:",
            "1) Instantiate the agent:",
            "   agent = OpenRouterAgent(",
            "       model_name='openai/gpt-4o',",
            "       tools=[...],",
            "       output_schema=None,",
            "       headers={",
            '           "HTTP-Referer": "your-site.com",  # Optional. Site URL for rankings',
            '           "X-Title": "Your Site Name",      # Optional. Site title for rankings',
            "       }",
            "   )",
            "2) Simple chat (invoke):",
            "   result = agent.invoke('Hello, how are you?')",
            "   print(result['message'])",
            "3) Two-step workflow (invoke_plus_next_call):",
            "   result = agent.invoke_plus_next_call(",
            "       'First prompt', 'Second prompt', 'Overall task prompt')",
            "   print(result['final_message'])"
        ]
        
        for line in help_text:
            print(line)
            
        return help_text
