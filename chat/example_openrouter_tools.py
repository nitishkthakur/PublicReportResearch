import os
import json
import requests
from dotenv import load_dotenv
import sys
import os.path as path

# Add the agents directory to the path so we can import OpenRouterAgent
sys.path.append(path.join(path.dirname(__file__), '..', 'agents'))
from agent_openrouter import OpenRouterAgent

load_dotenv()  # ensures OPENROUTER_API_KEY is read from .env

# Define a simple tool function
def search_gutenberg_books(search_terms: list):
    """
    Search for books in the Project Gutenberg library based on specified search terms.
    """
    search_query = " ".join(search_terms)
    url = "https://gutendex.com/books"
    response = requests.get(url, params={"search": search_query})
    
    simplified_results = []
    for book in response.json().get("results", [])[:5]:  # limiting to 5 results
        simplified_results.append({
            "id": book.get("id"),
            "title": book.get("title"),
            "authors": book.get("authors")
        })
        
    return simplified_results

def main():
    # instantiate with our tool
    agent = OpenRouterAgent(
        model_name="meta-llama/llama-4-maverick-17b-128e-instruct",  # You can change this to any model supported by OpenRouter
        tools=[search_gutenberg_books],
        output_schema=None,
        headers={
            "HTTP-Referer": "https://yourdomain.com",  # Optional. Site URL for rankings
            "X-Title": "Your Application",            # Optional. Site title for rankings
        }
    )
    
    # send a prompt that will likely trigger tool use
    prompt = "Can you find and recommend some books by James Joyce? List their titles."
    
    result = agent.invoke(prompt)
    
    # Print the agent's response and tool usage
    print("User:", prompt)
    print("\nAssistant:", result["message"])
    
    if result["tool_calls"]:
        print("\nTool calls made:")
        for call in result["tool_calls"]:
            print(f"- {call['tool']} with arguments: {call['arguments']}")

if __name__ == "__main__":
    main()
