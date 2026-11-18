import json

import requests


VEHICLE_POSITIONS_URL = (
    "https://mavplusz.hu/otp2-backend/otp/routers/default/index/graphql"
)

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) "
        "Gecko/20100101 Firefox/140.0"
    ),
}

VEHICLE_POSITIONS_QUERY = """
query VehiclePositions(
    $swLat: Float!
    $swLon: Float!
    $neLat: Float!
    $neLon: Float!
) {
    vehiclePositions(
      swLat: $swLat,
      swLon: $swLon,
      neLat: $neLat,
      neLon: $neLon,
      modes: [RAIL, SUBURBAN_RAILWAY, TRAMTRAIN]
    ) {
      vehicleId
      label
      lat
      lon
      heading
      speed
      lastUpdated
      trip {
        gtfsId
        tripShortName
        tripHeadsign
        trainCategoryName
        trainName
        routeShortName
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
      prevOrCurrentStop {
        scheduledArrival
        realtimeArrival
        arrivalDelay
        scheduledDeparture
        realtimeDeparture
        departureDelay
      }
    }
}
"""


def get_latest_vehicle_data():
    """Fetch latest vehicle data from the MÁV API."""
    try:
        response = requests.post(
            VEHICLE_POSITIONS_URL,
            headers=HEADERS,
            json={
                "query": VEHICLE_POSITIONS_QUERY,
                "operationName": "VehiclePositions",
                "variables": {
                    "swLat": 45.7,
                    "swLon": 16.0,
                    "neLat": 48.7,
                    "neLon": 22.9,
                },
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()

        print(f"Failed to fetch data: {response.status_code}")
        return None
    except Exception as exc:
        print(f"Exception during fetch: {exc}")
        return None
