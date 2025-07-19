
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import base64
import io
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from datetime import datetime, date
from dateutil.relativedelta import relativedelta, MO
import seaborn as sns
import os
from typing import List, Any, Dict
from xhtml2pdf import pisa

# Initialize FastAPI app
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="/home/nitish/Documents/github/PublicReportResearch/fastapi_app/static"), name="static")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="/home/nitish/Documents/github/PublicReportResearch/fastapi_app/templates")

####### Read Data and set things up ########
df = pd.read_excel("/home/nitish/Documents/github/PublicReportResearch/12_metrics.xlsx", sheet_name="Bank_Earnings_Data")

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

df['CompanyName'] = df['CompanyName'].replace(bank_name_mapping)

download_selection: Dict = {}

def get_chatbot_response(user_message):
    # This is a placeholder for the actual chatbot response logic
    # In a real application, this would interact with a language model
    if "citi" in user_message.lower():
        try:
            with open("/home/nitish/Documents/github/PublicReportResearch/Citi_Report.html", "r", encoding="utf-8") as file:
                citi_html = file.read()
            return {"type": "html", "data": citi_html}
        except FileNotFoundError:
            return {"type": "text", "data": "Sorry, the Citi report file could not be found."}
    
    return {"type": "text", "data": f"This is a sample response to: {user_message}"}

def generate_pdf_from_html(html_content):
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(src=html_content, dest=pdf_buffer)
    if not pisa_status.err:
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
    return None

def get_previous_quarter_dates():
    today = date.today()
    current_quarter = (today.month - 1) // 3 + 1
    if current_quarter == 1:
        end_date = date(today.year - 1, 12, 31)
        start_date = date(today.year - 1, 10, 1)
    else:
        end_of_previous_quarter_month = ((current_quarter - 2) * 3) + 3
        end_date = date(today.year, end_of_previous_quarter_month, 1) + relativedelta(months=1) - relativedelta(days=1)
        start_date = date(today.year, end_of_previous_quarter_month - 2, 1)
    return start_date, end_date

def get_quarter_list():
    quarters = []
    today = date.today()
    # Determine the last completed quarter
    current_quarter = (today.month - 1) // 3
    last_quarter_date = date(today.year, current_quarter * 3, 1) - relativedelta(days=1)

    d = date(2010, 1, 1)
    while d <= last_quarter_date:
        q = (d.month - 1) // 3 + 1
        quarters.append(f"{d.year} Q{q}")
        d += relativedelta(months=3)
    return sorted(quarters, reverse=True)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    start_date, end_date = get_previous_quarter_dates()
    quarter_list = get_quarter_list()
    return templates.TemplateResponse("index.html", {"request": request, "start_date": start_date, "end_date": end_date, "quarter_list": quarter_list})

@app.post("/chat", response_class=JSONResponse)
async def chat(message: str = Form(...)):
    response = get_chatbot_response(message)
    return response

@app.get("/citi_report", response_class=HTMLResponse)
async def get_citi_report():
    try:
        with open("/home/nitish/Documents/github/PublicReportResearch/Citi_Report.html", "r", encoding="utf-8") as file:
            citi_html = file.read()
        return HTMLResponse(content=citi_html)
    except FileNotFoundError:
        return HTMLResponse(content="<p>Citi report not found.</p>", status_code=404)

@app.post("/download_pdf", response_class=Response)
async def download_pdf(chat_html: str = Form(...)):
    pdf_bytes = generate_pdf_from_html(chat_html)
    if pdf_bytes:
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=chat_history.pdf"})
    return Response(content="Error generating PDF", status_code=500)

@app.post("/store_download_selection")
async def store_download_selection(
    from_date: str = Form(...),
    to_date: str = Form(...),
    data_types: List[str] = Form(...),
    companies: List[str] = Form(...)
):
    global download_selection
    download_selection = {
        "from_date": from_date,
        "to_date": to_date,
        "data_types": data_types,
        "companies": companies
    }
    return {"message": "Selection stored", "selection": download_selection}

@app.get("/previous_quarter_dates", response_class=JSONResponse)
async def previous_quarter_dates():
    start_date, end_date = get_previous_quarter_dates()
    return {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}

@app.post("/compare_reports", response_class=HTMLResponse)
async def compare_reports(
    mode: str = Form(...),
    companies: List[str] = Form(...),
    from_quarter: str = Form(...),
    to_quarter: str = Form(None)
):
    # In a real application, you would generate a report based on the selections.
    # For now, we'll return a sample HTML report.
    report_html = f"""
    <h3>Comparison Report</h3>
    <p><b>Mode:</b> {mode}</p>
    <p><b>Companies:</b> {', '.join(companies)}</p>
    <p><b>Quarters:</b> {from_quarter}{' to ' + to_quarter if to_quarter else ''}</p>
    <table class="table table-bordered">
        <thead>
            <tr>
                <th>Metric</th>
                <th>Company A</th>
                <th>Company B</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Revenue</td>
                <td>$100M</td>
                <td>$120M</td>
            </tr>
            <tr>
                <td>EPS</td>
                <td>$2.50</td>
                <td>$2.80</td>
            </tr>
        </tbody>
    </table>
    <p>Further analysis and commentary would go here.</p>
    """
    return HTMLResponse(content=report_html)
