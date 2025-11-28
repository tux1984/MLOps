-- Database: rawdb
-- Purpose: Store raw data ingested from external sources

-- Table: raw_train
-- Stores training data in batches
CREATE TABLE IF NOT EXISTS raw_train (
    id SERIAL PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE NOT NULL,
    batch_id INTEGER NOT NULL,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Diabetes dataset columns
    encounter_id INTEGER,
    patient_nbr INTEGER,
    race VARCHAR(50),
    gender VARCHAR(20),
    age VARCHAR(20),
    weight VARCHAR(20),
    admission_type_id INTEGER,
    discharge_disposition_id INTEGER,
    admission_source_id INTEGER,
    time_in_hospital INTEGER,
    payer_code VARCHAR(20),
    medical_specialty TEXT,
    num_lab_procedures INTEGER,
    num_procedures INTEGER,
    num_medications INTEGER,
    number_outpatient INTEGER,
    number_emergency INTEGER,
    number_inpatient INTEGER,
    diag_1 VARCHAR(10),
    diag_2 VARCHAR(10),
    diag_3 VARCHAR(10),
    number_diagnoses INTEGER,
    max_glu_serum VARCHAR(20),
    a1cresult VARCHAR(20),
    metformin VARCHAR(20),
    repaglinide VARCHAR(20),
    nateglinide VARCHAR(20),
    chlorpropamide VARCHAR(20),
    glimepiride VARCHAR(20),
    acetohexamide VARCHAR(20),
    glipizide VARCHAR(20),
    glyburide VARCHAR(20),
    tolbutamide VARCHAR(20),
    pioglitazone VARCHAR(20),
    rosiglitazone VARCHAR(20),
    acarbose VARCHAR(20),
    miglitol VARCHAR(20),
    troglitazone VARCHAR(20),
    tolazamide VARCHAR(20),
    examide VARCHAR(20),
    citoglipton VARCHAR(20),
    insulin VARCHAR(20),
    glyburide_metformin VARCHAR(20),
    glipizide_metformin VARCHAR(20),
    glimepiride_pioglitazone VARCHAR(20),
    metformin_rosiglitazone VARCHAR(20),
    metformin_pioglitazone VARCHAR(20),
    change VARCHAR(20),
    diabetesmed VARCHAR(20),
    readmitted VARCHAR(20), -- Target variable
    
    CONSTRAINT check_batch_id_positive CHECK (batch_id > 0)
);

-- Table: raw_validation
-- Stores validation data
CREATE TABLE IF NOT EXISTS raw_validation (
    id SERIAL PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE NOT NULL,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Same columns as raw_train
    encounter_id INTEGER,
    patient_nbr INTEGER,
    race VARCHAR(50),
    gender VARCHAR(20),
    age VARCHAR(20),
    weight VARCHAR(20),
    admission_type_id INTEGER,
    discharge_disposition_id INTEGER,
    admission_source_id INTEGER,
    time_in_hospital INTEGER,
    payer_code VARCHAR(20),
    medical_specialty TEXT,
    num_lab_procedures INTEGER,
    num_procedures INTEGER,
    num_medications INTEGER,
    number_outpatient INTEGER,
    number_emergency INTEGER,
    number_inpatient INTEGER,
    diag_1 VARCHAR(10),
    diag_2 VARCHAR(10),
    diag_3 VARCHAR(10),
    number_diagnoses INTEGER,
    max_glu_serum VARCHAR(20),
    a1cresult VARCHAR(20),
    metformin VARCHAR(20),
    repaglinide VARCHAR(20),
    nateglinide VARCHAR(20),
    chlorpropamide VARCHAR(20),
    glimepiride VARCHAR(20),
    acetohexamide VARCHAR(20),
    glipizide VARCHAR(20),
    glyburide VARCHAR(20),
    tolbutamide VARCHAR(20),
    pioglitazone VARCHAR(20),
    rosiglitazone VARCHAR(20),
    acarbose VARCHAR(20),
    miglitol VARCHAR(20),
    troglitazone VARCHAR(20),
    tolazamide VARCHAR(20),
    examide VARCHAR(20),
    citoglipton VARCHAR(20),
    insulin VARCHAR(20),
    glyburide_metformin VARCHAR(20),
    glipizide_metformin VARCHAR(20),
    glimepiride_pioglitazone VARCHAR(20),
    metformin_rosiglitazone VARCHAR(20),
    metformin_pioglitazone VARCHAR(20),
    change VARCHAR(20),
    diabetesmed VARCHAR(20),
    readmitted VARCHAR(20)
);

