import requests
import polyline
from dash import html, Input, Output
import dash
import plotly.graph_objects as go

from database import get_database_vehicle_data
from mav_api import HEADERS, get_latest_vehicle_data
from map_view import (
    add_heading_arrows,
    get_empty_map_layout,
    get_interactive_map_layout,
)
from train_data import (
    get_bounds,
    get_marker_colors,
    get_selected_vehicle_id,
    get_seconds_since_midnight,
    get_trains,
    filter_vehicle_positions,
    seconds_to_hhmm,
)


def register_callbacks(app):
    @app.callback(
        Output("vehicle-data-store", "data"),
        Input("vehicle-data-interval", "n_intervals"),
    )
    def fetch_vehicle_data(n_intervals):
        data = get_database_vehicle_data()
        if data is None:
            data = get_latest_vehicle_data()
        return data if data is not None else dash.no_update

    @app.callback(
        Output("map-graph", "figure"),
        Output("train-info", "children"),
        Input("map-graph", "clickData"),
        Input("vehicle-data-store", "data"),
        Input("train-search", "value"),
        Input("delay-filter", "value"),
    )
    def update_map(click_data, vehicle_data, search_text, delay_filter):
        if (
            not isinstance(vehicle_data, dict)
            or "data" not in vehicle_data
            or "vehiclePositions" not in vehicle_data["data"]
        ):
            fig = go.Figure()
            fig.update_layout(**get_empty_map_layout())
            return fig, ""

        vehicle_positions = vehicle_data["data"].get("vehiclePositions")
        if not isinstance(vehicle_positions, list):
            vehicle_positions = []

        vehicle_positions = filter_vehicle_positions(
            vehicle_positions,
            search_text,
            delay_filter,
        )

        trains = get_trains(vehicle_positions)
        zoom, bounds = get_bounds(None)
        fig = go.Figure()
        selected_vehicle_id = get_selected_vehicle_id(click_data)
        marker_colors = get_marker_colors(vehicle_positions, selected_vehicle_id)

        fig.add_trace(go.Scattermap(
            lat=[train["lat"] for train in trains],
            lon=[train["lon"] for train in trains],
            mode="markers",
            marker=dict(size=20, color=marker_colors),
            text=[
                f"{train['name']}<br>Speed: {train['speed']} km/h<br>Delay: {train['delay']} sec"
                for train in trains
            ],
            customdata=[
                str(
                    vehicle.get("vehicleId")
                    or (vehicle.get("trip") or {}).get("tripShortName")
                    or "unknown"
                )
                for vehicle in vehicle_positions
                if vehicle.get("lat") and vehicle.get("lon")
            ],
            name="Trains",
        ))
        add_heading_arrows(fig, trains, bounds, zoom)

        stops_info = ""
        if click_data and "points" in click_data:
            vehicle_id = str(click_data["points"][0]["customdata"])
            train = next(
                (item for item in trains if str(item.get("vehicleId")) == vehicle_id),
                None,
            )
            if not train:
                train = next(
                    (item for item in trains if str(item.get("name")) == vehicle_id),
                    None,
                )

            if train:
                stops_info = build_train_info(fig, train)

        fig.update_layout(**get_interactive_map_layout())
        return fig, stops_info


