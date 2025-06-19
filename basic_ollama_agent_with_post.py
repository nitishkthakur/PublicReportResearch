import requests
import json
import inspect
from typing import List, Callable, Optional, Any, Dict
from pydantic import BaseModel


class OllamaAgent:
    """
    A simple agent class for interacting with Ollama models with tool support and structured output.
    """
    
    def __init__(
        self,
        model_name: str,
        tools: List[Callable],
        output_schema: Optional[BaseModel] = None,
        endpoint: str = "http://localhost:11434/api/chat",
        proxies: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the Ollama Agent.
        
        Args:
            model_name: Name of the Ollama model to use
            tools: List of callable functions that can be used as tools
            output_schema: Optional Pydantic model for structured JSON output
            endpoint: URL of the Ollama chat API
            proxies: Proxy dictionary passed to ``requests.post``
        """
        self.model_name = model_name
        self.tools = tools
        self.output_schema = output_schema
        self.endpoint = endpoint
        self.proxies = proxies if proxies is not None else {"http": "", "https": ""}
        self.tool_schemas = self._generate_tool_schemas()
    
    def _generate_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Generate tool schemas from the provided functions based on their docstrings and signatures.
        
        Returns:
            List of tool schema dictionaries
        """
        schemas = []
        
        for tool in self.tools:
            # Get function signature
            sig = inspect.signature(tool)
            
            # Parse docstring for description and parameter info
            docstring = inspect.getdoc(tool) or ""
            
            # Basic schema structure
            schema = {
                "type": "function",
                "function": {
                    "name": tool.__name__,
                    "description": docstring.split('\n')[0] if docstring else f"Function {tool.__name__}",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            # Add parameters from function signature
            for param_name, param in sig.parameters.items():
                param_type = "string"  # Default type
                
                # Try to infer type from annotation
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == float:
                        param_type = "number"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif param.annotation == list:
                        param_type = "array"
                
                schema["function"]["parameters"]["properties"][param_name] = {
                    "type": param_type,
                    "description": f"Parameter {param_name}"
                }
                
                # Add to required if no default value
                if param.default == inspect.Parameter.empty:
                    schema["function"]["parameters"]["required"].append(param_name)
            
            schemas.append(schema)
        
        return schemas
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool by name with given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool
            
        Returns:
            Result of the tool execution
        """
        for tool in self.tools:
            if tool.__name__ == tool_name:
                try:
                    return tool(**arguments)
                except Exception as e:
                    return f"Error executing {tool_name}: {str(e)}"
        
        return f"Tool {tool_name} not found"
    
    def invoke(self, prompt: str) -> Dict[str, Any]:
        """
        Send a prompt to the Ollama model and handle tool calls and structured output.
        
        Args:
            prompt: The input prompt to send to the model
            
        Returns:
            Dictionary containing the response and any tool results
        """
        try:
            # Prepare the request
            request_params = {
                'model': self.model_name,
                'messages': [{'role': 'user', 'content': prompt}],
                'stream': False
            }
            
            # Add tools if available
            if self.tool_schemas:
                request_params['tools'] = self.tool_schemas
            
            # Add format for structured output if schema is provided
            if self.output_schema:
                request_params['format'] = self.output_schema.model_json_schema()
            
            # Make the request to Ollama
            response = requests.post(
                self.endpoint,
                json=request_params,
                proxies=self.proxies,
            )
            response.raise_for_status()
            response = response.json()
            
            result = {
                'message': response['message']['content'],
                'tool_calls': [],
                'structured_output': None
            }
            
            # Handle tool calls if present
            if 'tool_calls' in response['message']:
                for tool_call in response['message']['tool_calls']:
                    tool_name = tool_call['function']['name']
                    tool_args = tool_call['function']['arguments']
                    
                    # Execute the tool
                    tool_result = self._execute_tool(tool_name, tool_args)
                    
                    result['tool_calls'].append({
                        'tool': tool_name,
                        'arguments': tool_args,
                        'result': tool_result
                    })
            
            # Handle structured output if schema is provided
            if self.output_schema and result['message']:
                try:
                    parsed_output = json.loads(result['message'])
                    result['structured_output'] = self.output_schema(**parsed_output)
                except (json.JSONDecodeError, ValueError) as e:
                    result['structured_output'] = f"Failed to parse structured output: {str(e)}"
            
            return result
            
        except Exception as e:
            return {
                'error': f"Failed to invoke model: {str(e)}",
                'message': None,
                'tool_calls': [],
                'structured_output': None
            }


# Example usage:
if __name__ == "__main__":
    # Example tool functions
    def get_product(a: int, b: int) -> int:
        """
        Computes the product of two numbers.
        """
        return int(a) * int(b)

    def calculate_sum(a: int, b: int) -> int:
        """
        Calculate the sum of two numbers.
        
        Args:
            a: First number
            b: Second number
        """
        return a + b
    
    # Example output schema
    class WeatherResponse(BaseModel):
        location: str
        temperature: float
        units: str
        description: str
    
    # Create agent
    agent = OllamaAgent(
        model_name="llama3.2:1b",
        tools=[get_product, calculate_sum],
        output_schema=None
    )
    
    # Use agent
    result = agent.invoke("What's the Sum of 11 and 22? Also, what's the product of 11 and 22?")
    print(result)