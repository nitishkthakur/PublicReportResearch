from ollama import Client
from pydantic import BaseModel
from typing import Literal, Type, List, Dict, Any
import inspect
import json

# Initialize Ollama client with explicit endpoint
client = Client(host="http://localhost:11434")


def structured_output(
    model: str = "qwen3:4b",
    history: str = "",
    schema_model: Type[BaseModel] = None,
    prompt: str = ""
) -> dict:
    """
    Query an Ollama model via Client, enforce a Pydantic schema, and return validated output.

    Parameters:
        model (str): Model identifier (e.g., "qwen3:4b").
        history (str): Previous conversation history.
        schema_model (Type[BaseModel]): Pydantic BaseModel subclass to validate against.
        prompt (str): The user prompt.

    Returns:
        dict: Parsed and validated model output.

    Raises:
        ValueError: If schema_model is missing or validation fails.
    """
    if schema_model is None:
        raise ValueError("schema_model must be provided and inherit from pydantic.BaseModel")

    messages: List[Dict[str, Any]] = []
    if history:
        messages.append({"role": "user", "content": history})
    messages.append({"role": "user", "content": prompt})

    fmt = schema_model.model_json_schema()
    response = client.chat(model=model, messages=messages, format=fmt)
    content = response.message.content

    try:
        parsed = schema_model.model_validate_json(content)
    except Exception as e:
        raise ValueError(
            f"Validation against {schema_model.__name__} failed: {e}\nResponse: {content}"
        )
    return parsed.dict()


def tool_call(
    model: str = "qwen3:4b",
    history: str = "",
    tools: List = None,
    prompt: str = ""
) -> str:
    """
    Expose Python callables directly to Ollama for function calling and format its returned tool calls.

    Parameters:
        model (str): Ollama model name supporting tool calling.
        history (str): Previous conversation history.
        tools (List[callable]): Functions to expose as tools.
        prompt (str): Instruction for which tool to invoke and with what args.

    Returns:
        str: Human-readable log of each function invocation and its return.
    """
    tools = tools or []

    # Prepare messages
    messages: List[Dict[str, Any]] = []
    if history:
        messages.append({"role": "user", "content": history})
    messages.append({"role": "user", "content": prompt})

    # Call Ollama with tools parameter
    response = client.chat(
        model=model,
        messages=messages,
        tools=tools
    )

    logs: List[str] = []
    # Ollama will populate response.message.tool_calls
    for call in response.message.tool_calls or []:
        func_name = call.function.name
        args = call.function.arguments or {}
        # Look up actual function
        func = next((f for f in tools if f.__name__ == func_name), None)
        if func:
            result = func(**args)
            logs.append(f"{func_name} called with args {args}, returned: {result}")
        else:
            logs.append(f"Requested tool '{func_name}' not found.")

    return "\n".join(logs)


# Example Pydantic model with constrained country names
countries = ["USA", "India", "Bhutan"]
from typing_extensions import Literal
class Country(BaseModel):
    name: Literal[*countries]
    capital: str
    languages: list[str]

if __name__ == "__main__":
    # Structured output example
    country = structured_output(
        model="qwen2.5:3b",
        history="",
        schema_model=Country,
        prompt="Tell me about Joe Mama"
    )
    print("Structured Output:", country)

    # Tool call example
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b
    
    def subtract(a: int, b: int) -> int:
        """Subtract two integers."""
        return a - b

    calls_log = tool_call(
        model="qwen3:4b",
        history="",
        tools=[add, subtract],
        prompt="Compute the sum of 5 and 7 and subtract 3 from 4"
    )
    print("Tool Calls Log:\n", calls_log)
