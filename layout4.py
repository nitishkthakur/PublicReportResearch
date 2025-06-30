from dash import dcc, html
import dash_bootstrap_components as dbc
WF_RED = "#D71921"
WF_GOLD = "#FFCD41"
WF_DARK_RED = "#B71C1C"

PLEASANT_RED = "#C62828"  # Material Design Red 700
LIGHT_RED = "#FFEBEE"     # Material Design Red 50
DARK_RED = "#B71C1C"      # Material Design Red 900

custom_styles = {
    'navbar': {
        'backgroundColor': PLEASANT_RED,
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
    'sidebar': {
        'position': 'fixed',
        'top': '70px',
        'left': '0',
        'width': '250px',
        'height': 'calc(100vh - 70px)',
        'backgroundColor': '#f8f9fa',
        'borderRight': f'2px solid {PLEASANT_RED}',
        'padding': '20px',
        'overflowY': 'auto',
        'zIndex': '1000'
    },
    'sidebar_header': {
        'color': PLEASANT_RED,
        'fontSize': '18px',
        'fontWeight': 'bold',
        'marginBottom': '15px',
        'borderBottom': f'2px solid {PLEASANT_RED}',
        'paddingBottom': '8px'
    },
    'sidebar_section': {
        'marginBottom': '25px'
    },
    'sidebar_section_title': {
        'color': PLEASANT_RED,
        'fontSize': '16px',
        'fontWeight': '600',
        'marginBottom': '12px',
        'paddingLeft': '5px',
        'textTransform': 'uppercase',
        'letterSpacing': '0.5px'
    },
    'sidebar_item': {
        'padding': '10px 15px',
        'marginBottom': '6px',
        'backgroundColor': 'white',
        'border': f'1px solid #e0e6ed',
        'borderRadius': '6px',
        'cursor': 'pointer',
        'transition': 'all 0.2s ease',
        'color': '#495057',
        'fontWeight': '500',
        'fontSize': '14px',
        'borderLeft': f'4px solid transparent'
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
        'backgroundColor': PLEASANT_RED,
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
        'border': f'1px solid {PLEASANT_RED}',
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
        'border': f'2px solid {PLEASANT_RED}',
        'padding': '12px 20px',
        'fontSize': '16px'
    },
    'submit_button': {
        'backgroundColor': PLEASANT_RED,
        'color': 'white',
        'border': 'none',
        'borderRadius': '25px',
        'padding': '12px 25px',
        'fontSize': '16px',
        'fontWeight': 'bold',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease'
    },
    'main_content': {
        'marginLeft': '270px',
        'padding': '20px'
    },
    'bank_selector_container': {
        'marginBottom': '20px',
        'padding': '15px',
        'backgroundColor': 'white',
        'borderRadius': '8px',
        'border': f'1px solid {PLEASANT_RED}',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'
    },
    'bank_selector_title': {
        'color': PLEASANT_RED,
        'fontSize': '16px',
        'fontWeight': '600',
        'marginBottom': '12px',
        'textAlign': 'center'
    },
    'bank_scroll_container': {
        'display': 'flex',
        'overflowX': 'auto',
        'gap': '10px',
        'padding': '5px 0',
        'scrollbarWidth': 'thin',
        'scrollbarColor': f'{PLEASANT_RED} #f1f1f1'
    },
    'bank_button': {
        'minWidth': '140px',
        'padding': '8px 16px',
        'backgroundColor': 'white',
        'border': f'2px solid {PLEASANT_RED}',
        'borderRadius': '20px',
        'color': PLEASANT_RED,
        'fontSize': '14px',
        'fontWeight': '500',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease',
        'whiteSpace': 'nowrap',
        'textAlign': 'center'
    }
}

def get_layout():
    return html.Div([
        html.Div([
            html.H1("Earnings Research", style=custom_styles['title'])
        ], style=custom_styles['navbar']),

        # Sidebar
        html.Div([
            html.H3("Navigation", style=custom_styles['sidebar_header']),
            
            # Section 1: Earnings Analysis
            html.Div([
                html.Div("Earnings Analysis", style=custom_styles['sidebar_section_title']),
                html.Div([
                    html.Div("Chat", style=custom_styles['sidebar_item'], id="nav-chat"),
                    html.Div("KPI Overview", style=custom_styles['sidebar_item'], id="nav-kpi"),
                    html.Div("Compare Reports", style=custom_styles['sidebar_item'], id="nav-compare"),
                ])
            ], style=custom_styles['sidebar_section']),
            
            # Section 2: Metrics Analyser
            html.Div([
                html.Div("Metrics Analyser", style=custom_styles['sidebar_section_title']),
                html.Div([
                    html.Div("Revenue", style=custom_styles['sidebar_item'], id="nav-revenue"),
                    html.Div("Earnings Per Share", style=custom_styles['sidebar_item'], id="nav-eps"),
                ])
            ], style=custom_styles['sidebar_section']),
            
        ], style=custom_styles['sidebar']),

        # Main content area
        html.Div([
            dbc.Container([
                html.Br(),

                # Bank Selector Section
                html.Div([
                    html.Div("Select Bank for Earnings Report", style=custom_styles['bank_selector_title']),
                    html.Div([
                        html.Button("JPMorgan Chase", style=custom_styles['bank_button'], id="bank-jpm", n_clicks=0),
                        html.Button("Bank of America", style=custom_styles['bank_button'], id="bank-boa", n_clicks=0),
                        html.Button("Wells Fargo", style=custom_styles['bank_button'], id="bank-wfc", n_clicks=0),
                        html.Button("Citigroup", style=custom_styles['bank_button'], id="bank-citi", n_clicks=0),
                        html.Button("Goldman Sachs", style=custom_styles['bank_button'], id="bank-gs", n_clicks=0),
                        html.Button("Morgan Stanley", style=custom_styles['bank_button'], id="bank-ms", n_clicks=0),
                        html.Button("U.S. Bancorp", style=custom_styles['bank_button'], id="bank-usb", n_clicks=0),
                        html.Button("PNC Financial", style=custom_styles['bank_button'], id="bank-pnc", n_clicks=0),
                        html.Button("Truist Financial", style=custom_styles['bank_button'], id="bank-tfc", n_clicks=0),
                        html.Button("Charles Schwab", style=custom_styles['bank_button'], id="bank-schw", n_clicks=0),
                    ], style=custom_styles['bank_scroll_container'])
                ], style=custom_styles['bank_selector_container']),

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
        ], style=custom_styles['main_content'])
    ])