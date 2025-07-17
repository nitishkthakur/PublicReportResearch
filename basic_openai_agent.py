import json
import inspect
import os
from typing import List, Callable, Optional, Any, Dict, Generator, AsyncGenerator
from pydantic import BaseModel
import openai
from openai import OpenAI


class OpenAIAgent:
    """
    A simple agent class for interacting with OpenAI models with tool support and structured output.
    """
    
    def __init__(
        self,

        model_name: str = "gpt-4.1-mini",
        tools: List[Callable] = [],
        output_schema: Optional[BaseModel] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the OpenAI Agent.
        
        Args:
            model_name: Name of the OpenAI model to use (e.g., 'gpt-4', 'gpt-3.5-turbo')
            tools: List of callable functions that can be used as tools
            output_schema: Optional Pydantic model for structured JSON output
            api_key: OpenAI API key (if not provided, will use environment variable)
            base_url: Optional base URL for OpenAI API (for custom endpoints)
        """
        self.model_name = model_name
        self.tools = tools
        self.output_schema = output_schema
        # Use environment variable if api_key is not provided
        api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
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
        Send a prompt to the OpenAI model and handle tool calls and structured output.
        
        Args:
            prompt: The input prompt to send to the model
            
        Returns:
            Dictionary containing the response and any tool results
        """
        try:
            # Prepare the messages
            messages = [{'role': 'user', 'content': prompt}]
            
            # Prepare request parameters
            request_params = {
                'model': self.model_name,
                'messages': messages,
            }
            
            # Add tools if available
            if self.tool_schemas:
                request_params['tools'] = self.tool_schemas
                request_params['tool_choice'] = 'auto'
            
            # Add structured output format if schema is provided
            if self.output_schema:
                request_params['response_format'] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_output",
                        "schema": self.output_schema.model_json_schema()
                    }
                }
            
            # Make the request to OpenAI
            response = self.client.chat.completions.create(**request_params)
            
            result = {
                'message': response.choices[0].message.content,
                'tool_calls': [],
                'structured_output': None
            }
            
            # Handle tool calls if present
            if response.choices[0].message.tool_calls:
                for tool_call in response.choices[0].message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Execute the tool
                    tool_result = self._execute_tool(tool_name, tool_args)
                    
                    result['tool_calls'].append({
                        'tool': tool_name,
                        'arguments': tool_args,
                        'result': tool_result
                    })
                
                # If there were tool calls, make a follow-up call to get the final response
                if result['tool_calls']:
                    # Add the assistant's message with tool calls to conversation
                    messages.append(response.choices[0].message)
                    
                    # Add tool results as tool messages
                    for tool_call, tool_result in zip(response.choices[0].message.tool_calls, result['tool_calls']):
                        messages.append({
                            'role': 'tool',
                            'content': str(tool_result['result']),
                            'tool_call_id': tool_call.id
                        })
                    
                    # Make follow-up call to get final response
                    follow_up_params = {
                        'model': self.model_name,
                        'messages': messages,
                    }
                    
                    if self.output_schema:
                        follow_up_params['response_format'] = {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "structured_output",
                                "schema": self.output_schema.model_json_schema()
                            }
                        }
                    
                    follow_up_response = self.client.chat.completions.create(**follow_up_params)
                    result['message'] = follow_up_response.choices[0].message.content
            
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
        
    def invoke_plus_next_call(self, first_prompt: str, second_prompt: str, overall_task_prompt: str) -> Dict[str, Any]:
        """
        Perform a two-step invoke process where the output of the first call is used as input for the second call.
        
        Args:
            first_prompt: The initial prompt to send to the first invoke call
            second_prompt: The prompt to send in the second invoke call
            overall_task_prompt: The overall task context that frames the entire conversation
            
        Returns:
            Dictionary containing the final response and results from both calls
        """
        try:
            # First invoke call (with tools enabled)
            first_result = self.invoke(first_prompt)
            
            if 'error' in first_result:
                return {
                    'error': f"First invoke call failed: {first_result['error']}",
                    'first_result': first_result,
                    'second_result': None
                }
            
            # Get the output from the first call
            first_output = first_result.get('tool_calls', '')
            
            # Construct the input for the second invoke call
            second_invoke_input = (
                f"{overall_task_prompt}\n"
                f"<user>{first_prompt}</user>\n"
                f"<assistant>Output of first LLM Call: {first_output}</assistant>\n"
                f"<user>{second_prompt}</user>"
            )
            
            # Second invoke call (without tools)
            # Temporarily disable tools for the second call
            original_tool_schemas = self.tool_schemas
            self.tool_schemas = []
            
            try:
                second_result = self.invoke(second_invoke_input)
            finally:
                # Restore original tool schemas
                self.tool_schemas = original_tool_schemas
            
            return {
                'first_result': first_result,
                'second_result': second_result,
                'combined_input': second_invoke_input,
                'final_message': second_result.get('message') if 'error' not in second_result else second_result.get('error')
            }
            
        except Exception as e:
            return {
                'error': f"Failed in invoke_plus_next_call: {str(e)}",
                'first_result': None,
                'second_result': None
            }


