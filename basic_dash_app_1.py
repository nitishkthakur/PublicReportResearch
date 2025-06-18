import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64
import io
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Wells Fargo brand colors
WF_RED = "#D71921"
WF_GOLD = "#FFCD41"
WF_DARK_RED = "#B71C1C"

# Custom CSS styles
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

# Layout
app.layout = html.Div([
    # Navigation Bar
    html.Div([
        html.H1("Earnings Research", style=custom_styles['title'])
    ], style=custom_styles['navbar']),
    
    # Main Content
    dbc.Container([
        html.Br(),
        
        # Chat Container
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
        
        # Input Container
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
            )
        ], style=custom_styles['input_container']),
        
        html.Br(),
        
        # Hidden div to store chat history
        dcc.Store(id="chat-history", data=[]),
        
    ], fluid=True, style={'paddingTop': '20px', 'paddingBottom': '20px'})
])

# Mock function to simulate your chatbot response function
def get_chatbot_response(user_message):
    """
    Mock function that simulates your actual chatbot response.
    Replace this with your actual function that returns text, DataFrame, or matplotlib figure.
    """
    message_lower = user_message.lower()
    
    if "chart" in message_lower or "plot" in message_lower or "graph" in message_lower:
        # Return a matplotlib figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Sample data
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
        # Return a pandas DataFrame
        data = {
            'Quarter': ['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024'],
            'Revenue ($M)': [20500, 21300, 20860, 21200],
            'Net Income ($M)': [4600, 4800, 4500, 4700],
            'EPS ($)': [1.25, 1.30, 1.22, 1.28]
        }
        return pd.DataFrame(data)
        
    else:
        # Return text response
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
    """Convert different response types to displayable format"""
    if isinstance(response, str):
        # Text response
        return html.Div([
            html.Strong("Assistant: "),
            html.Span(response)
        ], style=custom_styles['bot_message'])
        
    elif isinstance(response, pd.DataFrame):
        # DataFrame response
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
        
    elif hasattr(response, 'savefig'):  # matplotlib figure
        # Convert matplotlib figure to base64 image
        img_buffer = io.BytesIO()
        response.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode()
        plt.close(response)  # Close figure to free memory
        
        return html.Div([
            html.Strong("Assistant: "),
            html.Br(),
            html.Img(
                src=f"data:image/png;base64,{img_base64}",
                style={'maxWidth': '100%', 'height': 'auto', 'marginTop': '10px'}
            )
        ], style=custom_styles['bot_message'])
    
    else:
        # Fallback for unknown response types
        return html.Div([
            html.Strong("Assistant: "),
            html.Span(str(response))
        ], style=custom_styles['bot_message'])

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
    """Update chat when user sends a message"""
    
    # Check if callback was triggered
    ctx = callback_context
    if not ctx.triggered or not user_input or user_input.strip() == "":
        return chat_children, "", chat_history
    
    # Add user message to chat
    user_message_div = html.Div([
        html.Strong("You: "),
        user_input
    ], style=custom_styles['user_message'])
    
    # Get bot response using your function
    bot_response = get_chatbot_response(user_input)
    bot_message_div = format_response_for_display(bot_response)
    
    # Update chat history
    new_history = chat_history + [
        {"type": "user", "content": user_input, "timestamp": datetime.now().isoformat()},
        {"type": "bot", "content": str(bot_response), "timestamp": datetime.now().isoformat()}
    ]
    
    # Add new messages to chat
    updated_chat = chat_children + [user_message_div, bot_message_div]
    
    return updated_chat, "", new_history

# Auto-scroll chat to bottom with JavaScript
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