-- Table: raw_test
-- Stores test data
CREATE TABLE IF NOT EXISTS raw_test (
    id SERIAL PRIMARY KEY,
    row_hash VARCHAR(32) UNIQUE NOT NULL,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Same columns as raw_train
    encounter_id INTEGER,
    patient_nbr INTEGER,
    race VARCHAR(50),
    gender VARCHAR(20),
    age VARCHAR(20),
    weight VARCHAR(20),
    admission_type_id INTEGER,
    discharge_disposition_id INTEGER,
    admission_source_id INTEGER,
    time_in_hospital INTEGER,
    payer_code VARCHAR(20),
    medical_specialty TEXT,
    num_lab_procedures INTEGER,
    num_procedures INTEGER,
    num_medications INTEGER,
    number_outpatient INTEGER,
    number_emergency INTEGER,
    number_inpatient INTEGER,
    diag_1 VARCHAR(10),
    diag_2 VARCHAR(10),
    diag_3 VARCHAR(10),
    number_diagnoses INTEGER,
    max_glu_serum VARCHAR(20),
    a1cresult VARCHAR(20),
    metformin VARCHAR(20),
    repaglinide VARCHAR(20),
    nateglinide VARCHAR(20),
    chlorpropamide VARCHAR(20),
    glimepiride VARCHAR(20),
    acetohexamide VARCHAR(20),
    glipizide VARCHAR(20),
    glyburide VARCHAR(20),
    tolbutamide VARCHAR(20),
    pioglitazone VARCHAR(20),
    rosiglitazone VARCHAR(20),
    acarbose VARCHAR(20),
    miglitol VARCHAR(20),
    troglitazone VARCHAR(20),
    tolazamide VARCHAR(20),
    examide VARCHAR(20),
    citoglipton VARCHAR(20),
    insulin VARCHAR(20),
    glyburide_metformin VARCHAR(20),
    glipizide_metformin VARCHAR(20),
    glimepiride_pioglitazone VARCHAR(20),
    metformin_rosiglitazone VARCHAR(20),
    metformin_pioglitazone VARCHAR(20),
    change VARCHAR(20),
    diabetesmed VARCHAR(20),
    readmitted VARCHAR(20)
);

-- Table: batch_metadata
-- Tracks metadata for each batch loaded
CREATE TABLE IF NOT EXISTS batch_metadata (
    batch_id SERIAL PRIMARY KEY,
    dataset_split VARCHAR(20) NOT NULL,  -- 'train', 'validation', or 'test'
    total_records INTEGER NOT NULL,
    new_records INTEGER NOT NULL,
    duplicate_records INTEGER NOT NULL,
    load_start_time TIMESTAMP NOT NULL,
    load_end_time TIMESTAMP,
    load_status VARCHAR(20) DEFAULT 'in_progress',  -- 'in_progress', 'completed', 'failed'
    error_message TEXT,
    
    CONSTRAINT check_split_value CHECK (dataset_split IN ('train', 'validation', 'test')),
    CONSTRAINT check_status_value CHECK (load_status IN ('in_progress', 'completed', 'failed'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_raw_train_batch_id ON raw_train(batch_id);
CREATE INDEX IF NOT EXISTS idx_raw_train_row_hash ON raw_train(row_hash);
CREATE INDEX IF NOT EXISTS idx_batch_metadata_split ON batch_metadata(dataset_split);
CREATE INDEX IF NOT EXISTS idx_batch_metadata_status ON batch_metadata(load_status);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mlops;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mlops;
