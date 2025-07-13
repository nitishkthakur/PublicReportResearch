import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import pandas as pd
import numpy as np
from rags import RAG
try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None
import os
from typing import List, Any
import seaborn as sns
from layout4 import get_layout, custom_styles

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
### Generate prompt without xml tags for the agent
role = "You are an expert Earnings Data Extractor and Analyzer. " 
task = "Call the appropriate functions to extract the earnings data from the DataFrame and analyze it for the companies mentioned.\n"

context_company_names = "\nWhen the user asks to search for a company, try to map their mentioned name to a list of pre-defined companies. The allowed company names are as follows :" + f"{', '.join(df['CompanyName'].unique().tolist())}" + "\n"

Context = "\nHere are the metrics present in the data:" + f"{', '.join(df.columns.tolist()[2:])}" + ""
prompt = role + task + context_company_names + Context

def compare_metrics_latest(company_names: str, metric: str, quarters: List[str] = None):
    """
    This function compares the latest values of a specified metric for a list of companies.

    Args:
        company_names (str): Comma-separated string of company names to compare.
        metric (str): The metric to compare, e.g., 'EPS', 'Revenue', etc.
        quarters (List[str], optional): List of quarters to filter the data. One example input is ['Q1', 'Q2']

    Returns:
        pd.DataFrame: A DataFrame containing the latest values of the specified metric for the given companies.
    
    Raises:
        ValueError: If the metric is not found in the DataFrame.
    """
    if type(company_names) is  str:
        company_names = [name.strip() for name in company_names.split(',')]
    
    latest_date = df['Datetime'].max()
    
    # Filter df
    latest_data = df[df['Datetime'] == latest_date]

    # Select relevant companies
    latest_data = latest_data[latest_data['CompanyName'].isin(company_names)]

    # Check if metric exists
    if metric not in latest_data.columns:
        raise ValueError(f"Metric '{metric}' not found in the data.")
    
    # Extract the relevant data
    metric_data = latest_data[['CompanyName', metric]].set_index('CompanyName')

    return metric_data.reset_index()



def plot_metrics_comparison_latest(company_names: str, metric: str):
    """
    This function plots the latest values of a specified metric for a list of companies.

    Args:
        company_names (str): Comma-separated string of company names to compare.
        metric (str): The metric to compare, e.g., 'EPS', 'Revenue', etc.

    Returns:
        Matplotlib plot: A plot containing the latest values of the specified metric for the given companies.

    Raises:
        ValueError: If the metric is not found in the DataFrame.
    """
    if type(company_names) is  str:
        company_names = [name.strip() for name in company_names.split(',')]
    print(company_names)
    latest_date = df['Datetime'].max()
    
    # Filter df
    latest_data = df[df['Datetime'] == latest_date]

    # Select relevant companies
    latest_data = latest_data[latest_data['CompanyName'].isin(company_names)]

    # Check if metric exists
    if metric not in latest_data.columns:
        raise ValueError(f"Metric '{metric}' not found in the data.")
    
    # Extract the relevant data
    metric_data = latest_data[['CompanyName', metric]].set_index('CompanyName')
    metric_data = metric_data.sort_values(by=metric, ascending=False)
    
    # Plotting  
    plt.figure(figsize=(10, 6))
    sns.barplot(x=metric_data.index, y=metric_data[metric], palette='viridis')
    plt.title(f'Latest {metric} Comparison for Companies')
    plt.xlabel('Company Name')
    plt.ylabel(metric)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    return plt.gcf()


def plot_and_compare_metrics_over_history(company_names: str, metric: str):
    """ This function plots the historical values of a specified metric for a list of companies over time. Call this when trying to see trend or over time.
    
    Args:
        company_names (str): Comma-separated string of company names to compare.
        metric (str): The metric to compare, e.g., 'EPS', 'Revenue', etc.
    Returns:
        Matplotlib plot: A plot containing the historical values of the specified metric for the given companies.
            
    Raises:
        ValueError: If the metric is not found in the DataFrame.
    """
    # Filter for company
    if type(company_names) is  str:
        company_names = [name.strip() for name in company_names.split(',')]
    
    # Filter df
    filtered_df = df[df['CompanyName'].isin(company_names)]

    # Check if metric exists
    if metric not in filtered_df.columns:
        raise ValueError(f"Metric '{metric}' not found in the data.")
    
    # Plotting
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=filtered_df, x='Datetime', y=metric, hue='CompanyName', marker='o')
    plt.title(f'{metric} Over Time for Companies')
    plt.xlabel('Date')
    plt.ylabel(metric)
    plt.xticks(rotation=45)
    plt.legend(title='Company Name')
    plt.tight_layout()
    plt.show()
    return plt.gcf()






















