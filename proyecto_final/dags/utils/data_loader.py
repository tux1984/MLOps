"""
Módulo de utilidades para carga de datos

Funciones para:
- Descarga de datasets
- Cálculo de row_hash para deduplicación
- Carga de datos en batches a PostgreSQL
"""

import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from sqlalchemy import create_engine, text
from sklearn.model_selection import train_test_split


def download_dataset(url: str, save_path: Path, force_download: bool = False) -> Path:
    """
    Descarga dataset desde URL y lo guarda localmente
    
    Args:
        url: URL del dataset
        save_path: Path donde guardar el archivo
        force_download: Si True, descarga incluso si el archivo existe
    
    Returns:
        Path: Ruta del archivo descargado
    """
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    if save_path.exists() and not force_download:
        print(f"✓ Dataset ya existe: {save_path}")
        return save_path
    
    print(f"Descargando dataset desde {url}")
    response = requests.get(url, allow_redirects=True, stream=True, timeout=300)
    response.raise_for_status()
    
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"✓ Dataset descargado: {save_path}")
    return save_path


def calculate_row_hash(row: pd.Series, key_columns: List[str]) -> str:
    """
    Calcula hash MD5 de una fila basándose en columnas clave
    
    Args:
        row: Fila de DataFrame
        key_columns: Lista de columnas para generar el hash
    
    Returns:
        str: Hash MD5 de 32 caracteres
    """
    values = '|'.join([str(row.get(col, '')) for col in key_columns])
    return hashlib.md5(values.encode()).hexdigest()


