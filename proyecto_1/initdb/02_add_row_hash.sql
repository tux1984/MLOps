DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'forest_cover_samples'
          AND column_name = 'row_hash'
    ) THEN
        ALTER TABLE forest_cover_samples
            ADD COLUMN row_hash TEXT;

        UPDATE forest_cover_samples
        SET row_hash = md5(
            COALESCE(group_number::TEXT, '') || '|' ||
            COALESCE(batch_number::TEXT, '') || '|' ||
            COALESCE(elevation::TEXT, '') || '|' ||
            COALESCE(aspect::TEXT, '') || '|' ||
            COALESCE(slope::TEXT, '') || '|' ||
            COALESCE(horizontal_distance_to_hydrology::TEXT, '') || '|' ||
            COALESCE(vertical_distance_to_hydrology::TEXT, '') || '|' ||
            COALESCE(horizontal_distance_to_roadways::TEXT, '') || '|' ||
            COALESCE(hillshade_9am::TEXT, '') || '|' ||
            COALESCE(hillshade_noon::TEXT, '') || '|' ||
            COALESCE(hillshade_3pm::TEXT, '') || '|' ||
            COALESCE(horizontal_distance_to_fire_points::TEXT, '') || '|' ||
            COALESCE(wilderness_area, '') || '|' ||
            COALESCE(soil_type, '') || '|' ||
            COALESCE(cover_type::TEXT, '')
        )
        WHERE row_hash IS NULL;

        ALTER TABLE forest_cover_samples
            ALTER COLUMN row_hash SET NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_forest_cover_samples_row_hash
            ON forest_cover_samples (row_hash);
    END IF;
END;
$$;
