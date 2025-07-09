import json
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import requests
import polyline
import math
import datetime
import os

# Custom CSS for full screen
external_stylesheets = [
    {
        'href': 'https://fonts.googleapis.com/css?family=Roboto',
        'rel': 'stylesheet'
    },
    {
        'href': 'https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css',
        'rel': 'stylesheet'
    }
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.index_string = '''
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
'''

def get_latest_vehicle_data():
    """Fetch latest vehicle data from the API. Returns dict or None on error."""
    url = "https://emma.mav.hu/otp2-backend/otp/routers/default/index/graphql"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
    }
    query = '''
        {
            vehiclePositions(
              swLat: 45.5,
              swLon: 16.1,
              neLat: 48.7,
              neLon: 22.8,
              modes: [RAIL, RAIL_REPLACEMENT_BUS]
            ) {
              trip {
                gtfsId
                tripShortName
                tripHeadsign
                trainCategoryName
                trainName
                route {
                  id
                  gtfsId
                  shortName
                  longName
                  textColor
                  color
                }
                stoptimes {
                stop {
                  name
                  lat
                  lon
                  platformCode
                }
                scheduledArrival            
                realtimeArrival            
                arrivalDelay
                scheduledDeparture            
                realtimeDeparture
               }
              }
              vehicleId
              lat
              lon
              label
              speed
              heading
              prevOrCurrentStop { 
                scheduledArrival
                realtimeArrival
                arrivalDelay
                scheduledDeparture
                realtimeDeparture
                departureDelay
              }
            }
        }'''
    try:
        response = requests.post(url, headers=headers, data=json.dumps({"query": query}), timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception during fetch: {e}")
        return None

# On startup, create vehicle_positions.json if missing
if not os.path.exists('vehicle_positions.json'):
    data = get_latest_vehicle_data()
    if data is not None:
        with open('vehicle_positions.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    else:
        # Write empty structure to avoid crash
        with open('vehicle_positions.json', 'w', encoding='utf-8') as f:
            f.write('{"data": {"vehiclePositions": []}}')

# Load vehicle positions
with open('vehicle_positions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

vehicle_positions = data['data']['vehiclePositions']

def get_train_info(vehicle):
    trip = vehicle.get('trip', {})
    name = trip.get('tripShortName') or vehicle.get('vehicleId', 'Unknown')
    speed = vehicle.get('speed', 'N/A')
    delay = vehicle.get('prevOrCurrentStop', {}).get('arrivalDelay', 'N/A')
    lat = vehicle.get('lat')
    lon = vehicle.get('lon')
    gtfsId = trip.get('gtfsId')
    route = trip.get('route', {})
    vehicleId = vehicle.get('vehicleId') 
    return {
        'name': name,
        'lat': lat,
        'lon': lon,
        'speed': speed,
        'delay': delay,
        'stoptimes': trip.get('stoptimes', []),
        'gtfsId': gtfsId,
        'route': route,
        'vehicleId': vehicleId
    }

trains = [get_train_info(v) for v in vehicle_positions if v.get('lat') and v.get('lon')]

app.layout = html.Div([
    dcc.Graph(id='map-graph', style={'height': '100vh', 'width': '100vw'}, config={'scrollZoom': True}),
    html.Div(id='train-info', style={'display': 'block'}),
    dcc.Store(id='vehicle-data-store'),
    dcc.Interval(id='vehicle-data-interval', interval=60*1000, n_intervals=0)
], style={'height': '100vh', 'width': '100vw', 'position': 'relative', 'overflow': 'hidden'})

@app.callback(
    Output('vehicle-data-store', 'data'),
    Input('vehicle-data-interval', 'n_intervals')
)
def fetch_vehicle_data(n_intervals):
    print("called")
    data = get_latest_vehicle_data()
    if data is not None:
        return data
    else:
        return dash.no_update

def get_marker_colors(vehicle_positions, selected_vehicle_id):
    """Return a list of marker colors, orange for selected, blue for others."""
    colors = []
    for v in vehicle_positions:
        vid = str(v.get('vehicleId') or v.get('trip', {}).get('tripShortName') or 'unknown')
        if selected_vehicle_id and vid == selected_vehicle_id:
            colors.append('#e67e22')
        else:
            colors.append('blue')
    return colors

def add_heading_arrows(fig, trains, data, bounds, zoom):
    """Add heading arrows to the map for visible trains if zoomed in enough."""
    if zoom < 12:
        return
    arrow_lines = []
    arrow_heads = {'lat': [], 'lon': [], 'customdata': [], 'text': []}
    for i, t in enumerate(trains):
        lat1 = t['lat']
        lon1 = t['lon']
        if bounds:
            if not (bounds['lat_min'] <= lat1 <= bounds['lat_max'] and bounds['lon_min'] <= lon1 <= bounds['lon_max']):
                continue
        heading = t.get('heading')
        if heading is None and 'vehiclePositions' in data['data']:
            for v in data['data']['vehiclePositions']:
                if v.get('lat') == lat1 and v.get('lon') == lon1:
                    heading = v.get('heading')
                    break
        if heading is not None:
            length = 0.003
            angle_rad = math.radians(heading)
            dlat = length * math.cos(angle_rad)
            dlon = length * math.sin(angle_rad) / math.cos(math.radians(lat1))
            lat2 = lat1 + dlat
            lon2 = lon1 + dlon
            arrow_lines.append(((lat1, lon1), (lat2, lon2)))
            arrow_heads['lat'].append(lat2)
            arrow_heads['lon'].append(lon2)
            arrow_heads['customdata'].append(i)
            arrow_heads['text'].append(f"{t['name']} heading: {heading}")
    for (lat1, lon1), (lat2, lon2) in arrow_lines:
        fig.add_trace(go.Scattermapbox(
            lat=[lat1, lat2],
            lon=[lon1, lon2],
            mode='lines',
            line=dict(width=2, color='black'),
            hoverinfo='skip',
            showlegend=False,
            name='HeadingLine',
        ))
    if arrow_heads['lat']:
        fig.add_trace(go.Scattermapbox(
            lat=arrow_heads['lat'],
            lon=arrow_heads['lon'],
            mode='markers',
            marker=dict(size=16, color='black', symbol='triangle', allowoverlap=True),
            text=arrow_heads['text'],
            customdata=arrow_heads['customdata'],
            showlegend=False,
            hoverinfo='skip',
            name='HeadingArrow'
        ))

def get_selected_vehicle_id(clickData):
    if clickData and 'points' in clickData:
        return str(clickData['points'][0]['customdata'])
    return None

def get_bounds(relayoutData):
    zoom = 7
    bounds = None
    if relayoutData:
        if 'mapbox.zoom' in relayoutData:
            zoom = relayoutData['mapbox.zoom']
        if 'mapbox._derived' in relayoutData:
            derived = relayoutData['mapbox._derived']
            if 'coordinates' in derived:
                coords = derived['coordinates']
                lats = [c[1] for c in coords]
                lons = [c[0] for c in coords]
                bounds = {
                    'lat_min': min(lats),
                    'lat_max': max(lats),
                    'lon_min': min(lons),
                    'lon_max': max(lons)
                }
    return zoom, bounds

@app.callback(
    Output('map-graph', 'figure'),
    Output('train-info', 'children'),
    Input('map-graph', 'clickData'),
    Input('map-graph', 'relayoutData'),
    State('map-graph', 'figure'),
    Input('vehicle-data-store', 'data')
)
def update_map(clickData, relayoutData, prev_fig, vehicle_data):
    if not isinstance(vehicle_data, dict) or 'data' not in vehicle_data or 'vehiclePositions' not in vehicle_data['data']:
        fig = go.Figure()
        fig.update_layout(
            mapbox=dict(
                style='open-street-map',
                center=dict(lat=47.1625, lon=19.5033),
                zoom=7
            ),
            margin={"r":0,"t":0,"l":0,"b":0},
            showlegend=False,
            height=900,
            uirevision=True
        )
        return fig, ''
    data = vehicle_data
    vehicle_positions = data['data'].get('vehiclePositions')
    if not isinstance(vehicle_positions, list):
        vehicle_positions = []
    trains = [get_train_info(v) for v in vehicle_positions if v.get('lat') and v.get('lon')]
    zoom, bounds = get_bounds(relayoutData)
    fig = go.Figure()
    selected_vehicle_id = get_selected_vehicle_id(clickData)
    marker_colors = get_marker_colors(vehicle_positions, selected_vehicle_id)
    fig.add_trace(go.Scattermapbox(
        lat=[t['lat'] for t in trains],
        lon=[t['lon'] for t in trains],
        mode='markers',
        marker=dict(size=20, color=marker_colors),
        text=[f"{t['name']}<br>Speed: {t['speed']} km/h<br>Delay: {t['delay']} sec" for t in trains],
        customdata=[str(v.get('vehicleId') or v.get('trip', {}).get('tripShortName') or 'unknown') for v in vehicle_positions if v.get('lat') and v.get('lon')],
        name='Trains'
    ))
    add_heading_arrows(fig, trains, data, bounds, zoom)
    stops_info = ''
    if clickData and 'points' in clickData:
        vehicle_id = str(clickData['points'][0]['customdata'])
        print('Clicked vehicle_id:', vehicle_id)
        train = next((t for t in trains if str(t.get('vehicleId')) == vehicle_id), None)
        if not train:
            train = next((t for t in trains if str(t.get('name')) == vehicle_id), None)
        if not train:
            print('No matching train found for vehicle_id:', vehicle_id)
            fig.update_layout(
                mapbox=dict(
                    style='open-street-map',
                    center=dict(lat=47.1625, lon=19.5033),
                    zoom=zoom
                ),
                margin={"r":0,"t":0,"l":0,"b":0},
                showlegend=False,
                height=900,
                uirevision=True
            )
            return fig, stops_info
        stops = train['stoptimes']
        gtfsId = train.get('gtfsId')
        if stops:
            stop_lats = [s['stop']['lat'] for s in stops if s.get('stop')]
            stop_lons = [s['stop']['lon'] for s in stops if s.get('stop')]
            stop_names = [s['stop']['name'] for s in stops if s.get('stop')]
            fig.add_trace(go.Scattermapbox(
                lat=stop_lats,
                lon=stop_lons,
                mode='markers+text',
                marker=dict(size=15, color='red'),
                text=stop_names,
                name='Stops',
                textposition='top right'
            ))
            print(gtfsId)
            # Fetch and decode polyline for the route
            if gtfsId:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
                }
                url = f'https://emma.mav.hu//otp2-backend/otp/routers/default/index/trips/{gtfsId}/geometry'
                try:
                    resp = requests.get(url, timeout=5, headers=headers)
                    if resp.ok:
                        poly = resp.json().get('points')
                        if poly:
                            coords = polyline.decode(poly)
                            route_lats, route_lons = zip(*coords)
                            fig.add_trace(go.Scattermapbox(
                                lat=route_lats,
                                lon=route_lons,
                                mode='lines',
                                line=dict(width=3, color='orange'),
                                name='Route'
                            ))
                except Exception as e:
                    pass
            # Find next stop (first with realtimeArrival or realtimeDeparture > now)
            now_sec = get_seconds_since_midnight()
            next_stop_idx = None
            for idx, s in enumerate(stops):
                arr = s.get('realtimeArrival')
                dep = s.get('realtimeDeparture')
                arr = int(arr) if arr else None
                dep = int(dep) if dep else None
                if (arr and arr > now_sec) or (dep and dep > now_sec):
                    next_stop_idx = idx
                    break
            # Get delay for next stop (or last stop if at end)
            if next_stop_idx is not None:
                delay_val = stops[next_stop_idx].get('arrivalDelay')
            else:
                delay_val = stops[-1].get('arrivalDelay')
            delay_min = f"{int(delay_val)//60:+} min" if delay_val is not None else ''
            delay_color = '#e67e22' if delay_val and int(delay_val) > 0 else '#2ecc40'
            # Build styled stop list for info panel
            stop_rows = []
            for i, s in enumerate(stops):
                if not s.get('stop'):
                    continue
                stop_rows.append(
                    html.Div([
                        # Arrival (show both scheduled and realtime)
                        (lambda s, i: (
                            html.Span([
                                html.Span(seconds_to_hhmm(s.get('scheduledArrival')), style={'textDecoration': 'line-through', 'color': '#888', 'marginRight': '4px', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'minWidth': '44px', 'maxWidth': '56px'}) if s.get('realtimeArrival') and s.get('scheduledArrival') and int(s.get('realtimeArrival')) != int(s.get('scheduledArrival')) else None,
                                html.Span(seconds_to_hhmm(s.get('realtimeArrival')), style={'color': '#e74c3c' if s.get('realtimeArrival') and s.get('scheduledArrival') and int(s.get('realtimeArrival')) > int(s.get('scheduledArrival')) else '#2ecc40', 'fontWeight': 'bold', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'minWidth': '44px', 'maxWidth': '56px'}) if s.get('realtimeArrival') else html.Span(seconds_to_hhmm(s.get('scheduledArrival')), style={'color': '#2ecc40', 'fontWeight': 'bold', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'minWidth': '44px', 'maxWidth': '56px'})
                            ], style={'display': 'inline-block', 'width': '104px', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis'})
                        ))(s, i),
                        # Departure (show both scheduled and realtime)
                        (lambda s, i: (
                            html.Span([
                                html.Span(seconds_to_hhmm(s.get('scheduledDeparture')), style={'textDecoration': 'line-through', 'color': '#888', 'marginRight': '4px', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'minWidth': '44px', 'maxWidth': '56px'}) if s.get('realtimeDeparture') and s.get('scheduledDeparture') and int(s.get('realtimeDeparture')) != int(s.get('scheduledDeparture')) else None,
                                html.Span(seconds_to_hhmm(s.get('realtimeDeparture')), style={'color': '#e74c3c' if s.get('realtimeDeparture') and s.get('scheduledDeparture') and int(s.get('realtimeDeparture')) > int(s.get('scheduledDeparture')) else '#2ecc40', 'fontWeight': 'bold', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'minWidth': '44px', 'maxWidth': '56px'}) if s.get('realtimeDeparture') else html.Span(seconds_to_hhmm(s.get('scheduledDeparture')), style={'color': '#2ecc40', 'fontWeight': 'bold', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'minWidth': '44px', 'maxWidth': '56px'})
                            ], style={'display': 'inline-block', 'width': '104px', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis'})
                        ))(s, i),
                        # Stop name
                        html.Div(s['stop']['name'], title=s['stop']['name'], style={'display': 'inline-block', 'marginLeft': '8px', 'minWidth': '90px', 'maxWidth': '180px', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'verticalAlign': 'middle'}),
                    ], style={'marginBottom': '1px', 'background': '#d6eaf8' if i == next_stop_idx else 'none', 'borderRadius': '4px', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'display': 'flex', 'alignItems': 'center', 'minHeight': '22px'})
                )
                # Insert a line after the last reached stop
                if next_stop_idx is not None and i == next_stop_idx - 1:
                    stop_rows.append(html.Div(style={'height': '2px', 'background': '#2980b9', 'margin': '2px 0 2px 0', 'borderRadius': '2px'}))
            stops_info = html.Div([
                html.Div([
                    html.Span(train['route']['longName'] + " - " + train['name'], style={'fontWeight': 'bold', 'fontSize': '1.2em', 'marginRight': '8px'}),
                    html.Span(f"({stop_names[0]} → {stop_names[-1]})", style={'color': '#555', 'fontSize': '1em'})
                ], style={'marginBottom': '10px'}),
                html.Div([
                    html.B(
                        (f"Next stop: {stops[next_stop_idx]['stop']['name']}" if next_stop_idx is not None else "End of route"),
                        style={'color': '#2980b9', 'fontSize': '1em'}
                    ),
                    html.Span(delay_min, style={'color': delay_color, 'fontWeight': 'bold', 'marginLeft': '8px'}) if delay_min else None
                ], style={'marginBottom': '8px', 'display': 'flex', 'alignItems': 'center'}),
                html.Div([
                    html.Div('Arrivals', style={'display': 'inline-block', 'width': '90px', 'color': '#888', 'fontSize': '0.9em'}),
                    html.Div('Departures', style={'display': 'inline-block', 'width': '100px', 'color': '#888', 'fontSize': '0.9em'}),
                    html.Div('Stop', style={'display': 'inline-block', 'marginLeft': '10px', 'color': '#888', 'fontSize': '0.9em'}),
                ], style={'marginBottom': '4px'}),
                html.Div(stop_rows, style={'maxHeight': '350px', 'overflowY': 'auto', 'overflowX': 'auto', 'whiteSpace': 'nowrap'}),
            ], style={'fontFamily': 'Roboto, Arial', 'fontSize': '1em'})
    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            center=dict(lat=47.1625, lon=19.5033),
            zoom=zoom
        ),
        margin={"r":0,"t":0,"l":0,"b":0},
        showlegend=False,
        height=900,
        uirevision=True
    )
    return fig, stops_info

def seconds_to_hhmm(seconds):
    if seconds is None or seconds == '':
        return ''
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:02}:{minutes:02}"
    except Exception:
        return ''

def get_seconds_since_midnight():
    now = datetime.datetime.now()
    return now.hour * 3600 + now.minute * 60 + now.second

if __name__ == '__main__':
    app.run()
