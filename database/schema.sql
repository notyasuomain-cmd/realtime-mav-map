
CREATE SCHEMA IF NOT EXISTS api;
CREATE SCHEMA IF NOT EXISTS private;

-- Minden jármű legutóbb ismert állapota
CREATE TABLE api.vehicles (
    vehicle_id TEXT PRIMARY KEY,
    label TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    heading DOUBLE PRECISION,
    source_updated TEXT,
    raw JSONB NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Csak a megváltozott állapotok
CREATE TABLE private.vehicle_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id TEXT NOT NULL,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    source_updated TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw JSONB NOT NULL
);

CREATE INDEX vehicle_history_lookup_idx
ON private.vehicle_history (vehicle_id, collected_at DESC);

CREATE INDEX vehicle_history_time_idx
ON private.vehicle_history (collected_at DESC);
