import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/chat", name="Chat Page")

layout = dbc.Container([
    dbc.Card([
        dbc.CardHeader("Chat Page", style={"backgroundColor": "#dc3545", "color": "white"}),
        dbc.CardBody([
            dbc.Form([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("System Instructions"),
                        dcc.Textarea(id="system-instructions", style={"width": "100%"}),
                    ], width=6),
                    dbc.Col([
                        dbc.Label("User Instructions"),
                        dcc.Textarea(id="user-instructions", style={"width": "100%"}),
                    ], width=6),
                ]),
                dbc.Button("Submit", id="submit-chat", color="secondary", className="mt-3"),
            ])
        ])
    ], className="mb-4")
])

# You can add callbacks here if needed
