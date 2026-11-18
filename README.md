# Hungarian Real-Time Train Map

This project visualizes real-time train positions and routes in Hungary using data from MÁV (Hungarian State Railways).

## Features
- Interactive map of Hungary showing all trains in real time
- Clickable train markers with info panel (name, speed, delay, stops, route)
- Route and stops displayed on the map
- Heading indicators for trains at sufficient zoom
- Automatic data refresh every minute
- PostgreSQL-backed vehicle and history storage
- Train search and delay filtering

## Requirements
- Python 3.8+
- pip

## Installation
1. Clone or download this repository.
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and change the database password if needed.

## Usage
1. Initialize PostgreSQL using `database/schema.sql`.
2. Start the collector:
   ```sh
   python collector/trains.py
   ```
3. Run the app:
   ```sh
   python app.py
   ```
4. Open your browser at `http://127.0.0.1:8050/`

## Files
- `app.py` — Main Dash app
- `callbacks.py` — Dash callback registration and map interactions
- `mav_api.py` — MÁV vehicle-position API client
- `train_data.py` — Vehicle data normalization and time/bounds helpers
- `map_view.py` — Plotly map traces and heading arrows
- `ui_layout.py` — Dash page layout and HTML template
- `database.py` — PostgreSQL reader
- `collector/trains.py` — Live MÁV data collector
- `database/schema.sql` — PostgreSQL schema
- `vehicle_positions.json` — Train data (auto-fetched if missing)
- `trains_map.html` — (Optional) Static map export

## Notes
- The live data is fetched by the collector from: `https://mavplusz.hu/otp2-backend/otp/routers/default/index/graphql`
- The map and info panel update automatically every minute.

## License
MIT License
