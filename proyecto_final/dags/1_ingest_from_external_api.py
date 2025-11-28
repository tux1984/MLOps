"""
DAG 1: Ingesta de Datos desde API Externa

Consume la API del profesor (http://10.43.100.103:8000) para obtener
datos de propiedades inmobiliarias (realtor dataset).

Cada request retorna un batch de datos diferente. El DAG debe:
1. Hacer request a la API con el número de grupo
2. Validar respuesta y extraer datos
3. Calcular hash para deduplicación
4. Insertar en raw_train, raw_validation, raw_test
5. Logging de operaciones en api_request_log

La API retorna error cuando todos los datos han sido recolectados.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import psycopg2
import psycopg2.extras
import requests
import hashlib
import pandas as pd
import logging
import os
import time

# Configuración
GROUP_NUMBER = int(os.getenv("GROUP_NUMBER", "3"))  # Número de grupo asignado
API_URL = os.getenv("API_URL", "http://10.43.100.103:8000")
RAW_DB_HOST = os.getenv("RAW_DB_HOST", "db-raw")
RAW_DB_PORT = int(os.getenv("RAW_DB_PORT", "5432"))
RAW_DB_NAME = os.getenv("RAW_DB_NAME", "rawdb")
RAW_DB_USER = os.getenv("RAW_DB_USER", "mlops_user")
RAW_DB_PASSWORD = os.getenv("RAW_DB_PASSWORD", "mlops_password")

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}


def get_raw_db_connection():
    """Establece conexión a base de datos RAW"""
    return psycopg2.connect(
        host=RAW_DB_HOST,
        port=RAW_DB_PORT,
        dbname=RAW_DB_NAME,
        user=RAW_DB_USER,
        password=RAW_DB_PASSWORD
    )


def calculate_row_hash(row: dict) -> str:
    """
    Calcula hash MD5 de una fila para deduplicación
    
    Args:
        row: Diccionario con datos de la propiedad
    
    Returns:
        str: Hash MD5
    """
    # Concatenar valores relevantes
    row_string = ''.join([str(v) for v in row.values() if v is not None])
    return hashlib.md5(row_string.encode()).hexdigest()


def get_next_request_count(**context) -> int:
    """
    Obtiene el próximo request_count desde la base de datos
    
    Returns:
        int: Siguiente request count
    """
    conn = get_raw_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT COALESCE(MAX(request_count), 0) + 1
            FROM api_request_log
            WHERE group_number = %s
        """, (GROUP_NUMBER,))
        
        next_count = cur.fetchone()[0]
        logger.info(f"Next request count: {next_count}")
        
        return next_count
        
    finally:
        cur.close()
        conn.close()


def fetch_data_from_api(**context) -> dict:
    """
    Hace request a la API externa para obtener batch de datos
    
    Returns:
        dict: Respuesta de la API con datos
    """
    ti = context['ti']
    request_count = ti.xcom_pull(task_ids='get_next_request_count')
    
    # Endpoint de la API
    endpoint = f"{API_URL}/data"
    
    # Parámetros del request
    # La API espera el día de la semana (Tuesday o Wednesday)
    # Usamos Tuesday para grupo 3
    day = "Tuesday" if GROUP_NUMBER == 3 else "Wednesday"
    
    params = {
        'group_number': GROUP_NUMBER,
        'day': day
    }
    
    logger.info(f"Fetching data from API: {endpoint}")
    logger.info(f"Parameters: group_number={GROUP_NUMBER}, day={day}, request_count={request_count}")
    
    start_time = time.time()
    
    try:
        response = requests.get(endpoint, params=params, timeout=300)
        
        execution_time = time.time() - start_time
        
        # Log del request
        conn = get_raw_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO api_request_log 
                (request_count, group_number, response_status_code, response_size, is_successful)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                request_count,
                GROUP_NUMBER,
                response.status_code,
                len(response.content),
                response.status_code == 200
            ))
            conn.commit()
        finally:
            cur.close()
            conn.close()
        
        # Validar respuesta
        if response.status_code == 200:
            api_data = response.json()
            logger.info(f"API request successful. Execution time: {execution_time:.2f}s")
            logger.info(f"API response keys: {list(api_data.keys())}")
            
            # La API devuelve un solo array 'data', necesitamos dividirlo en train/val/test
            all_data = api_data.get('data', [])
            total_records = len(all_data)
            logger.info(f"Total records received: {total_records}")
            
            # Dividir datos: 70% train, 15% validation, 15% test
            train_end = int(len(all_data) * 0.70)
            val_end = int(len(all_data) * 0.85)
            
            data = {
                'train': all_data[:train_end],
                'validation': all_data[train_end:val_end],
                'test': all_data[val_end:],
                'batch_number': api_data.get('batch_number', request_count)
            }
            
            logger.info(f"Split: train={len(data['train'])}, validation={len(data['validation'])}, test={len(data['test'])}")
            
            # Actualizar log con detalles
            conn = get_raw_db_connection()
            cur = conn.cursor()
            try:
                cur.execute("""
                    UPDATE api_request_log
                    SET num_records = %s
                    WHERE request_count = %s AND group_number = %s
                """, (total_records, request_count, GROUP_NUMBER))
                conn.commit()
            finally:
                cur.close()
                conn.close()
            
            return data
            
        elif response.status_code == 404:
            logger.info("API returned 404 - All data has been collected")
            return {"status": "complete", "message": "All data collected"}
            
        else:
            error_msg = f"API returned status {response.status_code}: {response.text}"
            logger.error(error_msg)
            
            # Log error
            conn = get_raw_db_connection()
            cur = conn.cursor()
            try:
                cur.execute("""
                    UPDATE api_request_log
                    SET error_message = %s
                    WHERE request_count = %s AND group_number = %s
                """, (error_msg, request_count, GROUP_NUMBER))
                conn.commit()
            finally:
                cur.close()
                conn.close()
            
            raise Exception(error_msg)
    
    except requests.Timeout:
        error_msg = "API request timeout after 300s"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    except Exception as e:
        error_msg = f"Error fetching data from API: {str(e)}"
        logger.error(error_msg)
        raise


