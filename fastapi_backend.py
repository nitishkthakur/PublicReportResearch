from fastapi import FastAPI, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import base64
import io
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
from datetime import datetime
import json
import os
import logging
from tools import *
from basic_ollama_agent_with_post import OllamaAgent
from basic_openai_agent import OpenAIAgent
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from excel_rag import FinancialDataTools
try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Earnings Research API", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Global variables for chat history
chat_history = []

####### Read Data and set things up ########
try:
    financial_tools = FinancialDataTools("12_metrics.xlsx")
    financial_tools.load_data()
    bank_name_mapping = {'AMERICAN EXPRESS COMPANY': 'American Express',
        'Bank of America Corporation': 'Bank of America',
        'CAPITAL\xa0ONE\xa0FINANCIAL\xa0CORP': 'Capital One',
        'Citigroup\xa0Inc': 'Citi',
        'Fifth Third Bancorp': 'Fifth Third',
        'Huntington Bancshares Incorporated': 'Huntington Bank',
        'JPMorgan Chase & Co': 'JPMorgan Chase',
        'KeyCorp': 'KeyBank',
        'NORTHERN TRUST CORPORATION': 'Northern Trust',
        'PNC Financial Services Group, Inc.': 'PNC Bank',
        "People's United Financial, Inc.": 'Peoples United',
        'SCHWAB CHARLES CORP': 'Charles Schwab',
        'STATE STREET CORPORATION': 'State Street',
        'TEGNA INC.': 'Tegna',
        'THE BANK OF NEW YORK MELLON CORPORATION': 'BNY Mellon',
        'TRUIST FINANCIAL CORPORATION': 'Truist',
        'The Goldman Sachs Group, Inc.': 'Goldman Sachs',
        'US BANCORP \\DE\\': 'US Bancorp',
        'WELLS FARGO & COMPANY/MN': 'Wells Fargo'

    }

    financial_tools.df['CompanyName'] = financial_tools.df['CompanyName'].replace(bank_name_mapping)

    DATA_LOADED = True
except Exception as e:
    print(f"Error loading data: {e}")
    DATA_LOADED = False

# Data models
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    response_type: str
    data: Optional[Dict[str, Any]] = None
tools_list = [financial_tools.compare_companies_metric, financial_tools.get_metric_trends, 
              financial_tools.get_metric_for_company_quarter_year]

class FinancialRAGAgent:
    def __init__(self, model_name: str, agent_provider: str = "openai"):
        """
        Initialize the Financial RAG Agent.
        
        Args:
####### Read Data and set things up ########
try:
            model_name: Name of the model to use
            agent_provider: Either "openai" or "ollama" to specify which agent to use
        """
        self.model_name = model_name
        self.agent_provider = agent_provider.lower()
        self.df = financial_tools.df
        
        # Initialize the appropriate agent based on provider
        if self.agent_provider == "openai":
            self.agent = OpenAIAgent(
                model_name=self.model_name,
                tools=tools_list,
                output_schema=None
            )
        elif self.agent_provider == "ollama":
            self.agent = OllamaAgent(
                model_name=self.model_name,
                tools=tools_list,
                output_schema=None
            )
        else:
            raise ValueError(f"Unsupported agent provider: {agent_provider}. Choose 'openai' or 'ollama'.")

    def run_question(self, question: str):
        role = "You are an expert Earnings Data Extractor and Analyzer. "
        task = "Call the appropriate functions to extract the earnings data from the DataFrame and analyze it for the companies mentioned.\n"
        context_company_names = (
            "\nWhen the user asks to search for a company, try to map their mentioned name to a list of pre-defined companies. "
            "The allowed company names are as follows :" + f"{', '.join(self.df['CompanyName'].unique().tolist())}" + "\n"
        )
        Context = "\nHere are the metrics present in the data:" + f"{', '.join(self.df.columns.tolist()[2:])}" + ""
        first_prompt = role + task + context_company_names + Context + question
        overall_prompt = (
            "You are a helpful assistant that provides answers based on user queries. "
            "You will be provided with the conversation to follow which might consist of answers from a tool call. "
            "If any information you need is not present in the following conversation, you mention so."
        )
        second_prompt = "Now, write the final answer to the user questions in html format based on the above conversation"

        result = self.agent.invoke_plus_next_call(
            first_prompt=first_prompt,
            second_prompt=second_prompt,
            overall_task_prompt=overall_prompt
        )
        return result

