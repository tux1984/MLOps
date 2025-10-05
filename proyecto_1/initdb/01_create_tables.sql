CREATE TABLE IF NOT EXISTS forest_cover_samples (
    id SERIAL PRIMARY KEY,
    group_number INTEGER NOT NULL,
    batch_number INTEGER NOT NULL,
    elevation INTEGER,
    aspect INTEGER,
    slope INTEGER,
    horizontal_distance_to_hydrology INTEGER,
    vertical_distance_to_hydrology INTEGER,
    horizontal_distance_to_roadways INTEGER,
    hillshade_9am INTEGER,
    hillshade_noon INTEGER,
    hillshade_3pm INTEGER,
    horizontal_distance_to_fire_points INTEGER,
    wilderness_area TEXT,
    soil_type TEXT,
    cover_type INTEGER,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_hash TEXT UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_forest_cover_samples_batch
    ON forest_cover_samples (batch_number);