def load_train_data(**context):
    """Carga datos de entrenamiento a raw_train"""
    ti = context['ti']
    data = ti.xcom_pull(task_ids='fetch_data_from_api')
    request_count = ti.xcom_pull(task_ids='get_next_request_count')
    
    if data.get('status') == 'complete':
        logger.info("No more train data to load")
        return
    
    if 'train' not in data or not data['train']:
        logger.warning("No train data in API response")
        return
    
    train_data = data['train']
    logger.info(f"Loading {len(train_data)} train records")
    
    conn = get_raw_db_connection()
    cur = conn.cursor()
    
    try:
        batch_id = int(time.time())
        inserted = 0
        duplicates = 0
        
        for row in train_data:
            row_hash = calculate_row_hash(row)
            
            try:
                cur.execute("""
                    INSERT INTO raw_train 
                    (row_hash, batch_id, request_count, brokered_by, status, price, 
                     bed, bath, acre_lot, street, city, state, zip_code, house_size, prev_sold_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (row_hash) DO NOTHING
                    RETURNING id
                """, (
                    row_hash,
                    batch_id,
                    request_count,
                    row.get('brokered_by'),
                    row.get('status'),
                    row.get('price'),
                    row.get('bed'),
                    row.get('bath'),
                    row.get('acre_lot'),
                    row.get('street'),
                    row.get('city'),
                    row.get('state'),
                    row.get('zip_code'),
                    row.get('house_size'),
                    row.get('prev_sold_date')
                ))
                
                if cur.fetchone():
                    inserted += 1
                else:
                    duplicates += 1
                    
            except Exception as e:
                logger.error(f"Error inserting row: {e}")
                continue
        
        conn.commit()
        logger.info(f"Train data loaded: {inserted} inserted, {duplicates} duplicates")
        
    finally:
        cur.close()
        conn.close()


def load_validation_data(**context):
    """Carga datos de validación a raw_validation"""
    ti = context['ti']
    data = ti.xcom_pull(task_ids='fetch_data_from_api')
    request_count = ti.xcom_pull(task_ids='get_next_request_count')
    
    if data.get('status') == 'complete':
        logger.info("No more validation data to load")
        return
    
    if 'validation' not in data or not data['validation']:
        logger.warning("No validation data in API response")
        return
    
    val_data = data['validation']
    logger.info(f"Loading {len(val_data)} validation records")
    
    conn = get_raw_db_connection()
    cur = conn.cursor()
    
    try:
        batch_id = int(time.time())
        inserted = 0
        duplicates = 0
        
        for row in val_data:
            row_hash = calculate_row_hash(row)
            
            try:
                cur.execute("""
                    INSERT INTO raw_validation 
                    (row_hash, batch_id, request_count, brokered_by, status, price, 
                     bed, bath, acre_lot, street, city, state, zip_code, house_size, prev_sold_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (row_hash) DO NOTHING
                    RETURNING id
                """, (
                    row_hash,
                    batch_id,
                    request_count,
                    row.get('brokered_by'),
                    row.get('status'),
                    row.get('price'),
                    row.get('bed'),
                    row.get('bath'),
                    row.get('acre_lot'),
                    row.get('street'),
                    row.get('city'),
                    row.get('state'),
                    row.get('zip_code'),
                    row.get('house_size'),
                    row.get('prev_sold_date')
                ))
                
                if cur.fetchone():
                    inserted += 1
                else:
                    duplicates += 1
                    
            except Exception as e:
                logger.error(f"Error inserting row: {e}")
                continue
        
        conn.commit()
        logger.info(f"Validation data loaded: {inserted} inserted, {duplicates} duplicates")
        
    finally:
        cur.close()
        conn.close()


