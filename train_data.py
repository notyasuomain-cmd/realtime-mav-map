from datetime import datetime


def get_train_info(vehicle):
    trip = vehicle.get("trip") or {}
    prev_or_current_stop = vehicle.get("prevOrCurrentStop") or {}
    name = (
        trip.get("tripShortName")
        or trip.get("routeShortName")
        or trip.get("tripHeadsign")
        or vehicle.get("label")
        or vehicle.get("vehicleId")
        or "Unknown"
    )
    return {
        "name": name,
        "lat": vehicle.get("lat"),
        "lon": vehicle.get("lon"),
        "speed": vehicle.get("speed", "N/A"),
        "delay": prev_or_current_stop.get("arrivalDelay", "N/A"),
        "stoptimes": trip.get("stoptimes") or [],
        "gtfsId": trip.get("gtfsId"),
        "route": trip.get("route") or {},
        "vehicleId": vehicle.get("vehicleId"),
        "heading": vehicle.get("heading"),
    }


def get_trains(vehicle_positions):
    return [
        get_train_info(vehicle)
        for vehicle in vehicle_positions
        if vehicle.get("lat") and vehicle.get("lon")
    ]


def filter_vehicle_positions(vehicle_positions, search_text=None, delay_filter="all"):
    search_text = (search_text or "").strip().casefold()
    filtered = []

    for vehicle in vehicle_positions:
        trip = vehicle.get("trip") or {}
        route = trip.get("route") or {}
        stop_names = [
            (stop.get("stop") or {}).get("name", "")
            for stop in (trip.get("stoptimes") or [])
            if stop.get("stop")
        ]
        searchable = " ".join([
            str(vehicle.get("vehicleId") or ""),
            str(vehicle.get("label") or ""),
            str(trip.get("tripShortName") or ""),
            str(trip.get("tripHeadsign") or ""),
            str(trip.get("routeShortName") or ""),
            str(route.get("shortName") or ""),
            str(route.get("longName") or ""),
            *stop_names,
        ]).casefold()

        if search_text and search_text not in searchable:
            continue

        delay_value = ((vehicle.get("prevOrCurrentStop") or {}).get("arrivalDelay"))
        try:
            delay_seconds = int(delay_value) if delay_value is not None else 0
        except (TypeError, ValueError):
            delay_seconds = 0

        if delay_filter == "on_time" and delay_seconds > 0:
            continue
        if delay_filter == "small_delay" and not (0 < delay_seconds <= 300):
            continue
        if delay_filter == "long_delay" and delay_seconds <= 300:
            continue

        filtered.append(vehicle)

    return filtered


def get_marker_colors(vehicle_positions, selected_vehicle_id):
    colors = []
    for vehicle in vehicle_positions:
        vehicle_id = str(
            vehicle.get("vehicleId")
            or (vehicle.get("trip") or {}).get("tripShortName")
            or "unknown"
        )
        colors.append("#e67e22" if selected_vehicle_id and vehicle_id == selected_vehicle_id else "blue")
    return colors


def get_selected_vehicle_id(click_data):
    if click_data and "points" in click_data:
        return str(click_data["points"][0]["customdata"])
    return None


def get_bounds(relayout_data):
    zoom = 7
    bounds = None
    if relayout_data:
        if "map.zoom" in relayout_data:
            zoom = relayout_data["map.zoom"]
        if "map._derived" in relayout_data:
            derived = relayout_data["map._derived"]
            if "coordinates" in derived:
                coords = derived["coordinates"]
                bounds = {
                    "lat_min": min(coord[1] for coord in coords),
                    "lat_max": max(coord[1] for coord in coords),
                    "lon_min": min(coord[0] for coord in coords),
                    "lon_max": max(coord[0] for coord in coords),
                }
    return zoom, bounds


def seconds_to_hhmm(seconds):
    if seconds is None or seconds == "":
        return ""
    try:
        seconds = int(seconds)
        return f"{seconds // 3600:02}:{(seconds % 3600) // 60:02}"
    except Exception:
        return ""


def get_seconds_since_midnight():
    now = datetime.now()
    return now.hour * 3600 + now.minute * 60 + now.second
