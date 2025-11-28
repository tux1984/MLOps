-- Database: rawdb
-- Purpose: Store raw data from realtor API (house prices dataset)

-- Table: raw_train
-- Stores training data from API batches
CREATE TABLE IF NOT EXISTS raw_train (
    id SERIAL PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE NOT NULL,
    batch_id INTEGER NOT NULL,
    request_count INTEGER NOT NULL,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Realtor dataset columns (from PDF)
    brokered_by TEXT,                    -- agencia/corredor (categórico)
    status VARCHAR(50),                  -- ready for sale or for_sale
    price NUMERIC(12, 2),                -- precio de la vivienda (target variable)
    bed INTEGER,                         -- número de camas
    bath NUMERIC(4, 2),                  -- número de baños
    acre_lot NUMERIC(10, 4),             -- tamaño del terreno/propiedad en acres
    street TEXT,                         -- dirección callejera (categórico)
    city VARCHAR(100),                   -- nombre de la ciudad
    state VARCHAR(50),                   -- nombre del estado
    zip_code VARCHAR(10),                -- código postal
    house_size INTEGER,                  -- área de la casa en pies cuadrados
    prev_sold_date DATE,                 -- fecha de venta anterior
    
    -- Metadata
    CONSTRAINT unique_row_per_batch UNIQUE (row_hash)
);

-- Index for faster queries
CREATE INDEX idx_raw_train_batch ON raw_train(batch_id);
CREATE INDEX idx_raw_train_timestamp ON raw_train(ingestion_timestamp);
CREATE INDEX idx_raw_train_price ON raw_train(price);
CREATE INDEX idx_raw_train_city_state ON raw_train(city, state);

-- Table: raw_validation
-- Stores validation data from API
CREATE TABLE IF NOT EXISTS raw_validation (
    id SERIAL PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE NOT NULL,
    batch_id INTEGER NOT NULL,
    request_count INTEGER NOT NULL,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Realtor dataset columns
    brokered_by TEXT,
    status VARCHAR(50),
    price NUMERIC(12, 2),
    bed INTEGER,
    bath NUMERIC(4, 2),
    acre_lot NUMERIC(10, 4),
    street TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(10),
    house_size INTEGER,
    prev_sold_date DATE,
    
    CONSTRAINT unique_val_row_per_batch UNIQUE (row_hash)
);

CREATE INDEX idx_raw_validation_batch ON raw_validation(batch_id);
CREATE INDEX idx_raw_validation_timestamp ON raw_validation(ingestion_timestamp);

-- Table: raw_test
-- Stores test data from API
CREATE TABLE IF NOT EXISTS raw_test (
    id SERIAL PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE NOT NULL,
    batch_id INTEGER NOT NULL,
    request_count INTEGER NOT NULL,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Realtor dataset columns
    brokered_by TEXT,
    status VARCHAR(50),
    price NUMERIC(12, 2),
    bed INTEGER,
    bath NUMERIC(4, 2),
    acre_lot NUMERIC(10, 4),
    street TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(10),
    house_size INTEGER,
    prev_sold_date DATE,
    
    CONSTRAINT unique_test_row_per_batch UNIQUE (row_hash)
);

CREATE INDEX idx_raw_test_batch ON raw_test(batch_id);
CREATE INDEX idx_raw_test_timestamp ON raw_test(ingestion_timestamp);

-- Table: api_request_log
-- Tracks API requests for debugging and monitoring
CREATE TABLE IF NOT EXISTS api_request_log (
    id SERIAL PRIMARY KEY,
    request_count INTEGER NOT NULL,
    group_number INTEGER NOT NULL,
    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_status_code INTEGER,
    response_size INTEGER,
    num_records INTEGER,
    error_message TEXT,
    is_successful BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_api_log_timestamp ON api_request_log(request_timestamp);
CREATE INDEX idx_api_log_group ON api_request_log(group_number);

-- Table: ingestion_summary
-- Stores summary statistics per batch ingestion
CREATE TABLE IF NOT EXISTS ingestion_summary (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER NOT NULL,
    request_count INTEGER NOT NULL,
    ingestion_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_records INTEGER,
    train_records INTEGER,
    validation_records INTEGER,
    test_records INTEGER,
    duplicates_found INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    execution_time_seconds NUMERIC(10, 2)
);

CREATE INDEX idx_ingestion_summary_batch ON ingestion_summary(batch_id);
CREATE INDEX idx_ingestion_summary_date ON ingestion_summary(ingestion_date);

-- View: Recent API requests
CREATE OR REPLACE VIEW v_recent_api_requests AS
SELECT 
    request_count,
    group_number,
    request_timestamp,
    response_status_code,
    num_records,
    is_successful
FROM api_request_log
ORDER BY request_timestamp DESC
LIMIT 50;

-- View: Ingestion statistics
CREATE OR REPLACE VIEW v_ingestion_stats AS
SELECT 
    COUNT(*) as total_batches,
    SUM(total_records) as total_records_ingested,
    SUM(train_records) as total_train,
    SUM(validation_records) as total_validation,
    SUM(test_records) as total_test,
    SUM(duplicates_found) as total_duplicates,
    AVG(execution_time_seconds) as avg_execution_time,
    MAX(ingestion_date) as last_ingestion_date
FROM ingestion_summary;

-- Comments for documentation
COMMENT ON TABLE raw_train IS 'Raw training data from realtor API - house prices dataset';
COMMENT ON TABLE raw_validation IS 'Raw validation data from realtor API';
COMMENT ON TABLE raw_test IS 'Raw test data from realtor API';
COMMENT ON TABLE api_request_log IS 'Log of all API requests to http://10.43.100.103:8000';
COMMENT ON TABLE ingestion_summary IS 'Summary statistics per batch ingestion';

COMMENT ON COLUMN raw_train.brokered_by IS 'Broker/agency name (categorical, encoded)';
COMMENT ON COLUMN raw_train.status IS 'House status: ready for sale or for_sale';
COMMENT ON COLUMN raw_train.price IS 'House price - TARGET VARIABLE for regression';
COMMENT ON COLUMN raw_train.bed IS 'Number of bedrooms';
COMMENT ON COLUMN raw_train.bath IS 'Number of bathrooms';
COMMENT ON COLUMN raw_train.acre_lot IS 'Property size in acres';
COMMENT ON COLUMN raw_train.street IS 'Street address (categorical, encoded)';
COMMENT ON COLUMN raw_train.house_size IS 'House area/size in square feet';
COMMENT ON COLUMN raw_train.prev_sold_date IS 'Previous sale date';