def load_test_data(**context):
    """Carga datos de prueba a raw_test"""
    ti = context['ti']
    data = ti.xcom_pull(task_ids='fetch_data_from_api')
    request_count = ti.xcom_pull(task_ids='get_next_request_count')
    
    if data.get('status') == 'complete':
        logger.info("No more test data to load")
        return
    
    if 'test' not in data or not data['test']:
        logger.warning("No test data in API response")
        return
    
    test_data = data['test']
    logger.info(f"Loading {len(test_data)} test records")
    
    conn = get_raw_db_connection()
    cur = conn.cursor()
    
    try:
        batch_id = int(time.time())
        inserted = 0
        duplicates = 0
        
        for row in test_data:
            row_hash = calculate_row_hash(row)
            
            try:
                cur.execute("""
                    INSERT INTO raw_test 
                    (row_hash, batch_id, request_count, brokered_by, status, price, 
                     bed, bath, acre_lot, street, city, state, zip_code, house_size, prev_sold_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (row_hash) DO NOTHING
                    RETURNING id
                """, (
                    row_hash,
                    batch_id,
                    request_count,
                    row.get('brokered_by'),
                    row.get('status'),
                    row.get('price'),
                    row.get('bed'),
                    row.get('bath'),
                    row.get('acre_lot'),
                    row.get('street'),
                    row.get('city'),
                    row.get('state'),
                    row.get('zip_code'),
                    row.get('house_size'),
                    row.get('prev_sold_date')
                ))
                
                if cur.fetchone():
                    inserted += 1
                else:
                    duplicates += 1
                    
            except Exception as e:
                logger.error(f"Error inserting row: {e}")
                continue
        
        conn.commit()
        logger.info(f"Test data loaded: {inserted} inserted, {duplicates} duplicates")
        
    finally:
        cur.close()
        conn.close()


def log_ingestion_summary(**context):
    """Registra resumen de la ingesta"""
    ti = context['ti']
    request_count = ti.xcom_pull(task_ids='get_next_request_count')
    
    conn = get_raw_db_connection()
    cur = conn.cursor()
    
    try:
        # Contar registros por dataset
        cur.execute("""
            SELECT 
                COUNT(*) as total_train
            FROM raw_train
            WHERE request_count = %s
        """, (request_count,))
        train_count = cur.fetchone()[0]
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_validation
            FROM raw_validation
            WHERE request_count = %s
        """, (request_count,))
        val_count = cur.fetchone()[0]
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_test
            FROM raw_test
            WHERE request_count = %s
        """, (request_count,))
        test_count = cur.fetchone()[0]
        
        total = train_count + val_count + test_count
        
        # Insertar resumen
        cur.execute("""
            INSERT INTO ingestion_summary
            (batch_id, request_count, total_records, train_records, validation_records, test_records)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            int(time.time()),
            request_count,
            total,
            train_count,
            val_count,
            test_count
        ))
        
        conn.commit()
        
        logger.info("="*60)
        logger.info(f"INGESTION SUMMARY - Request {request_count}")
        logger.info(f"Group Number: {GROUP_NUMBER}")
        logger.info(f"Train records: {train_count}")
        logger.info(f"Validation records: {val_count}")
        logger.info(f"Test records: {test_count}")
        logger.info(f"Total records: {total}")
        logger.info("="*60)
        
    finally:
        cur.close()
        conn.close()


# DAG Definition
with DAG(
    '1_ingest_from_external_api',
    default_args=default_args,
    description='Ingesta datos desde API externa del profesor (realtor dataset)',
    schedule_interval='@daily',  # Ejecutar diariamente o manual
    start_date=days_ago(1),
    catchup=False,
    tags=['ingestion', 'api', 'realtor'],
) as dag:
    
    task_get_request_count = PythonOperator(
        task_id='get_next_request_count',
        python_callable=get_next_request_count,
        provide_context=True
    )
    
    task_fetch_api = PythonOperator(
        task_id='fetch_data_from_api',
        python_callable=fetch_data_from_api,
        provide_context=True
    )
    
    task_load_train = PythonOperator(
        task_id='load_train_data',
        python_callable=load_train_data,
        provide_context=True
    )
    
    task_load_validation = PythonOperator(
        task_id='load_validation_data',
        python_callable=load_validation_data,
        provide_context=True
    )
    
    task_load_test = PythonOperator(
        task_id='load_test_data',
        python_callable=load_test_data,
        provide_context=True
    )
    
    task_summary = PythonOperator(
        task_id='log_ingestion_summary',
        python_callable=log_ingestion_summary,
        provide_context=True
    )
    
    # Dependencies
    task_get_request_count >> task_fetch_api
    task_fetch_api >> [task_load_train, task_load_validation, task_load_test]
    [task_load_train, task_load_validation, task_load_test] >> task_summary
