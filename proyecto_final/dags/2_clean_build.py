"""
DAG 2: Preprocesamiento y Limpieza de Datos

Este DAG se encarga de:
1. Leer datos de raw-db (raw_train, raw_validation, raw_test)
2. Aplicar limpieza y transformaciones
3. Manejar valores faltantes
4. Codificar variables categóricas
5. Normalizar/escalar features numéricas
6. Guardar datos limpios en clean-db

Transformaciones aplicadas:
- Eliminación de duplicados
- Imputación de valores faltantes
- Encoding de categóricas (One-Hot, Label Encoding)
- Normalización de numéricas (StandardScaler)
- Feature engineering (si aplica)

Tablas generadas en clean-db:
- clean_train: Datos de entrenamiento limpios
- clean_validation: Datos de validación limpios
- clean_test: Datos de prueba limpios
- preprocessing_metadata: Parámetros de transformación
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import pandas as pd
from sqlalchemy import create_engine
from utils.data_loader import get_db_connection
from utils.preprocessing import (
    full_preprocessing_pipeline,
    handle_missing_values,
    encode_lab_results,
    count_diabetes_medications,
    encode_binary_features,
    encode_gender,
    encode_race,
    encode_readmitted_target,
    extract_age_numeric,
    select_features_for_model
)

# Configuración de conexiones
RAW_DB_URI = get_db_connection('raw')
CLEAN_DB_URI = get_db_connection('clean')


default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def load_raw_train(**context):
    """
    Carga datos de entrenamiento desde raw-db
    
    Returns:
        pd.DataFrame: Datos raw de entrenamiento
    """
    print("="*50)
    print("TAREA 1: CARGA DE DATOS RAW - TRAIN")
    print("="*50)
    
    engine = create_engine(RAW_DB_URI)
    
    query = "SELECT * FROM raw_train ORDER BY batch_id, id"
    df = pd.read_sql(query, engine)
    engine.dispose()
    
    print(f"✓ Datos raw_train cargados: {len(df)} registros")
    print(f"  Columnas: {len(df.columns)}")
    print(f"  Batches: {df['batch_id'].nunique() if 'batch_id' in df.columns else 'N/A'}")
    
    # Guardar en XCom para siguiente tarea
    context['ti'].xcom_push(key='raw_train_count', value=len(df))
    
    return df


def load_raw_validation(**context):
    """
    Carga datos de validación desde raw-db
    
    Returns:
        pd.DataFrame: Datos raw de validación
    """
    print("="*50)
    print("TAREA 2: CARGA DE DATOS RAW - VALIDATION")
    print("="*50)
    
    engine = create_engine(RAW_DB_URI)
    
    query = "SELECT * FROM raw_validation ORDER BY id"
    df = pd.read_sql(query, engine)
    engine.dispose()
    
    print(f"✓ Datos raw_validation cargados: {len(df)} registros")
    
    context['ti'].xcom_push(key='raw_val_count', value=len(df))
    
    return df


def load_raw_test(**context):
    """
    Carga datos de prueba desde raw-db
    
    Returns:
        pd.DataFrame: Datos raw de prueba
    """
    print("="*50)
    print("TAREA 3: CARGA DE DATOS RAW - TEST")
    print("="*50)
    
    engine = create_engine(RAW_DB_URI)
    
    query = "SELECT * FROM raw_test ORDER BY id"
    df = pd.read_sql(query, engine)
    engine.dispose()
    
    print(f"✓ Datos raw_test cargados: {len(df)} registros")
    
    context['ti'].xcom_push(key='raw_test_count', value=len(df))
    
    return df


def preprocess_train(**context):
    """
    Preprocesa datos de entrenamiento
    
    Aplica pipeline completo:
    - Limpieza de missing values
    - Encoding de categorías
    - Feature engineering
    - Normalización (opcional)
    
    Returns:
        pd.DataFrame: Datos limpios
    """
    print("="*50)
    print("TAREA 4: PREPROCESAMIENTO - TRAIN")
    print("="*50)
    
    # Obtener datos raw
    train_df = context['ti'].xcom_pull(task_ids='load_raw_train')
    
    if train_df is None or len(train_df) == 0:
        raise ValueError("No se encontraron datos de entrenamiento")
    
    # Aplicar pipeline completo
    clean_df, scaler = full_preprocessing_pipeline(
        train_df,
        is_training=True,
        scaler=None
    )
    
    print(f"✓ Preprocesamiento train completado: {len(clean_df)} registros")
    print(f"  Features finales: {len(clean_df.columns)}")
    
    # Guardar en XCom
    context['ti'].xcom_push(key='clean_train_count', value=len(clean_df))
    context['ti'].xcom_push(key='n_features', value=len(clean_df.columns))
    
    return clean_df


def preprocess_validation(**context):
    """
    Preprocesa datos de validación
    
    Usa los mismos parámetros que train (no re-entrena encoders/scalers)
    
    Returns:
        pd.DataFrame: Datos limpios
    """
    print("="*50)
    print("TAREA 5: PREPROCESAMIENTO - VALIDATION")
    print("="*50)
    
    val_df = context['ti'].xcom_pull(task_ids='load_raw_validation')
    
    if val_df is None or len(val_df) == 0:
        raise ValueError("No se encontraron datos de validación")
    
    # Aplicar mismo pipeline (sin entrenar)
    clean_df, _ = full_preprocessing_pipeline(
        val_df,
        is_training=False,
        scaler=None
    )
    
    print(f"✓ Preprocesamiento validation completado: {len(clean_df)} registros")
    
    context['ti'].xcom_push(key='clean_val_count', value=len(clean_df))
    
    return clean_df


def preprocess_test(**context):
    """
    Preprocesa datos de prueba
    
    Usa los mismos parámetros que train (no re-entrena encoders/scalers)
    
    Returns:
        pd.DataFrame: Datos limpios
    """
    print("="*50)
    print("TAREA 6: PREPROCESAMIENTO - TEST")
    print("="*50)
    
    test_df = context['ti'].xcom_pull(task_ids='load_raw_test')
    
    if test_df is None or len(test_df) == 0:
        raise ValueError("No se encontraron datos de prueba")
    
    # Aplicar mismo pipeline (sin entrenar)
    clean_df, _ = full_preprocessing_pipeline(
        test_df,
        is_training=False,
        scaler=None
    )
    
    print(f"✓ Preprocesamiento test completado: {len(clean_df)} registros")
    
    context['ti'].xcom_push(key='clean_test_count', value=len(clean_df))
    
    return clean_df


def normalize_numerical_features(**context):
    """
    Normaliza/escala features numéricas
    
    Usa StandardScaler para normalizar a media=0, std=1
    
    Returns:
        dict: DataFrames normalizados y parámetros de scaler
    """
    # Esta función es opcional ya que full_preprocessing_pipeline
    # puede incluir normalización si se descomenta esa sección
    # Por ahora, simplemente pasa los datos sin cambios
    print("⚠ Normalización opcional - actualmente deshabilitada")
    pass


def save_train_to_clean_db(**context):
    """
    Guarda datos limpios de train en clean-db
    
    Inserta registros en tabla clean_train
    """
    print("="*50)
    print("TAREA 7: GUARDADO EN CLEAN DB - TRAIN")
    print("="*50)
    
    clean_df = context['ti'].xcom_pull(task_ids='preprocess_train')
    
    if clean_df is None or len(clean_df) == 0:
        raise ValueError("No hay datos limpios para guardar")
    
    engine = create_engine(CLEAN_DB_URI)
    
    # Guardar en clean_train
    clean_df.to_sql(
        'clean_train',
        engine,
        if_exists='replace',
        index=False,
        chunksize=1000
    )
    
    engine.dispose()
    
    print(f"✓ {len(clean_df)} registros guardados en clean_train")
    
    return {'saved': len(clean_df)}


def save_validation_to_clean_db(**context):
    """
    Guarda datos limpios de validation en clean-db
    
    Inserta registros en tabla clean_validation
    """
    print("="*50)
    print("TAREA 8: GUARDADO EN CLEAN DB - VALIDATION")
    print("="*50)
    
    clean_df = context['ti'].xcom_pull(task_ids='preprocess_validation')
    
    if clean_df is None or len(clean_df) == 0:
        raise ValueError("No hay datos limpios para guardar")
    
    engine = create_engine(CLEAN_DB_URI)
    
    clean_df.to_sql(
        'clean_validation',
        engine,
        if_exists='replace',
        index=False,
        chunksize=1000
    )
    
    engine.dispose()
    
    print(f"✓ {len(clean_df)} registros guardados en clean_validation")
    
    return {'saved': len(clean_df)}


def save_test_to_clean_db(**context):
    """
    Guarda datos limpios de test en clean-db
    
    Inserta registros en tabla clean_test
    """
    print("="*50)
    print("TAREA 9: GUARDADO EN CLEAN DB - TEST")
    print("="*50)
    
    clean_df = context['ti'].xcom_pull(task_ids='preprocess_test')
    
    if clean_df is None or len(clean_df) == 0:
        raise ValueError("No hay datos limpios para guardar")
    
    engine = create_engine(CLEAN_DB_URI)
    
    clean_df.to_sql(
        'clean_test',
        engine,
        if_exists='replace',
        index=False,
        chunksize=1000
    )
    
    engine.dispose()
    
    print(f"✓ {len(clean_df)} registros guardados en clean_test")
    
    return {'saved': len(clean_df)}


def log_preprocessing_summary(**context):
    """
    Genera resumen del preprocesamiento
    
    Muestra estadísticas de transformación y calidad de datos
    """
    print("="*50)
    print("RESUMEN DE PREPROCESAMIENTO")
    print("="*50)
    
    # Obtener conteos
    raw_train = context['ti'].xcom_pull(task_ids='load_raw_train', key='raw_train_count')
    raw_val = context['ti'].xcom_pull(task_ids='load_raw_validation', key='raw_val_count')
    raw_test = context['ti'].xcom_pull(task_ids='load_raw_test', key='raw_test_count')
    
    clean_train = context['ti'].xcom_pull(task_ids='preprocess_train', key='clean_train_count')
    clean_val = context['ti'].xcom_pull(task_ids='preprocess_validation', key='clean_val_count')
    clean_test = context['ti'].xcom_pull(task_ids='preprocess_test', key='clean_test_count')
    
    n_features = context['ti'].xcom_pull(task_ids='preprocess_train', key='n_features')
    
    print(f"\\nRegistros RAW:")
    print(f"  - Train: {raw_train}")
    print(f"  - Validation: {raw_val}")
    print(f"  - Test: {raw_test}")
    print(f"  TOTAL: {raw_train + raw_val + raw_test}")
    
    print(f"\\nRegistros CLEAN:")
    print(f"  - Train: {clean_train}")
    print(f"  - Validation: {clean_val}")
    print(f"  - Test: {clean_test}")
    print(f"  TOTAL: {clean_train + clean_val + clean_test}")
    
    print(f"\\nFeatures finales: {n_features}")
    
    # Calcular porcentaje de datos retenidos
    retention_train = (clean_train / raw_train * 100) if raw_train > 0 else 0
    retention_val = (clean_val / raw_val * 100) if raw_val > 0 else 0
    retention_test = (clean_test / raw_test * 100) if raw_test > 0 else 0
    
    print(f"\\nRetención de datos:")
    print(f"  - Train: {retention_train:.1f}%")
    print(f"  - Validation: {retention_val:.1f}%")
    print(f"  - Test: {retention_test:.1f}%")
    
    print("\\n✓ Preprocesamiento completado exitosamente")
    print("="*50)
    """
    Guarda datos limpios en clean-db
    
    Guarda:
    - clean_train: Datos de entrenamiento procesados
    - clean_validation: Datos de validación procesados
    - clean_test: Datos de prueba procesados
    - preprocessing_metadata: Parámetros de transformación
    """
    # TODO: Implementar guardado en clean-db
    # - Conectar a clean-db
    # - Insertar datos en tablas correspondientes
    # - Guardar metadata de preprocesamiento
    # - Validar inserción correcta
    # - Retornar estadísticas
    pass


def generate_data_quality_report(**context):
    """
    Genera reporte de calidad de datos
    
    Incluye:
    - Estadísticas descriptivas
    - Distribución de variables
    - Correlaciones
    - Missing values antes/después
    - Outliers detectados
    """
    # TODO: Implementar reporte de calidad
    # - Generar estadísticas
    # - Crear visualizaciones
    # - Guardar reporte en shared volume
    # - Loggear resumen
    pass


# Definición del DAG
with DAG(
    '2_clean_build',
    default_args=default_args,
    description='Preprocesamiento y limpieza de datos RAW -> CLEAN',
    schedule_interval=None,  # Manual trigger after DAG 1
    catchup=False,
    tags=['preprocessing', 'data-cleaning', 'feature-engineering'],
) as dag:

    # Task 1: Cargar datos raw
    # Task 1: Carga de datos raw
    task_load_train = PythonOperator(
        task_id='load_raw_train',
        python_callable=load_raw_train,
        provide_context=True,
    )

    task_load_val = PythonOperator(
        task_id='load_raw_validation',
        python_callable=load_raw_validation,
        provide_context=True,
    )

    task_load_test = PythonOperator(
        task_id='load_raw_test',
        python_callable=load_raw_test,
        provide_context=True,
    )

    # Task 2: Preprocesamiento
    task_preprocess_train = PythonOperator(
        task_id='preprocess_train',
        python_callable=preprocess_train,
        provide_context=True,
    )

    task_preprocess_val = PythonOperator(
        task_id='preprocess_validation',
        python_callable=preprocess_validation,
        provide_context=True,
    )

    task_preprocess_test = PythonOperator(
        task_id='preprocess_test',
        python_callable=preprocess_test,
        provide_context=True,
    )

    # Task 3: Guardado en clean-db
    task_save_train = PythonOperator(
        task_id='save_train_to_clean_db',
        python_callable=save_train_to_clean_db,
        provide_context=True,
    )

    task_save_val = PythonOperator(
        task_id='save_validation_to_clean_db',
        python_callable=save_validation_to_clean_db,
        provide_context=True,
    )

    task_save_test = PythonOperator(
        task_id='save_test_to_clean_db',
        python_callable=save_test_to_clean_db,
        provide_context=True,
    )

    # Task 4: Resumen
    task_summary = PythonOperator(
        task_id='log_preprocessing_summary',
        python_callable=log_preprocessing_summary,
        provide_context=True,
    )

    # Flujo del DAG
    # 1. Cargar datos raw en paralelo
    # 2. Preprocesar cada conjunto
    # 3. Guardar en clean-db
    # 4. Generar resumen
    
    task_load_train >> task_preprocess_train >> task_save_train
    task_load_val >> task_preprocess_val >> task_save_val
    task_load_test >> task_preprocess_test >> task_save_test
    
    [task_save_train, task_save_val, task_save_test] >> task_summary
