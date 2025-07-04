import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import pandas as pd

dash.register_page(__name__, path="/output", name="Output Tab")

# Example DataFrame for demonstration
df = pd.DataFrame({
    "Column 1": [1, 2, 3],
    "Column 2": ["A", "B", "C"]
})

layout = dbc.Container([
    dbc.Card([
        dbc.CardHeader("Tabular Output", style={"backgroundColor": "#dc3545", "color": "white"}),
        dbc.CardBody([
            dash_table.DataTable(
                id="output-table",
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.to_dict("records"),
                style_table={"overflowX": "auto"},
                style_header={"backgroundColor": "#dc3545", "color": "white"},
                style_cell={"textAlign": "left"},
            )
        ])
    ])
])