def build_train_info(fig, train):
    stops = train["stoptimes"]
    if not stops:
        return ""

    stop_lats = [stop["stop"]["lat"] for stop in stops if stop.get("stop")]
    stop_lons = [stop["stop"]["lon"] for stop in stops if stop.get("stop")]
    stop_names = [stop["stop"]["name"] for stop in stops if stop.get("stop")]

    fig.add_trace(go.Scattermap(
        lat=stop_lats,
        lon=stop_lons,
        mode="markers+text",
        marker=dict(size=15, color="red"),
        text=stop_names,
        name="Stops",
        textposition="top right",
    ))

    gtfs_id = train.get("gtfsId")
    if gtfs_id:
        url = (
            "https://emma.mav.hu/"
            "otp2-backend/otp/routers/default/index/trips/"
            f"{gtfs_id}/geometry"
        )
        try:
            response = requests.get(url, timeout=5, headers=HEADERS)
            if response.ok:
                encoded_points = response.json().get("points")
                if encoded_points:
                    coordinates = polyline.decode(encoded_points)
                    route_lats, route_lons = zip(*coordinates)
                    fig.add_trace(go.Scattermap(
                        lat=route_lats,
                        lon=route_lons,
                        mode="lines",
                        line=dict(width=3, color="orange"),
                        name="Route",
                    ))
        except Exception:
            pass

    now_sec = get_seconds_since_midnight()
    next_stop_idx = None
    for index, stop in enumerate(stops):
        arrival = int(stop["realtimeArrival"]) if stop.get("realtimeArrival") else None
        departure = int(stop["realtimeDeparture"]) if stop.get("realtimeDeparture") else None
        if (arrival and arrival > now_sec) or (departure and departure > now_sec):
            next_stop_idx = index
            break

    if next_stop_idx is not None:
        delay_value = stops[next_stop_idx].get("arrivalDelay")
    else:
        delay_value = stops[-1].get("arrivalDelay")

    delay_min = f"{int(delay_value)//60:+} min" if delay_value is not None else ""
    delay_color = "#e67e22" if delay_value and int(delay_value) > 0 else "#2ecc40"

    stop_rows = []
    for index, stop in enumerate(stops):
        if not stop.get("stop"):
            continue

        stop_rows.append(html.Div([
            build_arrival_time(stop),
            build_departure_time(stop),
            html.Div(
                stop["stop"]["name"],
                title=stop["stop"]["name"],
                style={
                    "display": "inline-block",
                    "marginLeft": "8px",
                    "minWidth": "90px",
                    "maxWidth": "180px",
                    "whiteSpace": "nowrap",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "verticalAlign": "middle",
                },
            ),
        ], style={
            "marginBottom": "1px",
            "background": "#d6eaf8" if index == next_stop_idx else "none",
            "borderRadius": "4px",
            "whiteSpace": "nowrap",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "display": "flex",
            "alignItems": "center",
            "minHeight": "22px",
        }))

        if next_stop_idx is not None and index == next_stop_idx - 1:
            stop_rows.append(html.Div(style={
                "height": "2px",
                "background": "#2980b9",
                "margin": "2px 0 2px 0",
                "borderRadius": "2px",
            }))

    route_name = train["route"].get("longName", "")
    train_name = train["name"]
    next_stop_name = (
        stops[next_stop_idx]["stop"]["name"]
        if next_stop_idx is not None
        else "End of route"
    )

    return html.Div([
        html.Div([
            html.Span(
                f"{route_name} - {train_name}",
                style={"fontWeight": "bold", "fontSize": "1.2em", "marginRight": "8px"},
            ),
            html.Span(
                f"({stop_names[0]} \u2192 {stop_names[-1]})",
                style={"color": "#555", "fontSize": "1em"},
            ),
        ], style={"marginBottom": "10px"}),
        html.Div([
            html.B(
                f"Next stop: {next_stop_name}" if next_stop_idx is not None else "End of route",
                style={"color": "#2980b9", "fontSize": "1em"},
            ),
            html.Span(
                delay_min,
                style={"color": delay_color, "fontWeight": "bold", "marginLeft": "8px"},
            ) if delay_min else None,
        ], style={"marginBottom": "8px", "display": "flex", "alignItems": "center"}),
        html.Div([
            html.Div("Arrivals", style={"display": "inline-block", "width": "90px", "color": "#888", "fontSize": "0.9em"}),
            html.Div("Departures", style={"display": "inline-block", "width": "100px", "color": "#888", "fontSize": "0.9em"}),
            html.Div("Stop", style={"display": "inline-block", "marginLeft": "10px", "color": "#888", "fontSize": "0.9em"}),
        ], style={"marginBottom": "4px"}),
        html.Div(
            stop_rows,
            style={"maxHeight": "350px", "overflowY": "auto", "overflowX": "auto", "whiteSpace": "nowrap"},
        ),
    ], style={"fontFamily": "Roboto, Arial", "fontSize": "1em"})


def build_arrival_time(stop):
    scheduled = stop.get("scheduledArrival")
    realtime = stop.get("realtimeArrival")
    differs = realtime and scheduled and int(realtime) != int(scheduled)
    color = (
        "#e74c3c"
        if realtime and scheduled and int(realtime) > int(scheduled)
        else "#2ecc40"
    )
    return html.Span([
        html.Span(
            seconds_to_hhmm(scheduled),
            style={
                "textDecoration": "line-through",
                "color": "#888",
                "marginRight": "4px",
                "whiteSpace": "nowrap",
            },
        ) if differs else None,
        html.Span(
            seconds_to_hhmm(realtime),
            style={"color": color, "fontWeight": "bold", "whiteSpace": "nowrap"},
        ) if realtime else html.Span(
            seconds_to_hhmm(scheduled),
            style={"color": "#2ecc40", "fontWeight": "bold", "whiteSpace": "nowrap"},
        ),
    ], style={"display": "inline-block", "width": "104px", "whiteSpace": "nowrap"})


def build_departure_time(stop):
    scheduled = stop.get("scheduledDeparture")
    realtime = stop.get("realtimeDeparture")
    differs = realtime and scheduled and int(realtime) != int(scheduled)
    color = (
        "#e74c3c"
        if realtime and scheduled and int(realtime) > int(scheduled)
        else "#2ecc40"
    )
    return html.Span([
        html.Span(
            seconds_to_hhmm(scheduled),
            style={
                "textDecoration": "line-through",
                "color": "#888",
                "marginRight": "4px",
                "whiteSpace": "nowrap",
            },
        ) if differs else None,
        html.Span(
            seconds_to_hhmm(realtime),
            style={"color": color, "fontWeight": "bold", "whiteSpace": "nowrap"},
        ) if realtime else html.Span(
            seconds_to_hhmm(scheduled),
            style={"color": "#2ecc40", "fontWeight": "bold", "whiteSpace": "nowrap"},
        ),
    ], style={"display": "inline-block", "width": "104px", "whiteSpace": "nowrap"})
