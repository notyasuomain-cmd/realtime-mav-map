from dash import dcc, html


EXTERNAL_STYLESHEETS = [
    {
        "href": "https://fonts.googleapis.com/css?family=Roboto",
        "rel": "stylesheet",
    },
    {
        "href": (
            "https://cdnjs.cloudflare.com/ajax/libs/"
            "normalize/8.0.1/normalize.min.css"
        ),
        "rel": "stylesheet",
    },
]


INDEX_STRING = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            html, body, #root, .app-container { height: 100%; width: 100%; margin: 0; padding: 0; }
            #map-graph { height: 100vh !important; width: 100vw !important; }
            #train-controls {
                position: absolute;
                top: 20px;
                left: 20px;
                z-index: 1000;
                display: flex;
                gap: 8px;
                background: rgba(30,30,30,0.96);
                padding: 10px;
                border-radius: 12px;
                border: 1px solid #2980b9;
            }
            #train-controls input {
                width: 220px;
                padding: 8px 10px;
                border-radius: 8px;
                border: none;
            }
            #delay-filter { width: 150px; }
            #delay-filter .Select-control { height: 34px; }
            #train-info {
                position: absolute;
                bottom: 30px;
                left: 30px;
                background: rgba(30,30,30,0.96);
                color: #fff;
                padding: 28px 28px 24px 28px;
                border-radius: 24px;
                z-index: 1000;
                max-width: 700px;
                min-width: 420px;
                font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
                font-size: 1.18em;
                box-shadow: 0 8px 32px rgba(0,0,0,0.25);
                border: 2px solid #2980b9;
            }
        </style>
        <link href="https://fonts.googleapis.com/css?family=Montserrat:400,700&display=swap" rel="stylesheet">
    </head>
    <body>
        <div id="root" class="app-container">{%app_entry%}</div>
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>
"""


def create_layout(initial_vehicle_data=None):
    return html.Div([
        html.Div([
            dcc.Input(
                id="train-search",
                type="text",
                placeholder="Vonat vagy célállomás...",
                debounce=True,
            ),
            dcc.Dropdown(
                id="delay-filter",
                options=[
                    {"label": "Minden vonat", "value": "all"},
                    {"label": "Pontosan érkezik", "value": "on_time"},
                    {"label": "5 percig késik", "value": "small_delay"},
                    {"label": "5 percen túl késik", "value": "long_delay"},
                ],
                value="all",
                clearable=False,
            ),
        ], id="train-controls"),
        dcc.Graph(
            id="map-graph",
            style={"height": "100vh", "width": "100vw"},
            config={"scrollZoom": True},
        ),
        html.Div(id="train-info", style={"display": "block"}),
        dcc.Store(id="vehicle-data-store", data=initial_vehicle_data),
        dcc.Interval(
            id="vehicle-data-interval",
            interval=60 * 1000,
            n_intervals=0,
        ),
    ], style={
        "height": "100vh",
        "width": "100vw",
        "position": "relative",
        "overflow": "hidden",
    })
