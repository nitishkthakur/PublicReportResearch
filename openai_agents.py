from openai import OpenAI
from pydantic import BaseModel
from typing import Type, TypeVar, Optional, Union

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
    ) -> Union[T, str]:
        """
        Generate a structured response using the provided Pydantic schema.
        
        Args:
            message: User message to send to the model
            schema: Pydantic model class defining the expected response structure
            model: OpenAI model to use (default: gpt-4o-2024-08-06)
            system_prompt: Optional system prompt to set context
            temperature: Temperature for response generation (default: 0.0)
            
        Returns:
            Parsed Pydantic model instance if successful, or refusal string if refused
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
            
            # Return parsed structured output
            return completion.choices[0].message.parsed.model_dump_json()
            
        except Exception as e:
            raise Exception(f"Error generating structured output: {str(e)}")