def get_chatbot_response(user_message: str):
    """Get response from chatbot - currently returns sample response."""
    try:
        agent = FinancialRAGAgent(model_name="gpt-4.1-mini", agent_provider="openai")
        result = agent.run_question(user_message)
        print(result, "\n\n\n\n")
        print(result.get("final_message", "No final answer found."))
        result = result.get("final_message", "No final answer found.")
    except:

        result = f"<!DOCTYPE html><html><head><style>body{{font-family: Arial, sans-serif; padding: 20px;}} h2{{color: #C62828;}}</style></head><body><h2>Sample Response</h2><p>You asked: {user_message}</p><p>This is a sample response. The RAG system is currently disabled.</p></body></html>"
    return result

def generate_pdf_from_history(history: List[Dict]):
    """Generate PDF from chat history."""
    html_chunks = []
    for item in history:
        if item['type'] == 'user':
            html_chunks.append(f"<p><strong>You:</strong> {item['content']}</p>")
        elif item['type'] == 'bot':
            subtype = item.get('subtype', 'text')
            if subtype == 'html':
                html_chunks.append(item['data'])
            elif subtype == 'text':
                html_chunks.append(f"<p><strong>Assistant:</strong> {item['data']}</p>")
            elif subtype == 'image':
                img_src = f"data:image/png;base64,{item['data']}"
                html_chunks.append(f"<p><strong>Assistant:</strong></p><img src=\"{img_src}\" style=\"max-width:100%;\"/>")

    complete_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Chat History</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        .styled-table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        .styled-table th, .styled-table td {{ padding: 12px 15px; border: 1px solid #ddd; text-align: left; }}
        .styled-table th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
{"".join(html_chunks)}
</body>
</html>
"""
    
    if pisa:
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(src=complete_html, dest=pdf_buffer)
        if not pisa_status.err:
            pdf_buffer.seek(0)
            return pdf_buffer.getvalue()
    
    # Fallback to simple text if pisa fails
    return complete_html.encode('utf-8')

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat", response_class=HTMLResponse)
async def handle_chat(request: Request, message: str = Form(...)):
    """Handle chat messages."""
    global chat_history
    
    # Add user message to history
    user_message = {
        'type': 'user',
        'content': message,
        'timestamp': datetime.now().isoformat()
    }
    chat_history.append(user_message)
    
    # Get bot response
    bot_response = get_chatbot_response(message)
    
    # Determine response type
    if "<!DOCTYPE html>" in bot_response:
        response_type = "html"
        bot_data = bot_response
    else:
        response_type = "text"
        bot_data = bot_response
    
    # Add bot response to history
    bot_message = {
        'type': 'bot',
        'subtype': response_type,
        'data': bot_data,
        'timestamp': datetime.now().isoformat()
    }
    chat_history.append(bot_message)
    
    # Return HTML for chat messages
    user_html = f'''
    <div class="user-message">
        <strong>You:</strong> {message}
    </div>
    '''
    
    if response_type == "html":
        bot_html = f'''
        <div class="bot-message">
            <strong>Assistant:</strong><br>
            <iframe srcdoc="{bot_data.replace('"', '&quot;')}" style="width: 100%; height: 400px; border: none; margin-top: 10px;"></iframe>
        </div>
        '''
    else:
        bot_html = f'''
        <div class="bot-message">
            <strong>Assistant:</strong> {bot_data}
        </div>
        '''
    
    return HTMLResponse(content=user_html + bot_html)

@app.post("/bank-select", response_class=HTMLResponse)
async def handle_bank_select(request: Request, bank: str = Form(...)):
    """Handle bank selection."""
    global chat_history
    
    # Try to load bank report
    try:
        report_file = f"{bank.lower()}_report.html"
        if os.path.exists(report_file):
            with open(report_file, "r", encoding="utf-8") as file:
                bank_html = file.read()
            
            response_data = bank_html
            response_type = "html"
        else:
            response_data = f"Report for {bank} is not available yet."
            response_type = "text"
    except Exception as e:
        response_data = f"Error loading {bank} report: {str(e)}"
        response_type = "text"
    
    # Add to chat history
    bot_message = {
        'type': 'bot',
        'subtype': response_type,
        'data': response_data,
        'timestamp': datetime.now().isoformat()
    }
    chat_history.append(bot_message)
    
    # Return HTML response
    if response_type == "html":
        return HTMLResponse(content=f'''
        <div class="bot-message">
            <strong>Assistant:</strong><br>
            <iframe srcdoc="{response_data.replace('"', '&quot;')}" style="width: 100%; height: 500px; border: 1px solid #ddd; border-radius: 8px; margin-top: 10px;"></iframe>
        </div>
        ''')
    else:
        return HTMLResponse(content=f'''
        <div class="bot-message">
            <strong>Assistant:</strong> {response_data}
        </div>
        ''')

@app.get("/download-pdf")
async def download_pdf():
    """Download chat history as PDF."""
    global chat_history
    
    try:
        pdf_data = generate_pdf_from_history(chat_history)
        
        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=chat_history.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

@app.post("/upload", response_class=HTMLResponse)
async def handle_upload(request: Request, file: UploadFile = File(...)):
    """Handle file upload."""
    logging.info("Upload Initiated")
    return HTMLResponse(content='''
    <div class="bot-message">
        <strong>Assistant:</strong> Upload functionality is under development. This feature will allow you to upload files for analysis.
    </div>
    ''')

@app.get("/reset-chat", response_class=HTMLResponse)
async def reset_chat():
    """Reset chat to initial state."""
    global chat_history
    chat_history = []
    
    return HTMLResponse(content='''
    <div class="bot-message">
        <strong>Assistant:</strong> Hello! I'm your Earnings Research assistant. Ask me anything about financial data, earnings analysis, or request charts and reports.
    </div>
    ''')

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "data_loaded": DATA_LOADED}

@app.get("/earnings-calendar", response_class=HTMLResponse)
async def earnings_calendar(request: Request):
    """Serve the earnings calendar page."""
    return templates.TemplateResponse("earnings_calendar.html", {"request": request})

@app.get("/api/earnings-data")
async def get_earnings_data():
    """Get earnings calendar data."""
    earnings_data = {
        "2024-01-12": "JPMorgan Chase Earnings Report",
        "2024-01-16": "Bank of America Earnings Report",
        "2024-01-17": "Goldman Sachs Earnings Report",
        "2024-01-19": "Wells Fargo Earnings Report",
        "2024-01-22": "American Express Earnings Report",
        "2024-02-14": "Citi Earnings Report",
        "2024-02-15": "JPMorgan Chase Earnings Report",
        "2024-02-20": "PNC Bank Earnings Report",
        "2024-02-23": "Charles Schwab Earnings Report",
        "2024-03-15": "Goldman Sachs Earnings Report",
        "2024-03-18": "Wells Fargo Earnings Report",
        "2024-03-21": "Bank of America Earnings Report",
        "2024-03-25": "Truist Earnings Report",
        "2024-04-12": "JPMorgan Chase Earnings Report",
        "2024-04-15": "Goldman Sachs Earnings Report",
        "2024-04-16": "Bank of America Earnings Report",
        "2024-04-18": "Wells Fargo Earnings Report",
        "2024-04-22": "American Express Earnings Report",
        "2024-05-14": "Citi Earnings Report",
        "2024-05-16": "JPMorgan Chase Earnings Report",
        "2024-05-20": "PNC Bank Earnings Report",
        "2024-05-23": "Charles Schwab Earnings Report"
    }
    return earnings_data

if __name__ == "__main__":
    import uvicorn
    #uvicorn.run("fastapi_backend:app", host="0.0.0.0", port=8000, reload=True)
    uvicorn.run("fastapi_backend:app", host="0.0.0.0", port=8000, reload=True)
