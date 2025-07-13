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


from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
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
    df = pd.read_excel("/home/nitish/Documents/github/PublicReportResearch/12_metrics.xlsx", sheet_name="Bank_Earnings_Data")
    
    bank_name_mapping = {
        'AMERICAN EXPRESS COMPANY': 'American Express',
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
    
    df['CompanyName'] = df['CompanyName'].replace(bank_name_mapping)
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

# Utility functions from original app
def compare_metrics_latest(company_names: str, metric: str, quarters: List[str] = None):
    """Compare latest values of a specified metric for a list of companies."""
    if not DATA_LOADED:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    if isinstance(company_names, str):
        company_names = [name.strip() for name in company_names.split(',')]
    
    latest_date = df['Datetime'].max()
    latest_data = df[df['Datetime'] == latest_date]
    latest_data = latest_data[latest_data['CompanyName'].isin(company_names)]

    if metric not in latest_data.columns:
        raise ValueError(f"Metric '{metric}' not found in the data.")
    
    metric_data = latest_data[['CompanyName', metric]].set_index('CompanyName')
    return metric_data.reset_index()

def plot_metrics_comparison_latest(company_names: str, metric: str):
    """Plot latest values of a specified metric for a list of companies."""
    if not DATA_LOADED:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    if isinstance(company_names, str):
        company_names = [name.strip() for name in company_names.split(',')]
    
    latest_date = df['Datetime'].max()
    latest_data = df[df['Datetime'] == latest_date]
    latest_data = latest_data[latest_data['CompanyName'].isin(company_names)]

    if metric not in latest_data.columns:
        raise ValueError(f"Metric '{metric}' not found in the data.")
    
    metric_data = latest_data[['CompanyName', metric]].set_index('CompanyName')
    metric_data = metric_data.sort_values(by=metric, ascending=False)
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x=metric_data.index, y=metric_data[metric], palette='viridis')
    plt.title(f'Latest {metric} Comparison for Companies')
    plt.xlabel('Company Name')
    plt.ylabel(metric)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Convert plot to base64 string
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.read()).decode()
    plt.close()
    
    return img_base64

def plot_and_compare_metrics_over_history(company_names: str, metric: str):
    """Plot historical values of a specified metric for a list of companies over time."""
    if not DATA_LOADED:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    if isinstance(company_names, str):
        company_names = [name.strip() for name in company_names.split(',')]
    
    filtered_df = df[df['CompanyName'].isin(company_names)]

    if metric not in filtered_df.columns:
        raise ValueError(f"Metric '{metric}' not found in the data.")
    
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=filtered_df, x='Datetime', y=metric, hue='CompanyName', marker='o')
    plt.title(f'{metric} Over Time for Companies')
    plt.xlabel('Date')
    plt.ylabel(metric)
    plt.xticks(rotation=45)
    plt.legend(title='Company Name')
    plt.tight_layout()
    
    # Convert plot to base64 string
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.read()).decode()
    plt.close()
    
    return img_base64

def get_chatbot_response(user_message: str):
    """Get response from chatbot - currently returns sample response."""
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
    uvicorn.run("fastapi_backend:app", host="0.0.0.0", port=8000, reload=True)
