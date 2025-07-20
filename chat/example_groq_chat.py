import os
from dotenv import load_dotenv
import sys
import os.path as path
from pydantic import BaseModel
from typing import List, Callable, Optional, Dict, Any
# Add the agents directory to the path so we can import OpenRouterAgent
sys.path.append(path.join(path.dirname(__file__), '..', 'agents'))

from groq_agent import GroqAgent


load_dotenv()  # ensures GROQ_API_KEY is read from .env
models = ["meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.3-70b-versatile", "meta-llama/llama-4-maverick-17b-128e-instruct",
          "deepseek-r1-distill-llama-70b", "llama-3.3-70b-versatile", "qwen/qwen3-32b"]
def main():
    # instantiate with no tools for free‐form chat
    # define the output schema for structured output
    class NextQuestions(BaseModel):
        question1: str
        question2: str
        question3: str
    output_schema = NextQuestions
    agent = GroqAgent(
        model_name=models[0],
        tools=[],
        output_schema=output_schema
    )
    # send a prompt
    prompt = """You are a Finance Assistant to Leadership of a Finance company who specializes in suggesting what next questions should be asked by the User based on the provided conversation.

Suggest 3 next questions to the user that they can ask. 

For example:
User: How did Citi bank do recently?
Assistant: 1. How did Citi compare to JPMC?
2. Which of the metrics did Citi Overtake JPMC
3. Rank Citi on the basis of Revenue

The conversation starts now:
"""

    user = """How did Citi compare do in Q12025?"""
    result = agent.invoke(prompt+user)
    # print the assistant's reply
    print("User:   ", prompt+user)
    print("Assistant:", result["message"])

if __name__ == "__main__":
    main()
