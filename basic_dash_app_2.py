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
from basic_ollama_agent import OllamaAgent
import ollama
import json
import inspect
from typing import List, Callable, Optional, Any, Dict
from pydantic import BaseModel
import matplotlib.pyplot as plt
import seaborn as sns


####### Read Data and set things up ########
df = pd.read_excel("bank_earnings_data_2019-01-01_2025-12-31.xlsx", sheet_name="Bank_Earnings_Data")

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

def compare_metrics_latest(company_names: str, metric: str):
    """
    This function compares the latest values of a specified metric for a list of companies.

    Args:
        company_names (str): Comma-separated string of company names to compare.
        metric (str): The metric to compare, e.g., 'EPS', 'Revenue', etc.

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

    return metric_data



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

# Create agent
model = "qwen2.5:7b"
agent = OllamaAgent(
    model_name=model,
    tools=[compare_metrics_latest, plot_metrics_comparison_latest, plot_and_compare_metrics_over_history],
    output_schema=None
)

# Use agent
#result = agent.invoke(prompt + "Plot the interest income of wells fargo, JP morgan, citi, american express and bank of america for the latest date.")
#result = agent.invoke(prompt + "Plot the interest income of wells fargo, JP morgan, citi, american express and bank of america for history")




















app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

WF_RED = "#D71921"
WF_GOLD = "#FFCD41"
WF_DARK_RED = "#B71C1C"

custom_styles = {
    'navbar': {
        'backgroundColor': WF_RED,
        'height': '70px',
        'display': 'flex',
        'alignItems': 'center',
        'paddingLeft': '20px',
        'paddingRight': '20px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    },
    'title': {
        'color': 'white',
        'fontSize': '28px',
        'fontWeight': 'bold',
        'margin': '0',
        'fontFamily': 'Arial, sans-serif'
    },
    'chat_container': {
        'height': '500px',
        'overflowY': 'scroll',
        'border': '1px solid #ddd',
        'borderRadius': '8px',
        'padding': '15px',
        'backgroundColor': '#f8f9fa',
        'marginBottom': '20px'
    },
    'user_message': {
        'backgroundColor': WF_RED,
        'color': 'white',
        'padding': '10px 15px',
        'borderRadius': '18px 18px 5px 18px',
        'marginBottom': '10px',
        'marginLeft': '20%',
        'wordWrap': 'break-word'
    },
    'bot_message': {
        'backgroundColor': 'white',
        'color': '#333',
        'padding': '10px 15px',
        'borderRadius': '18px 18px 18px 5px',
        'marginBottom': '10px',
        'marginRight': '20%',
        'border': f'1px solid {WF_RED}',
        'wordWrap': 'break-word'
    },
    'input_container': {
        'display': 'flex',
        'gap': '10px',
        'alignItems': 'center'
    },
    'text_input': {
        'flex': '1',
        'borderRadius': '25px',
        'border': f'2px solid {WF_RED}',
        'padding': '12px 20px',
        'fontSize': '16px'
    },
    'submit_button': {
        'backgroundColor': WF_RED,
        'color': 'white',
        'border': 'none',
        'borderRadius': '25px',
        'padding': '12px 25px',
        'fontSize': '16px',
        'fontWeight': 'bold',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease'
    }
}

app.layout = html.Div([
    html.Div([
        html.H1("Earnings Research", style=custom_styles['title'])
    ], style=custom_styles['navbar']),

    dbc.Container([
        html.Br(),

        html.Div(
            id="chat-container",
            children=[
                html.Div([
                    html.Strong("Assistant: "),
                    "Hello! I'm your Earnings Research assistant. Ask me anything about financial data, earnings analysis, or request charts and reports."
                ], style=custom_styles['bot_message'])
            ],
            style=custom_styles['chat_container']
        ),

        html.Div([
            dcc.Input(
                id="user-input",
                type="text",
                placeholder="Type your message here...",
                style=custom_styles['text_input'],
                n_submit=0
            ),
            html.Button(
                "Send",
                id="submit-button",
                n_clicks=0,
                style=custom_styles['submit_button']
            ),
            html.Button(
                "Download PDF",
                id="download-button",
                n_clicks=0,
                style=custom_styles['submit_button']
            )
        ], style=custom_styles['input_container']),

        html.Br(),

        dcc.Store(id="chat-history", data=[]),
        dcc.Download(id="download-pdf")

    ], fluid=True, style={'paddingTop': '20px', 'paddingBottom': '20px'})
])


def get_chatbot_response(user_message):
    message_lower = user_message.lower()
    result = agent.invoke(prompt + message_lower)
    return result['tool_calls'][0]['result']
    

def format_response_for_display(response):
    if isinstance(response, str):
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
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    for item in history:
        if item['type'] == 'user':
            elements.append(Paragraph(f"You: {item['content']}", styles['Normal']))
            elements.append(Spacer(1, 12))
        elif item['type'] == 'bot':
            subtype = item.get('subtype', 'text')
            if subtype == 'text':
                elements.append(Paragraph(f"Assistant: {item['data']}", styles['Normal']))
                elements.append(Spacer(1, 12))
            elif subtype == 'dataframe':
                df = pd.DataFrame(item['data'], columns=item['columns'])
                tbl_data = [item['columns']] + [list(map(str, row)) for row in df.values]
                table = Table(tbl_data)
                table.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)
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
     Input("user-input", "n_submit")],
    [State("user-input", "value"),
     State("chat-container", "children"),
     State("chat-history", "data")]
)
def update_chat(n_clicks, n_submit, user_input, chat_children, chat_history):
    ctx = callback_context
    if not ctx.triggered or not user_input or user_input.strip() == "":
        return chat_children, "", chat_history

    user_message_div = html.Div([
        html.Strong("You: "),
        user_input
    ], style=custom_styles['user_message'])

    bot_response = get_chatbot_response(user_input)

    if isinstance(bot_response, pd.DataFrame):
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

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8050)