import os
import json

import dash

from callbacks import register_callbacks
from database import get_database_vehicle_data
from mav_api import get_latest_vehicle_data
from ui_layout import EXTERNAL_STYLESHEETS, INDEX_STRING, create_layout


app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS)
app.index_string = INDEX_STRING

initial_vehicle_data = get_database_vehicle_data()

if initial_vehicle_data is None:
    if os.path.exists("vehicle_positions.json"):
        with open("vehicle_positions.json", "r", encoding="utf-8") as file:
            initial_vehicle_data = json.load(file)
    else:
        initial_vehicle_data = get_latest_vehicle_data()
        if initial_vehicle_data is not None:
            with open("vehicle_positions.json", "w", encoding="utf-8") as file:
                json.dump(initial_vehicle_data, file, ensure_ascii=False)
        else:
            initial_vehicle_data = {"data": {"vehiclePositions": []}}

app.layout = create_layout(initial_vehicle_data)


register_callbacks(app)


if __name__ == "__main__":
    app.run()
