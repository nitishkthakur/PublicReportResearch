from ollama import Client
from pydantic import BaseModel
from typing import Literal, Type, List, Dict, Any
import inspect
import json
import PyPDF2
from pathlib import Path

# Initialize Ollama client with explicit endpoint
client = Client(host="http://localhost:11434")


def structured_output(
    model: str = "qwen3:4b",
    history: str = "",
    schema_model: Type[BaseModel] = None,
    prompt: str = "",
    system_instructions: str = "Format output as valid JSON only."
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
    messages.append({"role": "system", "content": system_instructions})

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

class PDFChatBot:
    """
    A chatbot that reads PDF content and maintains conversation memory with HTML-formatted responses.
    """
    
    def __init__(
        self, 
        model: str = "qwen2.5:3b", 
        pdf_path: str = "", 
        pages_to_read: int = 5,
        pre_prompt: str = None
    ):
        """
        Initialize the PDF ChatBot.
        
        Parameters:
            model (str): Ollama model name
            pdf_path (str): Path to the PDF file
            pages_to_read (int): Number of pages to read from the beginning
            pre_prompt (str): Custom pre-prompt, uses default HTML formatting if None
        """
        self.model = model
        self.pdf_path = pdf_path
        self.pages_to_read = pages_to_read
        self.conversation_history: List[Dict[str, str]] = []
        self.pdf_content = ""
        
        # Default pre-prompt for HTML output with CSS and table formatting
        self.pre_prompt = pre_prompt or """
        You are a helpful assistant that provides responses in well-formatted HTML with embedded CSS.
        
        Format your response as follows:
        - Use proper HTML structure with <div> containers
        - Include inline CSS for styling (colors, fonts, spacing)
        - Always include at least one HTML table with borders and styling when relevant to the query
        - Use headings (<h1>, <h2>, <h3>) to structure content
        - Apply CSS styling for better readability (margins, padding, colors)
        - Make tables visually appealing with alternating row colors and borders
        
        Example CSS styling to use:
        <style>
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f2f2; font-weight: bold; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        h1 { color: #333; border-bottom: 2px solid #007acc; }
        h2 { color: #555; }
        div { margin: 10px; padding: 15px; }
        </style>
        """
        
        # Load PDF content
        self._load_pdf_content()
    
    def _load_pdf_content(self):
        """Extract text from the specified number of PDF pages."""
        if not self.pdf_path or not Path(self.pdf_path).exists():
            self.pdf_content = ""
            return
            
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pages_text = []
                
                # Read up to the specified number of pages
                num_pages = min(len(pdf_reader.pages), self.pages_to_read)
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    pages_text.append(page.extract_text())
                
                self.pdf_content = "\n".join(pages_text)
        except Exception as e:
            print(f"Error reading PDF: {e}")
            self.pdf_content = ""
    
    def chat(self, query: str, post_prompt: str = "") -> str:
        """
        Chat with the model using the query and optional post_prompt.
        
        Parameters:
            query (str): User's question or input
            post_prompt (str): Additional instructions to append to the query
            
        Returns:
            str: Model's response in HTML format
        """
        # Combine query and post_prompt
        full_query = f"{query} {post_prompt}".strip()
        
        # Prepare messages
        messages: List[Dict[str, Any]] = []
        
        # Add system message with pre-prompt and PDF context
        system_content = self.pre_prompt
        if self.pdf_content:
            system_content += f"\n\nContext from PDF:\n{self.pdf_content[:4000]}..."  # Limit PDF content
        
        messages.append({"role": "system", "content": system_content})
        
        # Add conversation history
        for msg in self.conversation_history:
            messages.append(msg)
        
        # Add current query
        messages.append({"role": "user", "content": full_query})
        
        # Get response from Ollama
        try:
            response = client.chat(model=self.model, messages=messages)
            assistant_response = response.message.content
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": full_query})
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            # Keep conversation history manageable (last 10 exchanges)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return assistant_response
            
        except Exception as e:
            return f"<div style='color: red; padding: 10px;'>Error: {e}</div>"
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
    
    def get_pdf_info(self) -> Dict[str, Any]:
        """Get information about the loaded PDF."""
        return {
            "pdf_path": self.pdf_path,
            "pages_to_read": self.pages_to_read,
            "content_length": len(self.pdf_content),
            "has_content": bool(self.pdf_content)
        }

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
    
    # PDFChatBot example
    print("\n" + "="*50)
    print("PDF ChatBot Example")
    print("="*50)
    
    # Initialize the chatbot with a PDF file
    pdf_bot = PDFChatBot(
        model="qwen2.5:3b",
        pdf_path="/path/to/your/document.pdf",  # Replace with actual PDF path
        pages_to_read=3
    )
    
    # Check PDF info
    pdf_info = pdf_bot.get_pdf_info()
    print(f"PDF Info: {pdf_info}")
    
    # Single example query
    print("\n--- PDF Query Example ---")
    query = "What is the main topic of this document?"
    post_prompt = "Please provide a summary in table format with key points."
    
    print(f"Question: {query}")
    print(f"Post-prompt: {post_prompt}")
    
    response = pdf_bot.chat(query, post_prompt)
    print(f"Response length: {len(response)} characters")
    
    # Save HTML response to file for viewing
    with open("/home/nitish/Documents/github/PublicReportResearch/pdf_response.html", "w", encoding="utf-8") as f:
        f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <title>PDF ChatBot Response</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>Query: {query}</h1>
    <h2>Post-prompt: {post_prompt}</h2>
    <hr>
    {response}
</body>
</html>
        """)
    print("Response saved to pdf_response.html")
    
    print("\nExample completed! Check pdf_response.html for the formatted response.")
