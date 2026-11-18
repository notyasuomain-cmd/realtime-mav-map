import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mav_collector:mav_collector@127.0.0.1:5432/mav",
)


def get_database_vehicle_data():
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT raw
                    FROM api.vehicles
                    WHERE lat IS NOT NULL
                      AND lon IS NOT NULL
                    ORDER BY last_seen DESC
                    """
                )
                vehicles = [row[0] for row in cursor.fetchall()]
        return {"data": {"vehiclePositions": vehicles}}
    except Exception as exc:
        print(f"Database read failed: {exc}", flush=True)
        return None