class OpenAIChat:
    """
    A simple chat class for interacting with OpenAI models with conversation history.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the OpenAI Chat.
        
        Args:
            model: Name of the OpenAI model to use
            api_key: OpenAI API key (if not provided, will use environment variable)
            base_url: Optional base URL for OpenAI API (for custom endpoints)
        """
        self.model = model
        # Use environment variable if api_key is not provided
        api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.conversation_history = []

    def chat(self, prompt: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Send a message to the model and get a response while maintaining conversation history.
        
        Args:
            prompt: The user's message
            conversation_history: Optional conversation history to use instead of internal history
            
        Returns:
            The model's response as a string
        """
        try:
            if conversation_history is not None:
                self.conversation_history = conversation_history

            # Add user message to history
            self.conversation_history.append({'role': 'user', 'content': prompt})
            
            # Make the request to OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
            )
            
            # Extract the assistant's response
            assistant_message = response.choices[0].message.content
            
            # Add assistant response to history
            self.conversation_history.append({'role': 'assistant', 'content': assistant_message})
            
            return assistant_message
            
        except Exception as e:
            error_msg = f"Error in chat: {str(e)}"
            # Don't add error to conversation history
            return error_msg

    def chat_stream(self, prompt: str, conversation_history: List[Dict[str, str]] = None) -> Generator[str, None, None]:
        """
        Send a message to the model and get a streaming response while maintaining conversation history.
        
        Args:
            prompt: The user's message
            conversation_history: Optional conversation history to use instead of internal history
            
        Yields:
            Chunks of the model's response as they are generated
        """
        try:
            if conversation_history is not None:
                self.conversation_history = conversation_history

            # Add user message to history
            self.conversation_history.append({'role': 'user', 'content': prompt})
            
            # Make the streaming request to OpenAI
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                stream=True,
            )
            
            full_response = ""
            
            # Process the streaming response
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content_chunk = chunk.choices[0].delta.content
                    full_response += content_chunk
                    yield content_chunk
            
            # Add the complete assistant response to history
            if full_response:
                self.conversation_history.append({'role': 'assistant', 'content': full_response})
            
        except Exception as e:
            error_msg = f"Error in streaming chat: {str(e)}"
            yield error_msg
    
    async def chat_stream_async(self, prompt: str, conversation_history: List[Dict[str, str]] = None) -> AsyncGenerator[str, None]:
        """
        Async version of chat_stream for use with async web frameworks like FastAPI.
        
        Args:
            prompt: The user's message
            conversation_history: Optional conversation history to use instead of internal history
            
        Yields:
            Chunks of the model's response as they are generated
        """
        try:
            if conversation_history is not None:
                self.conversation_history = conversation_history

            # Add user message to history
            self.conversation_history.append({'role': 'user', 'content': prompt})
            
            # Create async client
            async_client = openai.AsyncOpenAI(api_key=self.client.api_key, base_url=self.client.base_url)
            
            # Make the async streaming request to OpenAI
            stream = await async_client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                stream=True,
            )
            
            full_response = ""
            
            # Process the streaming response
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content_chunk = chunk.choices[0].delta.content
                    full_response += content_chunk
                    yield content_chunk
            
            # Add the complete assistant response to history
            if full_response:
                self.conversation_history.append({'role': 'assistant', 'content': full_response})
            
        except Exception as e:
            error_msg = f"Error in async streaming chat: {str(e)}"
            yield error_msg

    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history."""
        return self.conversation_history.copy()


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
    
    def calculate_weather(location: str) -> Dict[str, Any]:
        """
        Fetches weather information for a given location.
        
        Args:
            location: Name of the location to get weather for
            
        Returns:
            Dictionary with weather details
        """
        # Simulated response, replace with actual API call if needed
        if location.lower() == "india":
            temperature = 35
        else:
            temperature = 20
        return {
            "location": location,
            "temperature": temperature,
            "units": "Celsius",
            "description": "Sunny"
        }
    
    # Example output schema
    class WeatherResponse(BaseModel):
        location: str
        temperature: float
        units: str
        description: str
    
    # Create agent
    agent = OpenAIAgent(
        model_name="gpt-4.1-mini",
        tools=[get_product, calculate_sum, calculate_weather],
        output_schema=None
    )
    
    # Use agent - on one call
    result = agent.invoke("What's the Sum of 11 and 22? Also, what's the product of 11 and 22?")
    # print(result)
    
    # Use agent - on two step process
    result = agent.invoke_plus_next_call(
        first_prompt="What's the Sum of 11 and 22? Also, what's the product of 11 and 26? and let me know the weather in india",
        second_prompt="Now, write the final answer to the user questions based on the above conversation",
        overall_task_prompt="You are a helpful assistant that provides answers based on user queries based on only the conversation to follow. If any information you need is not present in the following conversation, you mention so"
    )
    print(result)
    
    '''# Example usage of chat
    chat_agent = OpenAIChat(model="gpt-4.1-mini")

    # Example of regular chat
    print("=== Regular Chat ===")
    chat_result = chat_agent.chat("Hello, who won the world series in 2020?")
    print(chat_result)
    
    # Example of streaming chat
    print("\n=== Streaming Chat ===")
    print("Question: What is artificial intelligence and how does it work?")
    print("Streaming Response: ", end="", flush=True)
    for chunk in chat_agent.chat_stream("What is artificial intelligence and how does it work?"):
        print(chunk, end="", flush=True)
    print()  # New line after streaming is complete
    
    # Print conversation history
    print("\nConversation History:")
    for message in chat_agent.get_history():
        print(f"{message['role']}: {message['content'][:100]}...")  # Truncate for readability
    
    # Clear history
    chat_agent.clear_history()
'''