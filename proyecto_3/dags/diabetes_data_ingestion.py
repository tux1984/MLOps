"""
Airflow DAG: Ingesta de datos de diabetes en batches desde URL externa.
Descarga el dataset y lo carga en lotes de 15,000 registros a la tabla RAW.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pendulum
import requests
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text

# Configuración de base de datos
RAW_DB_HOST = os.environ.get("RAW_DB_HOST", "db-raw")
RAW_DB_PORT = os.environ.get("RAW_DB_PORT", "5432")
RAW_DB_NAME = os.environ.get("RAW_DB_NAME", "rawdb")
RAW_DB_USER = os.environ.get("RAW_DB_USER", "postgres")
RAW_DB_PASSWORD = os.environ.get("RAW_DB_PASSWORD", "postgres")
SHARED_DIR = Path(os.environ.get("SHARED_DIR", "/shared"))

CONN_URI = f"postgresql+psycopg2://{RAW_DB_USER}:{RAW_DB_PASSWORD}@{RAW_DB_HOST}:{RAW_DB_PORT}/{RAW_DB_NAME}"
DATASET_URL = "https://docs.google.com/uc?export=download&confirm={{VALUE}}&id=1k5-1caezQ3zWJbKaiMULTGq-3sz6uThC"
BATCH_SIZE = 15000  # Requisito: lotes de 15,000 registros


def download_diabetes_dataset(**context) -> str:
    """Descarga el dataset de diabetes y lo guarda localmente."""
    data_dir = SHARED_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = data_dir / "Diabetes.csv"
    
    # Descargar solo si no existe
    if not filepath.exists():
        print(f"Descargando dataset desde {DATASET_URL}")
        response = requests.get(DATASET_URL, allow_redirects=True, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"Dataset descargado: {filepath}")
    else:
        print(f"Dataset ya existe: {filepath}")
    
    # Inspeccionar columnas del CSV
    df_sample = pd.read_csv(filepath, nrows=5)
    print(f"Columnas del CSV: {list(df_sample.columns)}")
    print(f"Total columnas: {len(df_sample.columns)}")
    
    return str(filepath)


def split_dataset(**context) -> dict:
    """
    Divide el dataset en train, validation y test.
    Train se procesará en batches, validation y test se cargan completos.
    """
    filepath = context['ti'].xcom_pull(task_ids='download_dataset')
    
    df = pd.read_csv(filepath)
    print(f"Dataset cargado: {len(df)} registros")
    
    # Normalizar nombres de columnas (lowercase para PostgreSQL)
    df.columns = df.columns.str.lower().str.replace('-', '_')
    print(f"Columnas normalizadas: {list(df.columns[:10])}...")
    
    # Dividir dataset: 70% train, 15% validation, 15% test
    from sklearn.model_selection import train_test_split
    
    train_df, temp_df = train_test_split(df, test_size=0.3, random_state=42)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42)
    
    print(f"Train: {len(train_df)}, Validation: {len(val_df)}, Test: {len(test_df)}")
    
    # Guardar splits temporalmente
    split_dir = SHARED_DIR / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    
    train_path = split_dir / "train.csv"
    val_path = split_dir / "validation.csv"
    test_path = split_dir / "test.csv"
    
    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    return {
        'train': str(train_path),
        'validation': str(val_path),
        'test': str(test_path),
        'train_batches': (len(train_df) + BATCH_SIZE - 1) // BATCH_SIZE
    }


def load_validation_test_data(**context) -> None:
    """Carga validation y test completos (no en batches)."""
    splits = context['ti'].xcom_pull(task_ids='split_dataset')
    engine = create_engine(CONN_URI)
    
    for split_type in ['validation', 'test']:
        print(f"[{split_type.upper()}] Iniciando carga...")
        df = pd.read_csv(splits[split_type])
        
        df['split_type'] = split_type
        df['batch_number'] = 0
        
        # Calcular row_hash
        df['row_hash'] = df.apply(
            lambda row: hashlib.md5(
                f"{row.get('encounter_id', '')}|{row.get('patient_nbr', '')}|{row.get('time_in_hospital', '')}".encode()
            ).hexdigest(),
            axis=1
        )
        
        # Insertar en chunks
        df.to_sql('diabetes_raw', engine, if_exists='append', index=False, method='multi', chunksize=1000)
        print(f"[{split_type.upper()}] ✓ {len(df)} registros cargados")


def load_train_batch(**context) -> None:
    """Carga un batch específico del conjunto de entrenamiento."""
    batch_num = context['params']['batch_num']
    splits = context['ti'].xcom_pull(task_ids='split_dataset')
    
    train_df = pd.read_csv(splits['train'])
    
    # Obtener el batch correspondiente
    start_idx = batch_num * BATCH_SIZE
    end_idx = min(start_idx + BATCH_SIZE, len(train_df))
    batch_df = train_df.iloc[start_idx:end_idx].copy()
    
    batch_df['split_type'] = 'train'
    batch_df['batch_number'] = batch_num
    
    # Calcular row_hash
    batch_df['row_hash'] = batch_df.apply(
        lambda row: hashlib.md5(
            f"{row.get('encounter_id', '')}|{row.get('patient_nbr', '')}|{row.get('time_in_hospital', '')}".encode()
        ).hexdigest(),
        axis=1
    )
    
    engine = create_engine(CONN_URI)
    batch_df.to_sql('diabetes_raw', engine, if_exists='append', index=False, method='multi', chunksize=1000)
    
    print(f"[BATCH {batch_num}] ✓ {len(batch_df)} registros cargados")


# Definición del DAG
default_args = {
    'owner': 'mlops',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=30),  # Timeout de 30 minutos por tarea
}

with DAG(
    'diabetes_data_ingestion',
    default_args=default_args,
    description='Ingesta de datos de diabetes en batches',
    schedule_interval='@daily',
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    tags=['diabetes', 'ingestion', 'raw-data'],
) as dag:
    
    download_task = PythonOperator(
        task_id='download_dataset',
        python_callable=download_diabetes_dataset,
    )
    
    split_task = PythonOperator(
        task_id='split_dataset',
        python_callable=split_dataset,
    )
    
    load_val_test_task = PythonOperator(
        task_id='load_validation_test',
        python_callable=load_validation_test_data,
    )
    
    # Crear tareas dinámicas para cada batch de train
    # Nota: En producción, usar Dynamic Task Mapping (Airflow 2.3+)
    # Para simplicidad, creamos 7 batches (asumiendo ~100k registros en train)
    batch_tasks = []
    for i in range(7):
        task = PythonOperator(
            task_id=f'load_train_batch_{i}',
            python_callable=load_train_batch,
            params={'batch_num': i},
        )
        batch_tasks.append(task)
    
    # Dependencias
    download_task >> split_task >> load_val_test_task
    split_task >> batch_tasks
