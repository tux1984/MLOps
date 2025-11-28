-- Database: cleandb
-- Purpose: Store preprocessed/clean data for ML training

-- Table: clean_train
-- Preprocessed training data ready for model training
CREATE TABLE IF NOT EXISTS clean_train (
    id SERIAL PRIMARY KEY,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Target variable
    price NUMERIC(12, 2) NOT NULL,
    
    -- Numerical features (original)
    bed INTEGER,
    bath NUMERIC(4, 2),
    acre_lot NUMERIC(10, 4),
    house_size INTEGER,
    
    -- Derived numerical features
    price_per_sqft NUMERIC(10, 4),              -- price / house_size
    bed_bath_ratio NUMERIC(6, 3),               -- bed / bath
    sqft_per_acre NUMERIC(10, 2),               -- house_size / acre_lot
    days_since_prev_sale INTEGER,               -- days from prev_sold_date to ingestion
    
    -- Categorical features (encoded)
    brokered_by_encoded INTEGER,
    status_encoded INTEGER,
    street_encoded INTEGER,
    city_encoded INTEGER,
    state_encoded INTEGER,
    zip_code_encoded INTEGER,
    
    -- Time features (from prev_sold_date)
    prev_sale_year INTEGER,
    prev_sale_month INTEGER,
    prev_sale_quarter INTEGER,
    is_prev_sold BOOLEAN,
    
    -- Location features (aggregations)
    avg_price_by_city NUMERIC(12, 2),
    avg_price_by_state NUMERIC(12, 2),
    avg_price_by_zip NUMERIC(12, 2),
    
    -- Statistical features
    bed_zscore NUMERIC(10, 4),
    bath_zscore NUMERIC(10, 4),
    house_size_zscore NUMERIC(10, 4),
    acre_lot_zscore NUMERIC(10, 4),
    
    -- Metadata
    original_row_hash VARCHAR(32),
    preprocessing_version VARCHAR(20) DEFAULT '1.0'
);

CREATE INDEX idx_clean_train_price ON clean_train(price);
CREATE INDEX idx_clean_train_city ON clean_train(city_encoded);
CREATE INDEX idx_clean_train_state ON clean_train(state_encoded);

-- Table: clean_validation
-- Preprocessed validation data
CREATE TABLE IF NOT EXISTS clean_validation (
    id SERIAL PRIMARY KEY,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    price NUMERIC(12, 2) NOT NULL,
    bed INTEGER,
    bath NUMERIC(4, 2),
    acre_lot NUMERIC(10, 4),
    house_size INTEGER,
    price_per_sqft NUMERIC(10, 4),
    bed_bath_ratio NUMERIC(6, 3),
    sqft_per_acre NUMERIC(10, 2),
    days_since_prev_sale INTEGER,
    
    brokered_by_encoded INTEGER,
    status_encoded INTEGER,
    street_encoded INTEGER,
    city_encoded INTEGER,
    state_encoded INTEGER,
    zip_code_encoded INTEGER,
    
    prev_sale_year INTEGER,
    prev_sale_month INTEGER,
    prev_sale_quarter INTEGER,
    is_prev_sold BOOLEAN,
    
    avg_price_by_city NUMERIC(12, 2),
    avg_price_by_state NUMERIC(12, 2),
    avg_price_by_zip NUMERIC(12, 2),
    
    bed_zscore NUMERIC(10, 4),
    bath_zscore NUMERIC(10, 4),
    house_size_zscore NUMERIC(10, 4),
    acre_lot_zscore NUMERIC(10, 4),
    
    original_row_hash VARCHAR(32),
    preprocessing_version VARCHAR(20) DEFAULT '1.0'
);

CREATE INDEX idx_clean_validation_price ON clean_validation(price);

