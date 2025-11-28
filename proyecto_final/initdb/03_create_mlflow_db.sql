-- Database: mlflow
-- Purpose: Backend store for MLflow tracking server
-- Note: MLflow will create its own tables automatically
-- This file is for any custom tables or initial setup

-- Grant necessary permissions to mlflow user
-- Database privileges are already set via POSTGRES_USER
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mlflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mlflow;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO mlflow;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO mlflow;

-- Optional: Create custom tables for additional MLflow metadata

-- Table: model_deployment_history
-- Tracks when models are promoted to Production
CREATE TABLE IF NOT EXISTS model_deployment_history (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    model_version INTEGER NOT NULL,
    previous_stage VARCHAR(50),
    new_stage VARCHAR(50) NOT NULL,
    promoted_by VARCHAR(100),
    promotion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deployment_notes TEXT,
    
    CONSTRAINT check_stage_value CHECK (new_stage IN ('Staging', 'Production', 'Archived'))
);

-- Table: model_performance_tracking
-- Tracks model performance over time in production
CREATE TABLE IF NOT EXISTS model_performance_tracking (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    model_version INTEGER NOT NULL,
    tracking_date DATE NOT NULL,
    
    -- Performance metrics
    total_predictions INTEGER DEFAULT 0,
    avg_prediction_time_ms FLOAT,
    error_count INTEGER DEFAULT 0,
    
    -- Business metrics (if available)
    accuracy FLOAT,
    precision_score FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    
    -- Drift detection
    data_drift_detected BOOLEAN DEFAULT FALSE,
    drift_score FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(model_name, model_version, tracking_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_deployment_history_model ON model_deployment_history(model_name, model_version);
CREATE INDEX IF NOT EXISTS idx_deployment_history_timestamp ON model_deployment_history(promotion_timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_tracking_model ON model_performance_tracking(model_name, model_version);
CREATE INDEX IF NOT EXISTS idx_performance_tracking_date ON model_performance_tracking(tracking_date);

-- Grant permissions on custom tables
GRANT ALL PRIVILEGES ON TABLE model_deployment_history TO mlflow;
GRANT ALL PRIVILEGES ON TABLE model_performance_tracking TO mlflow;
GRANT ALL PRIVILEGES ON SEQUENCE model_deployment_history_id_seq TO mlflow;
GRANT ALL PRIVILEGES ON SEQUENCE model_performance_tracking_id_seq TO mlflow;
