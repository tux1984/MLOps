-- Asegurar que la columna row_hash existe y tiene un índice único
DO $$
BEGIN
    -- Verificar si row_hash ya existe
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'diabetes_raw'
          AND column_name = 'row_hash'
    ) THEN
        ALTER TABLE diabetes_raw ADD COLUMN row_hash TEXT;
    END IF;

    -- Crear función para generar hash si no existe
    CREATE OR REPLACE FUNCTION generate_diabetes_row_hash(rec diabetes_raw)
    RETURNS TEXT AS $func$
    BEGIN
        RETURN md5(
            COALESCE(rec.encounter_id::TEXT, '') || '|' ||
            COALESCE(rec.patient_nbr::TEXT, '') || '|' ||
            COALESCE(rec.time_in_hospital::TEXT, '') || '|' ||
            COALESCE(rec.num_lab_procedures::TEXT, '') || '|' ||
            COALESCE(rec.readmitted, '')
        );
    END;
    $func$ LANGUAGE plpgsql IMMUTABLE;

    -- Crear índice único si no existe
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname = 'uq_diabetes_raw_row_hash'
    ) THEN
        CREATE UNIQUE INDEX uq_diabetes_raw_row_hash ON diabetes_raw (row_hash);
    END IF;
END;
$$;
