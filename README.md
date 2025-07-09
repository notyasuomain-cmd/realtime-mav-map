# Hungarian Real-Time Train Map

This project visualizes real-time train positions and routes in Hungary using data from MÁV (Hungarian State Railways).

## Features
- Interactive map of Hungary showing all trains in real time
- Clickable train markers with info panel (name, speed, delay, stops, route)
- Route and stops displayed on the map
- Heading indicators for trains at sufficient zoom
- Automatic data refresh every minute

## Requirements
- Python 3.8+
- pip

## Installation
1. Clone or download this repository.
2. Install dependencies:
   ```sh
   pip install dash plotly requests polyline
   ```

## Usage
1. Run the app:
   ```sh
   python app.py
   ```
2. Open your browser and go to `http://127.0.0.1:8050/`

## Files
- `app.py` — Main Dash app
- `vehicle_positions.json` — Train data (auto-fetched if missing)
- `trains_map.html` — (Optional) Static map export

## Notes
- The live data is fetched from: `https://emma.mav.hu/otp2-backend/otp/routers/default/index/graphql`
- The map and info panel update automatically every minute.

## License
MIT License
