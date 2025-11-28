"""
DAG 1: Ingesta de Datos en Batches de 15,000 registros

Este DAG se encarga de:
1. Descargar el dataset de diabetes desde URL externa
2. Dividir los datos en train/validation/test (70/15/15)
3. Cargar los datos en batches de 15,000 registros a PostgreSQL (raw-db)
4. Calcular row_hash para cada registro (detección de duplicados)
5. Registrar metadata de cada batch

Tablas generadas en raw-db:
- raw_train: Datos de entrenamiento
- raw_validation: Datos de validación
- raw_test: Datos de prueba
- batch_metadata: Información de cada batch cargado
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
from pathlib import Path
import pandas as pd
from utils.data_loader import (
    download_dataset as dl_dataset,
    split_dataset as split_ds,
    normalize_column_names,
    load_to_postgres,
    get_db_connection
)

# Configuración
DATASET_URL = "https://docs.google.com/uc?export=download&confirm={{VALUE}}&id=1k5-1caezQ3zWJbKaiMULTGq-3sz6uThC"
SHARED_DIR = Path(os.getenv('SHARED_DIR', '/opt/airflow/shared'))
BATCH_SIZE = 15000

# Conexiones a DB
RAW_DB_URI = get_db_connection('raw')


default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def download_dataset(**context):
    """
    Descarga el dataset de diabetes desde URL externa
    
    Returns:
        str: Path del archivo descargado
    """
    print("="*50)
    print("TAREA 1: DESCARGA DE DATASET")
    print("="*50)
    
    data_dir = SHARED_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = data_dir / "diabetes.csv"
    
    # Descargar dataset
    filepath = dl_dataset(DATASET_URL, filepath, force_download=False)
    
    # Validar descarga
    df_sample = pd.read_csv(filepath, nrows=5)
    print(f"✓ Columnas detectadas: {len(df_sample.columns)}")
    print(f"✓ Primeras columnas: {list(df_sample.columns[:5])}")
    
    context['ti'].xcom_push(key='dataset_path', value=str(filepath))
    print(f"✓ Dataset descargado: {filepath}")
    
    return str(filepath)


def split_dataset(**context):
    """
    Divide el dataset en train/validation/test
    
    Split: 70% train, 15% validation, 15% test
    
    Returns:
        dict: Paths de los archivos generados
    """
    print("="*50)
    print("TAREA 2: SPLIT DE DATASET")
    print("="*50)
    
    dataset_path = context['ti'].xcom_pull(task_ids='download_dataset', key='dataset_path')
    
    # Leer dataset
    df = pd.read_csv(dataset_path)
    print(f"Dataset cargado: {len(df)} registros")
    
    # Normalizar columnas
    df = normalize_column_names(df)
    print(f"Columnas normalizadas: {list(df.columns[:5])}...")
    
    # Split dataset (70/15/15)
    train_df, val_df, test_df = split_ds(
        df,
        train_size=0.7,
        val_size=0.15,
        test_size=0.15,
        random_state=42,
        stratify_column='readmitted' if 'readmitted' in df.columns else None
    )
    
    # Guardar splits
    split_dir = SHARED_DIR / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    
    train_path = split_dir / "train.csv"
    val_path = split_dir / "validation.csv"
    test_path = split_dir / "test.csv"
    
    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    # Calcular número de batches
    n_batches = (len(train_df) + BATCH_SIZE - 1) // BATCH_SIZE
    
    result = {
        'train_path': str(train_path),
        'val_path': str(val_path),
        'test_path': str(test_path),
        'n_batches': n_batches,
        'train_size': len(train_df),
        'val_size': len(val_df),
        'test_size': len(test_df)
    }
    
    context['ti'].xcom_push(key='split_info', value=result)
    print(f"✓ Split completado: {n_batches} batches de entrenamiento")
    
    return result


def load_train_batches(**context):
    """
    Carga datos de entrenamiento en batches de 15,000 registros
    
    Para cada batch:
    - Calcular row_hash (MD5 de todos los campos concatenados)
    - Verificar duplicados
    - Insertar en tabla raw_train
    - Registrar metadata en batch_metadata
    """
    print("="*50)
    print("TAREA 3: CARGA DE BATCHES DE ENTRENAMIENTO")
    print("="*50)
    
    split_info = context['ti'].xcom_pull(task_ids='split_dataset', key='split_info')
    train_path = split_info['train_path']
    n_batches = split_info['n_batches']
    
    # Leer archivo de entrenamiento
    train_df = pd.read_csv(train_path)
    print(f"Dataset de entrenamiento: {len(train_df)} registros")
    print(f"Cargando en {n_batches} batches de {BATCH_SIZE} registros")
    
    total_inserted = 0
    
    for batch_num in range(n_batches):
        start_idx = batch_num * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(train_df))
        batch_df = train_df.iloc[start_idx:end_idx].copy()
        
        print(f"\n[BATCH {batch_num+1}/{n_batches}] Procesando {len(batch_df)} registros...")
        
        # Cargar a PostgreSQL
        inserted = load_to_postgres(
            df=batch_df,
            table_name='raw_train',
            connection_uri=RAW_DB_URI,
            batch_id=batch_num + 1,
            if_exists='append',
            chunksize=1000,
            add_row_hash=True
        )
        
        total_inserted += inserted
        print(f"[BATCH {batch_num+1}/{n_batches}] ✓ {inserted} registros insertados")
    
    print(f"\n✓ TOTAL: {total_inserted} registros de entrenamiento cargados")
    
    return {'total_inserted': total_inserted, 'n_batches': n_batches}


def load_validation_data(**context):
    """
    Carga datos de validación completos (sin batches)
    
    Inserta todos los registros de validación en raw_validation
    """
    print("="*50)
    print("TAREA 4: CARGA DE DATOS DE VALIDACIÓN")
    print("="*50)
    
    split_info = context['ti'].xcom_pull(task_ids='split_dataset', key='split_info')
    val_path = split_info['val_path']
    
    # Leer archivo de validación
    val_df = pd.read_csv(val_path)
    print(f"Dataset de validación: {len(val_df)} registros")
    
    # Cargar a PostgreSQL
    inserted = load_to_postgres(
        df=val_df,
        table_name='raw_validation',
        connection_uri=RAW_DB_URI,
        batch_id=1,
        if_exists='append',
        chunksize=1000,
        add_row_hash=True
    )
    
    print(f"✓ {inserted} registros de validación cargados")
    
    return {'inserted': inserted}


def load_test_data(**context):
    """
    Carga datos de prueba completos (sin batches)
    
    Inserta todos los registros de test en raw_test
    """
    print("="*50)
    print("TAREA 5: CARGA DE DATOS DE PRUEBA")
    print("="*50)
    
    split_info = context['ti'].xcom_pull(task_ids='split_dataset', key='split_info')
    test_path = split_info['test_path']
    
    # Leer archivo de prueba
    test_df = pd.read_csv(test_path)
    print(f"Dataset de prueba: {len(test_df)} registros")
    
    # Cargar a PostgreSQL
    inserted = load_to_postgres(
        df=test_df,
        table_name='raw_test',
        connection_uri=RAW_DB_URI,
        batch_id=1,
        if_exists='append',
        chunksize=1000,
        add_row_hash=True
    )
    
    print(f"✓ {inserted} registros de prueba cargados")
    
    return {'inserted': inserted}


def log_ingestion_summary(**context):
    """
    Registra resumen de la ingesta completa
    
    Genera reporte con:
    - Total de registros por tabla
    - Número de batches cargados
    - Duplicados detectados
    - Tiempo total de ejecución
    """
    print("="*50)
    print("RESUMEN DE INGESTA")
    print("="*50)
    
    split_info = context['ti'].xcom_pull(task_ids='split_dataset', key='split_info')
    train_info = context['ti'].xcom_pull(task_ids='load_train_batches')
    val_info = context['ti'].xcom_pull(task_ids='load_validation_data')
    test_info = context['ti'].xcom_pull(task_ids='load_test_data')
    
    print(f"\\nDataset splits:")
    print(f"  - Train: {split_info['train_size']} registros ({train_info['n_batches']} batches)")
    print(f"  - Validation: {split_info['val_size']} registros")
    print(f"  - Test: {split_info['test_size']} registros")
    
    print(f"\\nRegistros insertados:")
    print(f"  - Train: {train_info['total_inserted']}")
    print(f"  - Validation: {val_info['inserted']}")
    print(f"  - Test: {test_info['inserted']}")
    
    total = train_info['total_inserted'] + val_info['inserted'] + test_info['inserted']
    print(f"\\n✓ TOTAL: {total} registros cargados exitosamente")
    print("="*50)


# Definición del DAG
with DAG(
    '1_raw_batch_ingest_15k',
    default_args=default_args,
    description='Ingesta de datos de diabetes en batches de 15k registros',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['ingestion', 'raw-data', 'batch-processing'],
) as dag:

    # Task 1: Descargar dataset
    task_download = PythonOperator(
        task_id='download_dataset',
        python_callable=download_dataset,
        provide_context=True,
    )

    # Task 2: Dividir dataset
    task_split = PythonOperator(
        task_id='split_dataset',
        python_callable=split_dataset,
        provide_context=True,
    )

    # Task 3: Cargar train en batches
    task_load_train = PythonOperator(
        task_id='load_train_batches',
        python_callable=load_train_batches,
        provide_context=True,
    )

    # Task 4: Cargar validation
    task_load_val = PythonOperator(
        task_id='load_validation_data',
        python_callable=load_validation_data,
        provide_context=True,
    )

    # Task 5: Cargar test
    task_load_test = PythonOperator(
        task_id='load_test_data',
        python_callable=load_test_data,
        provide_context=True,
    )

    # Task 6: Resumen de ingesta
    task_summary = PythonOperator(
        task_id='log_ingestion_summary',
        python_callable=log_ingestion_summary,
        provide_context=True,
    )

    # Flujo del DAG
    task_download >> task_split
    task_split >> [task_load_train, task_load_val, task_load_test]
    [task_load_train, task_load_val, task_load_test] >> task_summary
