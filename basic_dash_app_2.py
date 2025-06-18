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

    if "chart" in message_lower or "plot" in message_lower or "graph" in message_lower:
        fig, ax = plt.subplots(figsize=(10, 6))
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        revenue = [100, 120, 130, 110, 140, 160]
        ax.plot(months, revenue, marker='o', linewidth=2, markersize=8, color=WF_RED)
        ax.set_title('Wells Fargo Revenue Trend', fontsize=16, fontweight='bold')
        ax.set_ylabel('Revenue (Millions $)', fontsize=12)
        ax.set_xlabel('Month', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f8f9fa')
        plt.tight_layout()
        return fig

    elif "data" in message_lower or "table" in message_lower or "dataframe" in message_lower:
        data = {
            'Quarter': ['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024'],
            'Revenue ($M)': [20500, 21300, 20860, 21200],
            'Net Income ($M)': [4600, 4800, 4500, 4700],
            'EPS ($)': [1.25, 1.30, 1.22, 1.28]
        }
        return pd.DataFrame(data)

    else:
        responses = {
            "hello": "Hello! How can I help you with earnings research today?",
            "revenue": "Wells Fargo's revenue has shown steady growth over the past quarters, primarily driven by net interest income and fee-based services.",
            "earnings": "Recent earnings reports show strong performance with consistent EPS growth and improved efficiency ratios.",
            "help": "I can help you with:\n• Financial data analysis\n• Earnings trend charts\n• Revenue breakdowns\n• Comparative analysis\n• Custom reports\n\nJust ask me what you'd like to know!"
        }
        for key, response in responses.items():
            if key in message_lower:
                return response
        return f"I understand you're asking about: '{user_message}'. This is a mock response. In the actual implementation, your chatbot function would process this query and return appropriate financial analysis, data, or visualizations."


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