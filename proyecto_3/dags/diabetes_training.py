"""
Airflow DAG: Entrenamiento de modelos de ML con MLflow.
Entrena múltiples modelos, registra en MLflow y promueve el mejor a Production.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd
import pendulum
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine

# Configuración
CLEAN_DB_HOST = os.environ.get("CLEAN_DB_HOST", "db-clean")
CLEAN_DB_PORT = os.environ.get("CLEAN_DB_PORT", "5432")
CLEAN_DB_NAME = os.environ.get("CLEAN_DB_NAME", "cleandb")
CLEAN_DB_USER = os.environ.get("CLEAN_DB_USER", "postgres")
CLEAN_DB_PASSWORD = os.environ.get("CLEAN_DB_PASSWORD", "postgres")

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")

CLEAN_CONN_URI = f"postgresql+psycopg2://{CLEAN_DB_USER}:{CLEAN_DB_PASSWORD}@{CLEAN_DB_HOST}:{CLEAN_DB_PORT}/{CLEAN_DB_NAME}"


def prepare_training_data(**context) -> dict:
    """Prepara datasets de train, validation, test desde CLEAN DB."""
    df = pd.read_sql_table('diabetes_clean', CLEAN_CONN_URI)
    
    if df.empty:
        raise AirflowException("No hay datos en diabetes_clean. Ejecute preprocessing primero.")
    
    # Separar por split_type
    train_df = df[df['split_type'] == 'train'].copy()
    val_df = df[df['split_type'] == 'validation'].copy()
    test_df = df[df['split_type'] == 'test'].copy()
    
    print(f"Train: {len(train_df)}, Validation: {len(val_df)}, Test: {len(test_df)}")
    
    if train_df.empty or val_df.empty:
        raise AirflowException("Train o validation vacíos")
    
    # Guardar temporalmente
    from pathlib import Path
    shared_dir = Path(os.environ.get("SHARED_DIR", "/shared"))
    train_path = shared_dir / "train_clean.csv"
    val_path = shared_dir / "val_clean.csv"
    test_path = shared_dir / "test_clean.csv"
    
    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    return {
        'train': str(train_path),
        'validation': str(val_path),
        'test': str(test_path)
    }


def train_models_with_mlflow(**context) -> dict:
    """
    Entrena múltiples modelos con diferentes hiperparámetros.
    Registra todo en MLflow y retorna el mejor modelo.
    """
    import mlflow
    import mlflow.sklearn
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score, 
        classification_report, confusion_matrix
    )
    import numpy as np
    
    # Configurar MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("diabetes_readmission_prediction")
    
    paths = context['ti'].xcom_pull(task_ids='prepare_data')
    
    train_df = pd.read_csv(paths['train'])
    val_df = pd.read_csv(paths['validation'])
    
    # Preparar features y target
    # Target: readmitted (NO, <30, >30) -> clasificación multiclase
    feature_cols = [
        'age_numeric', 'time_in_hospital', 'num_lab_procedures', 'num_procedures',
        'num_medications', 'number_outpatient', 'number_emergency', 'number_inpatient',
        'number_diagnoses', 'max_glu_serum_encoded', 'a1cresult_encoded',
        'change_encoded', 'diabetesmed_encoded', 'num_diabetes_meds'
    ]
    
    X_train = train_df[feature_cols]
    y_train = train_df['readmitted']
    
    X_val = val_df[feature_cols]
    y_val = val_df['readmitted']
    
    # Codificar target
    le = LabelEncoder()
    y_train_encoded = le.fit_transform(y_train)
    y_val_encoded = le.transform(y_val)
    
    # Escalar features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # Modelos a entrenar
    models = {
        'logistic_regression': LogisticRegression(max_iter=500, random_state=42),
        'random_forest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
        'gradient_boosting': GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42),
    }
    
    best_model = None
    best_f1 = 0
    best_run_id = None
    
    for model_name, model in models.items():
        with mlflow.start_run(run_name=model_name) as run:
            print(f"\n=== Entrenando {model_name} ===")
            
            # Entrenar
            model.fit(X_train_scaled, y_train_encoded)
            
            # Predecir
            y_pred = model.predict(X_val_scaled)
            
            # Métricas
            accuracy = accuracy_score(y_val_encoded, y_pred)
            precision = precision_score(y_val_encoded, y_pred, average='weighted')
            recall = recall_score(y_val_encoded, y_pred, average='weighted')
            f1 = f1_score(y_val_encoded, y_pred, average='weighted')
            
            print(f"Accuracy: {accuracy:.4f}")
            print(f"Precision: {precision:.4f}")
            print(f"Recall: {recall:.4f}")
            print(f"F1-Score: {f1:.4f}")
            
            # Registrar parámetros
            mlflow.log_params(model.get_params())
            
            # Registrar métricas
            mlflow.log_metric("accuracy", accuracy)
            mlflow.log_metric("precision", precision)
            mlflow.log_metric("recall", recall)
            mlflow.log_metric("f1_score", f1)
            
            # Registrar modelo
            mlflow.sklearn.log_model(
                model,
                artifact_path="model",
                registered_model_name=f"diabetes_{model_name}",
            )
            
            # Registrar scaler y label encoder
            import joblib
            scaler_path = f"/tmp/scaler_{model_name}.pkl"
            le_path = f"/tmp/label_encoder_{model_name}.pkl"
            joblib.dump(scaler, scaler_path)
            joblib.dump(le, le_path)
            mlflow.log_artifact(scaler_path, artifact_path="preprocessing")
            mlflow.log_artifact(le_path, artifact_path="preprocessing")
            
            # Tracking del mejor modelo
            if f1 > best_f1:
                best_f1 = f1
                best_model = model_name
                best_run_id = run.info.run_id
    
    print(f"\n=== Mejor modelo: {best_model} (F1={best_f1:.4f}) ===")
    
    return {
        'best_model': best_model,
        'best_f1': best_f1,
        'best_run_id': best_run_id
    }


def promote_best_model_to_production(**context) -> None:
    """Promueve automáticamente el mejor modelo a stage 'Production' en MLflow."""
    import mlflow
    from mlflow.tracking import MlflowClient
    
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()
    
    best_info = context['ti'].xcom_pull(task_ids='train_models')
    best_model_name = f"diabetes_{best_info['best_model']}"
    
    print(f"Promoviendo modelo '{best_model_name}' a Production")
    
    # Obtener la última versión del modelo
    model_versions = client.search_model_versions(f"name='{best_model_name}'")
    
    if not model_versions:
        raise AirflowException(f"No se encontraron versiones para {best_model_name}")
    
    # Ordenar por versión (la más reciente)
    latest_version = sorted(model_versions, key=lambda x: int(x.version), reverse=True)[0]
    
    # Transicionar a Production
    client.transition_model_version_stage(
        name=best_model_name,
        version=latest_version.version,
        stage="Production",
        archive_existing_versions=True  # Archivar versiones previas en Production
    )
    
    print(f"Modelo {best_model_name} versión {latest_version.version} promovido a Production")


# Definición del DAG
default_args = {
    'owner': 'mlops',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'diabetes_training',
    default_args=default_args,
    description='Entrenamiento de modelos con MLflow y promoción automática',
    schedule_interval='@weekly',  # Entrenar semanalmente
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    tags=['diabetes', 'training', 'mlflow'],
) as dag:
    
    prepare_task = PythonOperator(
        task_id='prepare_data',
        python_callable=prepare_training_data,
    )
    
    train_task = PythonOperator(
        task_id='train_models',
        python_callable=train_models_with_mlflow,
    )
    
    promote_task = PythonOperator(
        task_id='promote_to_production',
        python_callable=promote_best_model_to_production,
    )
    
    prepare_task >> train_task >> promote_task
