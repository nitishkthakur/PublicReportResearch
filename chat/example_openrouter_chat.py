import os
from dotenv import load_dotenv
import sys
import os.path as path

# Import pydantic for structured output
from pydantic import BaseModel
from typing import List, Callable, Optional, Dict, Any
# Add the agents directory to the path so we can import OpenRouterAgent
sys.path.append(path.join(path.dirname(__file__), '..', 'agents'))
from agent_openrouter import OpenRouterAgent

load_dotenv()  # ensures OPENROUTER_API_KEY is read from .env
models = ["qwen/qwen3-30b-a3b:free", 
          "deepseek/deepseek-r1-0528:free",
          "moonshotai/kimi-k2:free",
            "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "google/gemma-3n-e2b-it:free",
            "tencent/hunyuan-a13b-instruct:free",
            "tngtech/deepseek-r1t2-chimera:free",
            "mistralai/mistral-small-3.2-24b-instruct:free",
            "moonshotai/kimi-dev-72b:free",
            "deepseek/deepseek-r1-0528-qwen3-8b:free","meta-llama/llama-3.1-405b-instruct:free",
            "meta-llama/llama-3.2-11b-vision-instruct:free", 
            "deepseek/deepseek-r1-distill-qwen-14b:free",
            "google/gemma-3-27b-it:free","google/gemma-3-12b-it:free",
            "google/gemma-3-4b-it:free", "meta-llama/llama-4-maverick",
            "qwen/qwen3-235b-a22b:free", "qwen/qwen3-32b:free", ]

cheap_models = ["google/gemini-2.5-flash", "x-ai/grok-3-mini",
                "deepseek/deepseek-r1-distill-qwen-7b", 
                "deepseek/deepseek-r1-0528", "qwen/qwen3-32b",
                "qwen/qwen3-235b-a22b", "openai/gpt-4.1-mini",
                "meta-llama/llama-4-maverick", "openai/gpt-4.1-nano",
                "qwen/qwen2.5-vl-32b-instruct", "deepseek/deepseek-chat-v3-0324",
                "openai/gpt-4o-mini-search-preview", "google/gemini-2.0-flash-001",
                "qwen/qwen2.5-vl-72b-instruct", "deepseek/deepseek-r1", "qwen/qwen-2.5-72b-instruct",
                "anthropic/claude-3-haiku:beta", "perplexity/sonar-deep-research"

                ]
def main():
    class NextQuestions(BaseModel):
        question1: str
        question2: str
        question3: str


    # instantiate with no tools for free-form chat
    agent = OpenRouterAgent(
        model_name="qwen/qwen3-30b-a3b:free",  # You can change this to any model supported by OpenRouter
        tools=[],
        output_schema=NextQuestions,
        headers={
            "HTTP-Referer": "https://yourdomain.com",  # Optional. Site URL for rankings
            "X-Title": "Your Application",            # Optional. Site title for rankings
        }
    )
    
    # send a prompt
    prompt = """You are a Finance Assistant to Leadership of a Finance company who specializes in suggesting what next questions should be asked by the User based on the provided conversation.

Suggest 3 next questions to the user that they can ask. 

For example:
User: How did Citi bank do recently?
Assistant: 1. How did Citi compare to JPMC?
2. Which of the metrics did Citi Overtake JPMC
3. Rank Citi on the basis of Revenue

Answer in JSON format with keys question1, question2, question3.

The conversation starts now:
"""

    user = """How did Citi compare to JPMC on Q12025?"""
    try:
        result = agent.invoke(prompt+user)
        # print the assistant's reply
        print("User:   ", user)
        print("Assistant:", result["message"])
        print("\nFull result object:")
        print(result)
        if "structured_output" in result:
            print("\nStructured output:")
            print(result["structured_output"])
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
