import math

import plotly.graph_objects as go


def add_heading_arrows(fig, trains, bounds, zoom):
    if zoom < 12:
        return

    arrow_lines = []
    arrow_heads = {"lat": [], "lon": [], "customdata": [], "text": []}

    for index, train in enumerate(trains):
        lat1 = train["lat"]
        lon1 = train["lon"]
        if bounds and not (
            bounds["lat_min"] <= lat1 <= bounds["lat_max"]
            and bounds["lon_min"] <= lon1 <= bounds["lon_max"]
        ):
            continue

        heading = train.get("heading")
        if heading is None:
            continue

        length = 0.003
        angle_rad = math.radians(heading)
        dlat = length * math.cos(angle_rad)
        dlon = length * math.sin(angle_rad) / math.cos(math.radians(lat1))
        lat2 = lat1 + dlat
        lon2 = lon1 + dlon
        arrow_lines.append(((lat1, lon1), (lat2, lon2)))
        arrow_heads["lat"].append(lat2)
        arrow_heads["lon"].append(lon2)
        arrow_heads["customdata"].append(index)
        arrow_heads["text"].append(f"{train['name']} heading: {heading}")

    for (lat1, lon1), (lat2, lon2) in arrow_lines:
        fig.add_trace(go.Scattermap(
            lat=[lat1, lat2],
            lon=[lon1, lon2],
            mode="lines",
            line=dict(width=2, color="black"),
            hoverinfo="skip",
            showlegend=False,
            name="HeadingLine",
        ))

    if arrow_heads["lat"]:
        fig.add_trace(go.Scattermap(
            lat=arrow_heads["lat"],
            lon=arrow_heads["lon"],
            mode="markers",
            marker=dict(size=16, color="black", symbol="triangle", allowoverlap=True),
            text=arrow_heads["text"],
            customdata=arrow_heads["customdata"],
            showlegend=False,
            hoverinfo="skip",
            name="HeadingArrow",
        ))


def get_empty_map_layout(zoom=7):
    return {
        "map": {
            "style": "open-street-map",
            "center": {"lat": 47.1625, "lon": 19.5033},
            "zoom": zoom,
        },
        "margin": {"r": 0, "t": 0, "l": 0, "b": 0},
        "showlegend": False,
        "height": 900,
        "uirevision": True,
    }


def get_interactive_map_layout():
    return {
        "map": {
            "style": "open-street-map",
        },
        "margin": {"r": 0, "t": 0, "l": 0, "b": 0},
        "showlegend": False,
        "height": 900,
        "uirevision": "map-position",
    }
