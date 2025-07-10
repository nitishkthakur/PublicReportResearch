import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
import os

app = Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP, '/assets/custom.css'])

app.layout = dbc.Container([
    dbc.Navbar(
        dbc.Container([
            html.A(
                dbc.Row([
                    dbc.Col(html.Div("Multi-Page Dash App", style={"color": "white", "fontWeight": "bold", "fontSize": 24})),
                ], align="center", className="g-0"),
                href="/",
                style={"textDecoration": "none"},
            ),
        ]),
        color="danger",  # Red
        dark=True,
        className="mb-4"
    ),
    dash.page_container
], fluid=True)

if __name__ == "__main__":
    app.run(debug=True)