DOCS_DIR = os.path.join(os.getcwd(), "docs")
INDEX_DIR = os.path.join(os.getcwd(), "rag_index")

pre_prompt = """Answer the question asked by the user. Support your answer with data in tabular format.
Provide tables and supporting commentary. Provide the answer only in HTML format. When the user asks a question, give more context that helps them understand better and more.
If they ask for one metric, give surrounding information which will be useful to Finance Experts about other related metrics and other quarters.
Follow the following steps:
1. Plan and list out what you will present to the user in <think> </think> tags.
2. Start the answer after the think tags.
3. The Answer should be in proper html format. The answer should start with <!DOCTYPE html> tag. Make sure to add some basic css to beautify the answer section only
4. Only provide html, not markdown or any other format.
5. Do not provide any explanation or commentary outside the html tags.
6. The commentary should be detailed. Compare previous quarters, other related metrics.
If the user asks to summarize the report of a particular company, quarter, then list out first, the top 20 metrics to analyze.
"""

'''rag = RAG(llm_model="gemma3:4b-it-fp16")
try:
    rag.load_vector_store(INDEX_DIR)
except Exception:
    rag.build_vector_store(DOCS_DIR)
    rag.save_vector_store(INDEX_DIR)
'''
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

WF_RED = "#D71921"
WF_GOLD = "#FFCD41"
WF_DARK_RED = "#B71C1C"

app.layout = get_layout()

def get_chatbot_response(user_message):


    result = "<!DOCTYPE html><html> <h2> sample Response </h2> </html>"
    #result = rag.invoke(user_message)
    idx = result.find("<!DOCTYPE html>")
    if idx != -1:
        result = result[idx:]
    return result
    

def format_response_for_display(response):
    if isinstance(response, str):
        stripped = response.strip()
        if "<!DOCTYPE html>" in response or stripped.startswith("<html"):
            iframe = html.Iframe(srcDoc=response,
                                 style={'width': '100%', 'height': '600px', 'border': 'none'})
            return html.Div([
                html.Strong("Assistant: "),
                html.Br(),
                iframe
            ], style=custom_styles['bot_message'])
        return html.Div([
            html.Strong("Assistant: "),
            html.Span(response)
        ], style=custom_styles['bot_message'])
    elif isinstance(response, pd.DataFrame):
        return html.Div([
            html.Strong("Assistant: "),
            html.Br(),
            html.Div([
                dbc.Table.from_dataframe(
                    response,
                    striped=True,
                    bordered=True,
                    hover=True,
                    size='sm',
                    style={'marginTop': '10px'}
                )
            ])
        ], style=custom_styles['bot_message'])
    elif hasattr(response, 'savefig'):
        img_buffer = io.BytesIO()
        response.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode()
        plt.close(response)
        return html.Div([
            html.Strong("Assistant: "),
            html.Br(),
            html.Img(
                src=f"data:image/png;base64,{img_base64}",
                style={'maxWidth': '100%', 'height': 'auto', 'marginTop': '10px'}
            )
        ], style=custom_styles['bot_message'])
    else:
        return html.Div([
            html.Strong("Assistant: "),
            html.Span(str(response))
        ], style=custom_styles['bot_message'])


