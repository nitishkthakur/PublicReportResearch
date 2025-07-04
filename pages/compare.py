import dash
from dash import html, dcc, dash_table, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import io

dash.register_page(__name__, path="/compare", name="Compare Tab")

# Example DataFrame for demonstration (should match Output Tab)
df_output = pd.DataFrame({
    "Column 1": [1, 2, 3],
    "Column 2": ["A", "B", "C"]
})

layout = dbc.Container([
    dbc.Card([
        dbc.CardHeader("Upload and Compare", style={"backgroundColor": "#dc3545", "color": "white"}),
        dbc.CardBody([
            dcc.Upload(
                id="upload-data",
                children=html.Div([
                    "Drag and Drop or ",
                    html.A("Select CSV File")
                ]),
                style={
                    "width": "100%",
                    "height": "60px",
                    "lineHeight": "60px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "5px",
                    "textAlign": "center",
                    "margin": "10px 0"
                },
                multiple=False
            ),
            html.Div(id="compare-output")
        ])
    ])
])

@callback(
    Output("compare-output", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename")
)
def update_output(contents, filename):
    if contents is not None:
        content_type, content_string = contents.split(",")
        decoded = io.BytesIO(base64.b64decode(content_string))
        try:
            df_uploaded = pd.read_csv(decoded)
        except Exception as e:
            return html.Div(["There was an error processing this file."])
        return dbc.Row([
            dbc.Col([
                html.H5("Output Table"),
                dash_table.DataTable(
                    columns=[{"name": i, "id": i} for i in df_output.columns],
                    data=df_output.to_dict("records"),
                    style_table={"overflowX": "auto"},
                    style_header={"backgroundColor": "#dc3545", "color": "white"},
                    style_cell={"textAlign": "left"},
                )
            ], width=6),
            dbc.Col([
                html.H5("Uploaded Table"),
                dash_table.DataTable(
                    columns=[{"name": i, "id": i} for i in df_uploaded.columns],
                    data=df_uploaded.to_dict("records"),
                    style_table={"overflowX": "auto"},
                    style_header={"backgroundColor": "#6c757d", "color": "white"},
                    style_cell={"textAlign": "left"},
                )
            ], width=6)
        ])
    return None

import base64  # required for decoding