def split_dataset(
    df: pd.DataFrame,
    train_size: float = 0.7,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
    stratify_column: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Divide dataset en train, validation y test
    
    Args:
        df: DataFrame a dividir
        train_size: Proporción para training (0.7 = 70%)
        val_size: Proporción para validation
        test_size: Proporción para test
        random_state: Semilla para reproducibilidad
        stratify_column: Columna para estratificación (opcional)
    
    Returns:
        tuple: (train_df, val_df, test_df)
    """
    assert abs(train_size + val_size + test_size - 1.0) < 0.01, "Las proporciones deben sumar 1.0"
    
    stratify = df[stratify_column] if stratify_column else None
    
    # Primera división: train vs (val + test)
    train_df, temp_df = train_test_split(
        df,
        test_size=(val_size + test_size),
        random_state=random_state,
        stratify=stratify
    )
    
    # Segunda división: val vs test
    if stratify_column:
        stratify_temp = temp_df[stratify_column]
    else:
        stratify_temp = None
    
    val_df, test_df = train_test_split(
        temp_df,
        test_size=test_size / (val_size + test_size),
        random_state=random_state,
        stratify=stratify_temp
    )
    
    print(f"✓ División completada:")
    print(f"  - Train: {len(train_df)} ({len(train_df)/len(df)*100:.1f}%)")
    print(f"  - Validation: {len(val_df)} ({len(val_df)/len(df)*100:.1f}%)")
    print(f"  - Test: {len(test_df)} ({len(test_df)/len(df)*100:.1f}%)")
    
    return train_df, val_df, test_df


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas para PostgreSQL
    
    Args:
        df: DataFrame con columnas a normalizar
    
    Returns:
        pd.DataFrame: DataFrame con columnas normalizadas
    """
    df.columns = df.columns.str.lower().str.replace('-', '_').str.replace(' ', '_')
    return df


def load_to_postgres(
    df: pd.DataFrame,
    table_name: str,
    connection_uri: str,
    batch_id: Optional[int] = None,
    if_exists: str = 'append',
    chunksize: int = 1000,
    add_row_hash: bool = True,
    hash_columns: Optional[List[str]] = None
) -> int:
    """
    Carga DataFrame a tabla PostgreSQL
    
    Args:
        df: DataFrame a cargar
        table_name: Nombre de la tabla destino
        connection_uri: URI de conexión a PostgreSQL
        batch_id: ID del batch (opcional)
        if_exists: Comportamiento si tabla existe ('append', 'replace', 'fail')
        chunksize: Tamaño de chunks para inserción
        add_row_hash: Si True, agrega columna row_hash
        hash_columns: Columnas para calcular hash (si add_row_hash=True)
    
    Returns:
        int: Número de registros insertados
    """
    df_copy = df.copy()
    
    # Agregar batch_id si se proporciona
    if batch_id is not None:
        df_copy['batch_id'] = batch_id
    
    # Calcular row_hash si se solicita
    if add_row_hash:
        if hash_columns is None:
            hash_columns = ['encounter_id', 'patient_nbr', 'time_in_hospital']
        
        df_copy['row_hash'] = df_copy.apply(
            lambda row: calculate_row_hash(row, hash_columns),
            axis=1
        )
    
    # Crear engine y cargar datos
    engine = create_engine(connection_uri)
    
    try:
        rows_before = len(df_copy)
        df_copy.to_sql(
            table_name,
            engine,
            if_exists=if_exists,
            index=False,
            method='multi',
            chunksize=chunksize
        )
        print(f"✓ {rows_before} registros insertados en {table_name}")
        return rows_before
    
    except Exception as e:
        print(f"✗ Error al insertar en {table_name}: {e}")
        # Intentar inserción fila por fila para identificar duplicados
        inserted = 0
        for _, row in df_copy.iterrows():
            try:
                pd.DataFrame([row]).to_sql(
                    table_name,
                    engine,
                    if_exists='append',
                    index=False
                )
                inserted += 1
            except:
                pass  # Ignorar duplicados
        
        print(f"  {inserted}/{rows_before} registros insertados (duplicados omitidos)")
        return inserted
    
    finally:
        engine.dispose()


def create_batches(df: pd.DataFrame, batch_size: int) -> List[pd.DataFrame]:
    """
    Divide DataFrame en batches
    
    Args:
        df: DataFrame a dividir
        batch_size: Tamaño de cada batch
    
    Returns:
        list: Lista de DataFrames (batches)
    """
    n_batches = (len(df) + batch_size - 1) // batch_size
    batches = []
    
    for i in range(n_batches):
        start_idx = i * batch_size
        end_idx = min(start_idx + batch_size, len(df))
        batch = df.iloc[start_idx:end_idx].copy()
        batches.append(batch)
    
    print(f"✓ Creados {n_batches} batches de tamaño {batch_size}")
    return batches


def get_batch_metadata(connection_uri: str, table_name: str = 'batch_metadata') -> pd.DataFrame:
    """
    Obtiene metadata de batches cargados
    
    Args:
        connection_uri: URI de conexión a PostgreSQL
        table_name: Nombre de tabla de metadata
    
    Returns:
        pd.DataFrame: Metadata de batches
    """
    engine = create_engine(connection_uri)
    
    query = f"SELECT * FROM {table_name} ORDER BY load_timestamp DESC"
    df = pd.read_sql(query, engine)
    engine.dispose()
    
    return df


def check_duplicates(
    df: pd.DataFrame,
    connection_uri: str,
    table_name: str,
    hash_column: str = 'row_hash'
) -> Tuple[pd.DataFrame, int]:
    """
    Verifica duplicados comparando con tabla existente
    
    Args:
        df: DataFrame a verificar
        connection_uri: URI de conexión a PostgreSQL
        table_name: Nombre de tabla a comparar
        hash_column: Nombre de columna de hash
    
    Returns:
        tuple: (df_sin_duplicados, n_duplicados)
    """
    engine = create_engine(connection_uri)
    
    # Obtener hashes existentes
    query = f"SELECT {hash_column} FROM {table_name}"
    existing_hashes = pd.read_sql(query, engine)
    engine.dispose()
    
    existing_set = set(existing_hashes[hash_column])
    
    # Filtrar duplicados
    df_filtered = df[~df[hash_column].isin(existing_set)].copy()
    n_duplicates = len(df) - len(df_filtered)
    
    if n_duplicates > 0:
        print(f"⚠ {n_duplicates} duplicados encontrados y omitidos")
    
    return df_filtered, n_duplicates


def get_db_connection(db_type: str) -> str:
    """
    Obtiene URI de conexión según tipo de DB
    
    Args:
        db_type: Tipo de DB ('raw', 'clean', 'mlflow', 'airflow')
    
    Returns:
        str: URI de conexión
    """
    db_configs = {
        'raw': {
            'host': os.getenv('RAW_DB_HOST', 'db-raw'),
            'port': os.getenv('RAW_DB_PORT', '5432'),
            'name': os.getenv('RAW_DB_NAME', 'rawdb'),
            'user': os.getenv('RAW_DB_USER', 'postgres'),
            'password': os.getenv('RAW_DB_PASSWORD', 'postgres')
        },
        'clean': {
            'host': os.getenv('CLEAN_DB_HOST', 'db-clean'),
            'port': os.getenv('CLEAN_DB_PORT', '5432'),
            'name': os.getenv('CLEAN_DB_NAME', 'cleandb'),
            'user': os.getenv('CLEAN_DB_USER', 'postgres'),
            'password': os.getenv('CLEAN_DB_PASSWORD', 'postgres')
        },
        'mlflow': {
            'host': os.getenv('MLFLOW_DB_HOST', 'db-mlflow'),
            'port': os.getenv('MLFLOW_DB_PORT', '5432'),
            'name': os.getenv('MLFLOW_DB_NAME', 'mlflowdb'),
            'user': os.getenv('MLFLOW_DB_USER', 'postgres'),
            'password': os.getenv('MLFLOW_DB_PASSWORD', 'postgres')
        },
        'airflow': {
            'host': os.getenv('AIRFLOW_DB_HOST', 'db-airflow'),
            'port': os.getenv('AIRFLOW_DB_PORT', '5432'),
            'name': os.getenv('AIRFLOW_DB_NAME', 'airflowdb'),
            'user': os.getenv('AIRFLOW_DB_USER', 'postgres'),
            'password': os.getenv('AIRFLOW_DB_PASSWORD', 'postgres')
        }
    }
    
    config = db_configs.get(db_type)
    if not config:
        raise ValueError(f"DB type inválido: {db_type}. Use: {list(db_configs.keys())}")
    
    return f"postgresql+psycopg2://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['name']}"