def generate_pdf(history):
    # Build a unified HTML representation of the chat
    html_chunks: List[str] = []
    for item in history:
        if item['type'] == 'user':
            html_chunks.append(f"<p><strong>You:</strong> {item['content']}</p>")
        elif item['type'] == 'bot':
            subtype = item.get('subtype', 'text')
            if subtype == 'html':
                html_chunks.append(item['data'])
            elif subtype == 'text':
                html_chunks.append(f"<p><strong>Assistant:</strong> {item['data']}</p>")
            elif subtype == 'dataframe':
                df = pd.DataFrame(item['data'], columns=item['columns'])
                html_chunks.append("<p><strong>Assistant:</strong></p>" + df.to_html(index=False, classes="styled-table"))
            elif subtype == 'image':
                img_src = f"data:image/png;base64,{item['data']}"
                html_chunks.append(f"<p><strong>Assistant:</strong></p><img src=\"{img_src}\" style=\"max-width:100%;\"/>")

    complete_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=\"UTF-8\"> 
  <title>Chat History</title>
  <style>
    body {{ font-family: Arial, sans-serif; padding:20px; }}
    .styled-table {{ border-collapse: collapse; width:100%; margin-bottom:20px; table-layout:auto; }}
    .styled-table th, .styled-table td {{ padding:12px 15px; border:1px solid #ddd; text-align:left; vertical-align:top; }}
    .styled-table th {{ background-color:#f2f2f2; }}
  </style>
</head>
<body>
{"".join(html_chunks)}
</body>
</html>
"""
    # Attempt HTML-to-PDF conversion via xhtml2pdf (pip install xhtml2pdf)
    if pisa:
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(src=complete_html, dest=pdf_buffer)
        if not pisa_status.err:
            pdf_buffer.seek(0)
            return pdf_buffer.getvalue()
    # Fallback to basic ReportLab PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements: List[Any] = []
    for item in history:
        if item['type'] == 'user':
            elements.append(Paragraph(f"You: {item['content']}", styles['Normal']))
            elements.append(Spacer(1, 12))
        elif item['type'] == 'bot':
            subtype = item.get('subtype', 'text')
            if subtype == 'html':
                elements.append(Paragraph("Assistant (HTML content):", styles['Normal']))
                elements.append(Paragraph(item['data'], styles['Normal']))
                elements.append(Spacer(1, 12))
            elif subtype == 'text':
                elements.append(Paragraph(f"Assistant: {item['data']}", styles['Normal']))
                elements.append(Spacer(1, 12))
            elif subtype == 'dataframe':
                df = pd.DataFrame(item['data'], columns=item['columns'])
                tbl_data = [item['columns']] + [list(map(str, row)) for row in df.values]
                table = Table(tbl_data)
                table.setStyle(TableStyle([
                    ("GRID", (0,0), (-1,-1), 1, colors.black),
                    ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ]))
                elements.append(Paragraph("Assistant:", styles['Normal']))
                elements.append(table)
                elements.append(Spacer(1, 12))
            elif subtype == 'image':
                img_data = base64.b64decode(item['data'])
                img_io = io.BytesIO(img_data)
                elements.append(Paragraph("Assistant:", styles['Normal']))
                elements.append(Image(img_io, width=400, height=300))
                elements.append(Spacer(1, 12))
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


@app.callback(
    [Output("chat-container", "children"),
     Output("user-input", "value"),
     Output("chat-history", "data")],
    [Input("submit-button", "n_clicks"),
     Input("user-input", "n_submit"),
     Input("bank-citi", "n_clicks")],
    [State("user-input", "value"),
     State("chat-container", "children"),
     State("chat-history", "data")]
)
def update_chat(n_clicks, n_submit, citi_clicks, user_input, chat_children, chat_history):
    ctx = callback_context
    if not ctx.triggered:
        return chat_children, "", chat_history
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Handle Citi bank button click
    if trigger_id == "bank-citi" and citi_clicks > 0:
        try:
            # Load the HTML file
            with open("Citi_Report.html", "r", encoding="utf-8") as file:
                citi_html = file.read()
            
            # Create bot message with HTML content
            bot_message_div = html.Div([
                html.Strong("Assistant: "),
                html.Br(),
                html.Iframe(
                    srcDoc=citi_html,
                    style={'width': '100%', 'height': '600px', 'border': '1px solid #ddd', 'borderRadius': '8px'}
                )
            ], style=custom_styles['bot_message'])
            
            # Update chat history
            store_bot = {
                'type': 'bot',
                'subtype': 'html',
                'data': citi_html,
                'timestamp': datetime.now().isoformat()
            }
            
            new_history = chat_history + [store_bot]
            updated_chat = chat_children + [bot_message_div]
            
            return updated_chat, "", new_history
            
        except FileNotFoundError:
            error_message = html.Div([
                html.Strong("Assistant: "),
                html.Span("Sorry, the Citi report file could not be found.")
            ], style=custom_styles['bot_message'])
            
            return chat_children + [error_message], "", chat_history
    
    # Handle regular chat input
    if not user_input or user_input.strip() == "":
        return chat_children, "", chat_history

    user_message_div = html.Div([
        html.Strong("You: "),
        user_input
    ], style=custom_styles['user_message'])

    bot_response = get_chatbot_response(user_input)

    if isinstance(bot_response, str) and "<!DOCTYPE html>" in bot_response:
        bot_message_div = format_response_for_display(bot_response)
        store_bot = {
            'type': 'bot',
            'subtype': 'html',
            'data': bot_response,
            'timestamp': datetime.now().isoformat()
        }
    elif isinstance(bot_response, pd.DataFrame):
        bot_message_div = format_response_for_display(bot_response)
        store_bot = {
            'type': 'bot',
            'subtype': 'dataframe',
            'columns': bot_response.columns.tolist(),
            'data': bot_response.to_dict('records'),
            'timestamp': datetime.now().isoformat()
        }
    elif hasattr(bot_response, 'savefig'):
        img_buffer = io.BytesIO()
        bot_response.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode()
        plt.close(bot_response)
        bot_message_div = format_response_for_display(bot_response)
        store_bot = {
            'type': 'bot',
            'subtype': 'image',
            'data': img_base64,
            'timestamp': datetime.now().isoformat()
        }
    else:
        bot_message_div = format_response_for_display(bot_response)
        store_bot = {
            'type': 'bot',
            'subtype': 'text',
            'data': str(bot_response),
            'timestamp': datetime.now().isoformat()
        }

    new_history = chat_history + [
        {'type': 'user', 'content': user_input, 'timestamp': datetime.now().isoformat()},
        store_bot
    ]

    updated_chat = chat_children + [user_message_div, bot_message_div]

    return updated_chat, "", new_history


@app.callback(
    Output("download-pdf", "data"),
    Input("download-button", "n_clicks"),
    State("chat-history", "data"),
    prevent_initial_call=True
)
def download_chat(n_clicks, history):
    pdf_bytes = generate_pdf(history)
    return dcc.send_bytes(pdf_bytes, filename="chat_history.pdf")


app.clientside_callback(
    """
    function(children) {
        setTimeout(function() {
            var chatContainer = document.getElementById('chat-container');
            if (chatContainer) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }, 100);
        return window.dash_clientside.no_update;
    }
    """,
    Output("chat-container", "style"),
    Input("chat-container", "children")
)

# Add callback for sidebar navigation
@app.callback(
    Output("chat-container", "children", allow_duplicate=True),
    [Input("nav-kpi", "n_clicks"),
     Input("nav-compare", "n_clicks"),
     Input("nav-revenue", "n_clicks"),
     Input("nav-eps", "n_clicks"),
     Input("nav-download-data", "n_clicks"),
     Input("nav-net-income", "n_clicks"),
     Input("nav-segment-performance", "n_clicks"),
     Input("nav-capital-risk", "n_clicks")],
    prevent_initial_call=True
)
def handle_sidebar_navigation(kpi_clicks, compare_clicks, revenue_clicks, eps_clicks, download_data_clicks, net_income_clicks, segment_clicks, capital_clicks):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update
    
    # Return empty page for any sidebar click except chat
    return [html.Div([
        html.H3("Coming Soon", style={'textAlign': 'center', 'color': '#666', 'marginTop': '100px'}),
        html.P("This feature is under development.", style={'textAlign': 'center', 'color': '#999'})
    ])]

# Add callback for upload button
@app.callback(
    [Output("chat-container", "children", allow_duplicate=True),
     Output("chat-history", "data", allow_duplicate=True)],
    Input("upload-button", "n_clicks"),
    [State("chat-container", "children"),
     State("chat-history", "data")],
    prevent_initial_call=True
)
def handle_upload(upload_clicks, chat_children, chat_history):
    if upload_clicks > 0:
        # Create upload message
        upload_message = html.Div([
            html.Strong("Assistant: "),
            html.Span("Upload functionality is under development. This feature will allow you to upload files for analysis.")
        ], style=custom_styles['bot_message'])
        
        # Update chat history
        store_bot = {
            'type': 'bot',
            'subtype': 'text',
            'data': 'Upload functionality is under development. This feature will allow you to upload files for analysis.',
            'timestamp': datetime.now().isoformat()
        }
        
        new_history = chat_history + [store_bot]
        updated_chat = chat_children + [upload_message]
        
        return updated_chat, new_history
    
    return dash.no_update, dash.no_update

# Add callback to reset chat when clicking on Chat navigation
@app.callback(
    Output("chat-container", "children", allow_duplicate=True),
    Input("nav-chat", "n_clicks"),
    prevent_initial_call=True
)
def reset_to_chat(chat_clicks):
    if chat_clicks > 0:
        return [html.Div([
            html.Strong("Assistant: "),
            "Hello! I'm your Earnings Research assistant. Ask me anything about financial data, earnings analysis, or request charts and reports."
        ], style=custom_styles['bot_message'])]
    return dash.no_update

if __name__ == "__main__":
    app.run(debug=True)