-- Table: clean_test
-- Preprocessed test data
CREATE TABLE IF NOT EXISTS clean_test (
    id SERIAL PRIMARY KEY,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    price NUMERIC(12, 2) NOT NULL,
    bed INTEGER,
    bath NUMERIC(4, 2),
    acre_lot NUMERIC(10, 4),
    house_size INTEGER,
    price_per_sqft NUMERIC(10, 4),
    bed_bath_ratio NUMERIC(6, 3),
    sqft_per_acre NUMERIC(10, 2),
    days_since_prev_sale INTEGER,
    
    brokered_by_encoded INTEGER,
    status_encoded INTEGER,
    street_encoded INTEGER,
    city_encoded INTEGER,
    state_encoded INTEGER,
    zip_code_encoded INTEGER,
    
    prev_sale_year INTEGER,
    prev_sale_month INTEGER,
    prev_sale_quarter INTEGER,
    is_prev_sold BOOLEAN,
    
    avg_price_by_city NUMERIC(12, 2),
    avg_price_by_state NUMERIC(12, 2),
    avg_price_by_zip NUMERIC(12, 2),
    
    bed_zscore NUMERIC(10, 4),
    bath_zscore NUMERIC(10, 4),
    house_size_zscore NUMERIC(10, 4),
    acre_lot_zscore NUMERIC(10, 4),
    
    original_row_hash VARCHAR(32),
    preprocessing_version VARCHAR(20) DEFAULT '1.0'
);

CREATE INDEX idx_clean_test_price ON clean_test(price);

-- Table: encoding_mappings
-- Stores categorical encodings for consistency across batches
CREATE TABLE IF NOT EXISTS encoding_mappings (
    id SERIAL PRIMARY KEY,
    feature_name VARCHAR(50) NOT NULL,
    original_value TEXT NOT NULL,
    encoded_value INTEGER NOT NULL,
    frequency INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(feature_name, original_value)
);

CREATE INDEX idx_encoding_feature ON encoding_mappings(feature_name);

-- Table: preprocessing_statistics
-- Stores statistics used for normalization/standardization
CREATE TABLE IF NOT EXISTS preprocessing_statistics (
    id SERIAL PRIMARY KEY,
    feature_name VARCHAR(50) NOT NULL,
    mean_value NUMERIC(15, 6),
    std_value NUMERIC(15, 6),
    min_value NUMERIC(15, 6),
    max_value NUMERIC(15, 6),
    median_value NUMERIC(15, 6),
    q1_value NUMERIC(15, 6),
    q3_value NUMERIC(15, 6),
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_source VARCHAR(20) DEFAULT 'train'
);

CREATE INDEX idx_preprocessing_stats_feature ON preprocessing_statistics(feature_name);

-- View: Feature summary
CREATE OR REPLACE VIEW v_feature_summary AS
SELECT 
    'train' as dataset,
    COUNT(*) as num_records,
    AVG(price) as avg_price,
    STDDEV(price) as std_price,
    MIN(price) as min_price,
    MAX(price) as max_price,
    AVG(house_size) as avg_house_size,
    AVG(bed) as avg_bed,
    AVG(bath) as avg_bath
FROM clean_train
UNION ALL
SELECT 
    'validation' as dataset,
    COUNT(*) as num_records,
    AVG(price) as avg_price,
    STDDEV(price) as std_price,
    MIN(price) as min_price,
    MAX(price) as max_price,
    AVG(house_size) as avg_house_size,
    AVG(bed) as avg_bed,
    AVG(bath) as avg_bath
FROM clean_validation
UNION ALL
SELECT 
    'test' as dataset,
    COUNT(*) as num_records,
    AVG(price) as avg_price,
    STDDEV(price) as std_price,
    MIN(price) as min_price,
    MAX(price) as max_price,
    AVG(house_size) as avg_house_size,
    AVG(bed) as avg_bed,
    AVG(bath) as avg_bath
FROM clean_test;

-- Comments
COMMENT ON TABLE clean_train IS 'Preprocessed training data for house price prediction';
COMMENT ON TABLE clean_validation IS 'Preprocessed validation data';
COMMENT ON TABLE clean_test IS 'Preprocessed test data';
COMMENT ON TABLE encoding_mappings IS 'Categorical feature encodings for consistency';
COMMENT ON TABLE preprocessing_statistics IS 'Statistics for normalization and feature engineering';

COMMENT ON COLUMN clean_train.price IS 'TARGET VARIABLE - House price in USD';
COMMENT ON COLUMN clean_train.price_per_sqft IS 'Derived: price divided by house_size';
COMMENT ON COLUMN clean_train.bed_bath_ratio IS 'Derived: bedrooms divided by bathrooms';
COMMENT ON COLUMN clean_train.days_since_prev_sale IS 'Derived: days between prev_sold_date and ingestion';
