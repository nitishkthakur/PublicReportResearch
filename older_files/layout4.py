from dash import dcc, html
import dash_bootstrap_components as dbc
WF_RED = "#D71921"
WF_GOLD = "#FFCD41"
WF_DARK_RED = "#B71C1C"

DEEP_BLUE = "#1A237E"  # Indigo 900, a deep blue

custom_styles = {
    'navbar': {
        'backgroundColor': DEEP_BLUE,
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
        'backgroundColor': DEEP_BLUE,
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
        'border': f'1px solid {DEEP_BLUE}',
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
        'border': f'2px solid {DEEP_BLUE}',
        'padding': '12px 20px',
        'fontSize': '16px'
    },
    'submit_button': {
        'backgroundColor': DEEP_BLUE,
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

def get_layout():
    return html.Div([
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