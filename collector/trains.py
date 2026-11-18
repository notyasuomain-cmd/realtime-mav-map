
import asyncio
import os
import time

import httpx
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mav_collector:mav_collector@127.0.0.1:5432/mav",
)
INTERVAL = float(os.getenv("POLL_INTERVAL", "10"))

URL = (
    "https://mavplusz.hu/"
    "otp2-backend/otp/routers/default/index/graphql"
)

QUERY = """
query VehiclePositions(
    $swLat: Float!
    $swLon: Float!
    $neLat: Float!
    $neLon: Float!
) {
    vehiclePositions(
        swLat: $swLat
        swLon: $swLon
        neLat: $neLat
        neLon: $neLon
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
                departureDelay
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

PAYLOAD = {
    "query": QUERY,
    "operationName": "VehiclePositions",
    "variables": {
        "swLat": 45.7,
        "swLon": 16.0,
        "neLat": 48.7,
        "neLon": 22.9,
    },
}

UPSERT_SQL = """
WITH changed AS (
    INSERT INTO api.vehicles (
        vehicle_id, label, lat, lon, speed,
        heading, source_updated, raw
    )
    VALUES (
        %(vehicle_id)s, %(label)s, %(lat)s, %(lon)s,
        %(speed)s, %(heading)s, %(source_updated)s,
        %(raw)s
    )
    ON CONFLICT (vehicle_id) DO UPDATE SET
        label = EXCLUDED.label,
        lat = EXCLUDED.lat,
        lon = EXCLUDED.lon,
        speed = EXCLUDED.speed,
        heading = EXCLUDED.heading,
        source_updated = EXCLUDED.source_updated,
        raw = EXCLUDED.raw,
        last_seen = NOW()
    WHERE api.vehicles.raw IS DISTINCT FROM EXCLUDED.raw
    RETURNING vehicle_id, lat, lon, source_updated, raw
)
INSERT INTO private.vehicle_history (
    vehicle_id, lat, lon, source_updated, raw
)
SELECT vehicle_id, lat, lon, source_updated, raw
FROM changed
"""

async def fetch_trains(client):
    response = await client.post(URL, json=PAYLOAD)
    response.raise_for_status()

    result = response.json()

    if result.get("errors"):
        raise RuntimeError(result["errors"])

    return result["data"]["vehiclePositions"]


async def save_trains(conn, trains):
    records = []

    for train in trains:
        if not train.get("vehicleId"):
            continue

        records.append({
            "vehicle_id": train["vehicleId"],
            "label": train.get("label"),
            "lat": train.get("lat"),
            "lon": train.get("lon"),
            "speed": train.get("speed"),
            "heading": train.get("heading"),
            "source_updated": str(train["lastUpdated"])
                if train.get("lastUpdated") is not None
                else None,
            "raw": Jsonb(train),
        })

    async with conn.transaction():
        async with conn.cursor() as cursor:
            for record in records:
                await cursor.execute(UPSERT_SQL, record)

    return len(records)


async def main():
    async with httpx.AsyncClient(timeout=20) as client:
        async with await psycopg.AsyncConnection.connect(
            DATABASE_URL,
            autocommit=True
        ) as conn:

            while True:
                started = time.monotonic()

                try:
                    trains = await fetch_trains(client)
                    saved = await save_trains(conn, trains)

                    duration = time.monotonic() - started

                    print(
                        f"Received: {len(trains)} | "
                        f"Processed: {saved} | "
                        f"Time: {duration:.2f}s",
                        flush=True
                    )

                except Exception as exc:
                    print(f"Collector error: {exc}", flush=True)

                elapsed = time.monotonic() - started
                await asyncio.sleep(max(1, INTERVAL - elapsed))


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
