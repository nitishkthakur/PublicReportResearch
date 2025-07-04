import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/config", name="Config Tab")

layout = dbc.Container([
    dbc.Card([
        dbc.CardHeader("Config Tab", style={"backgroundColor": "#dc3545", "color": "white"}),
        dbc.CardBody([
            dbc.Label("Config Settings"),
            dcc.Textarea(id="config-text", style={"width": "100%", "height": 100}),
            dbc.Button("Set", id="set-config", color="secondary", className="mt-3"),
            html.Div(id="config-output", className="mt-2")
        ])
    ])
])

@callback(
    Output("config-output", "children"),
    Input("set-config", "n_clicks"),
    State("config-text", "value")
)
def set_config(n_clicks, value):
    if n_clicks:
        return f"Config set to: {value}"
    return ""
