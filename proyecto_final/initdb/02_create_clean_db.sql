-- Database: cleandb
-- Purpose: Store preprocessed and cleaned data ready for ML training

-- Table: clean_train
-- Stores cleaned and preprocessed training data
CREATE TABLE IF NOT EXISTS clean_train (
    id SERIAL PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE NOT NULL,
    processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Preprocessed features (numeric and encoded)
    encounter_id INTEGER,
    patient_nbr INTEGER,
    
    -- Categorical features (encoded as integers)
    race_encoded INTEGER,
    gender_encoded INTEGER,
    age_encoded INTEGER,
    
    -- Numeric features (original or normalized)
    admission_type_id INTEGER,
    discharge_disposition_id INTEGER,
    admission_source_id INTEGER,
    time_in_hospital INTEGER,
    num_lab_procedures INTEGER,
    num_procedures INTEGER,
    num_medications INTEGER,
    number_outpatient INTEGER,
    number_emergency INTEGER,
    number_inpatient INTEGER,
    number_diagnoses INTEGER,
    
    -- Encoded lab results
    max_glu_serum_encoded INTEGER,
    a1cresult_encoded INTEGER,
    
    -- Diabetes medications count (engineered feature)
    num_diabetes_meds INTEGER,
    
    -- Encoded binary features
    change_encoded INTEGER,
    diabetesmed_encoded INTEGER,
    
    -- Target variable (binary: 0=No readmission, 1=Readmission)
    readmitted INTEGER
);

-- Table: clean_validation
-- Stores cleaned validation data
CREATE TABLE IF NOT EXISTS clean_validation (
    id SERIAL PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE NOT NULL,
    processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Same columns as clean_train
    encounter_id INTEGER,
    patient_nbr INTEGER,
    race_encoded INTEGER,
    gender_encoded INTEGER,
    age_encoded INTEGER,
    admission_type_id INTEGER,
    discharge_disposition_id INTEGER,
    admission_source_id INTEGER,
    time_in_hospital INTEGER,
    num_lab_procedures INTEGER,
    num_procedures INTEGER,
    num_medications INTEGER,
    number_outpatient INTEGER,
    number_emergency INTEGER,
    number_inpatient INTEGER,
    number_diagnoses INTEGER,
    max_glu_serum_encoded INTEGER,
    a1cresult_encoded INTEGER,
    num_diabetes_meds INTEGER,
    change_encoded INTEGER,
    diabetesmed_encoded INTEGER,
    readmitted INTEGER
);

-- Table: clean_test
-- Stores cleaned test data
CREATE TABLE IF NOT EXISTS clean_test (
    id SERIAL PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE NOT NULL,
    processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Same columns as clean_train
    encounter_id INTEGER,
    patient_nbr INTEGER,
    race_encoded INTEGER,
    gender_encoded INTEGER,
    age_encoded INTEGER,
    admission_type_id INTEGER,
    discharge_disposition_id INTEGER,
    admission_source_id INTEGER,
    time_in_hospital INTEGER,
    num_lab_procedures INTEGER,
    num_procedures INTEGER,
    num_medications INTEGER,
    number_outpatient INTEGER,
    number_emergency INTEGER,
    number_inpatient INTEGER,
    number_diagnoses INTEGER,
    max_glu_serum_encoded INTEGER,
    a1cresult_encoded INTEGER,
    num_diabetes_meds INTEGER,
    change_encoded INTEGER,
    diabetesmed_encoded INTEGER,
    readmitted INTEGER
);

-- Table: preprocessing_metadata
-- Stores parameters used for preprocessing transformations
CREATE TABLE IF NOT EXISTS preprocessing_metadata (
    id SERIAL PRIMARY KEY,
    preprocessing_run_id UUID UNIQUE NOT NULL,
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Imputation parameters
    imputation_strategy JSONB,  -- Stores strategy for each column
    imputation_values JSONB,    -- Stores computed values (means, modes, etc)
    
    -- Encoding parameters
    encoding_mappings JSONB,    -- Stores label/one-hot encoding mappings
    
    -- Scaling parameters
    scaler_params JSONB,        -- Stores StandardScaler parameters (mean, std)
    
    -- Feature engineering
    engineered_features JSONB,  -- List of new features created
    
    -- General metadata
    total_features INTEGER,
    dropped_columns TEXT[],
    preprocessing_version VARCHAR(20)
);

-- Table: data_quality_metrics
-- Stores data quality metrics for each preprocessing run
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id SERIAL PRIMARY KEY,
    preprocessing_run_id UUID REFERENCES preprocessing_metadata(preprocessing_run_id),
    dataset_split VARCHAR(20) NOT NULL,
    
    -- Record counts
    total_records_before INTEGER,
    total_records_after INTEGER,
    records_removed INTEGER,
    
    -- Missing values
    missing_values_before JSONB,  -- Per column before imputation
    missing_values_after JSONB,   -- Per column after imputation
    
    -- Outliers
    outliers_detected JSONB,      -- Per column
    outliers_removed INTEGER,
    
    -- Feature statistics
    feature_statistics JSONB,     -- Descriptive stats per feature
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_split_value CHECK (dataset_split IN ('train', 'validation', 'test'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_clean_train_row_hash ON clean_train(row_hash);
CREATE INDEX IF NOT EXISTS idx_clean_validation_row_hash ON clean_validation(row_hash);
CREATE INDEX IF NOT EXISTS idx_clean_test_row_hash ON clean_test(row_hash);
CREATE INDEX IF NOT EXISTS idx_preprocessing_metadata_run_id ON preprocessing_metadata(preprocessing_run_id);
CREATE INDEX IF NOT EXISTS idx_data_quality_metrics_run_id ON data_quality_metrics(preprocessing_run_id);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mlops;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mlops;
