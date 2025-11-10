"""
Airflow DAG: Preprocesamiento de datos de diabetes.
Transforma datos de RAW a CLEAN con feature engineering.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd
import pendulum
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text

# Configuración de bases de datos
RAW_DB_HOST = os.environ.get("RAW_DB_HOST", "db-raw")
RAW_DB_PORT = os.environ.get("RAW_DB_PORT", "5432")
RAW_DB_NAME = os.environ.get("RAW_DB_NAME", "rawdb")
RAW_DB_USER = os.environ.get("RAW_DB_USER", "postgres")
RAW_DB_PASSWORD = os.environ.get("RAW_DB_PASSWORD", "postgres")

CLEAN_DB_HOST = os.environ.get("CLEAN_DB_HOST", "db-clean")
CLEAN_DB_PORT = os.environ.get("CLEAN_DB_PORT", "5432")
CLEAN_DB_NAME = os.environ.get("CLEAN_DB_NAME", "cleandb")
CLEAN_DB_USER = os.environ.get("CLEAN_DB_USER", "postgres")
CLEAN_DB_PASSWORD = os.environ.get("CLEAN_DB_PASSWORD", "postgres")

RAW_CONN_URI = f"postgresql+psycopg2://{RAW_DB_USER}:{RAW_DB_PASSWORD}@{RAW_DB_HOST}:{RAW_DB_PORT}/{RAW_DB_NAME}"
CLEAN_CONN_URI = f"postgresql+psycopg2://{CLEAN_DB_USER}:{CLEAN_DB_PASSWORD}@{CLEAN_DB_HOST}:{CLEAN_DB_PORT}/{CLEAN_DB_NAME}"


def extract_age_numeric(age_range: str) -> int:
    """Convierte rangos de edad a valor numérico central."""
    if pd.isna(age_range) or age_range == '?':
        return 50  # valor por defecto
    
    # Formato: "[0-10)", "[10-20)", etc.
    age_range = str(age_range).replace('[', '').replace(')', '')
    if '-' in age_range:
        parts = age_range.split('-')
        try:
            return (int(parts[0]) + int(parts[1])) // 2
        except:
            return 50
    return 50


def preprocess_diabetes_data(**context) -> None:
    """
    Preprocesa datos de RAW a CLEAN:
    - Limpieza de valores faltantes
    - Encoding de variables categóricas
    - Feature engineering
    - Manejo de desbalanceo
    """
    raw_engine = create_engine(RAW_CONN_URI)
    clean_engine = create_engine(CLEAN_CONN_URI)
    
    # Leer datos de RAW
    df = pd.read_sql_table('diabetes_raw', RAW_CONN_URI)
    
    if df.empty:
        raise AirflowException("No hay datos en diabetes_raw para preprocesar")
    
    print(f"Datos RAW cargados: {len(df)} registros")
    
    # --- LIMPIEZA ---
    # Eliminar duplicados por row_hash
    df = df.drop_duplicates(subset=['row_hash'], keep='first')
    
    # Reemplazar '?' con NaN
    df = df.replace('?', pd.NA)
    
    # --- FEATURE ENGINEERING ---
    
    # 1. Convertir edad a numérico
    df['age_numeric'] = df['age'].apply(extract_age_numeric)
    
    # 2. Codificar max_glu_serum (None=0, Norm=1, >200=2, >300=3)
    glu_mapping = {'None': 0, 'Norm': 1, '>200': 2, '>300': 3}
    df['max_glu_serum_encoded'] = df['max_glu_serum'].map(glu_mapping).fillna(0).astype(int)
    
    # 3. Codificar a1cresult (None=0, Norm=1, >7=2, >8=3)
    a1c_mapping = {'None': 0, 'Norm': 1, '>7': 2, '>8': 3}
    df['a1cresult_encoded'] = df['a1cresult'].map(a1c_mapping).fillna(0).astype(int)
    
    # 4. Codificar change (No=0, Ch=1)
    df['change_encoded'] = (df['change'] == 'Ch').astype(int)
    
    # 5. Codificar diabetesmed (No=0, Yes=1)
    df['diabetesmed_encoded'] = (df['diabetesmed'] == 'Yes').astype(int)
    
    # 6. Contar medicamentos para diabetes (feature engineering)
    diabetes_med_cols = [
        'metformin', 'repaglinide', 'nateglinide', 'chlorpropamide', 'glimepiride',
        'glipizide', 'glyburide', 'pioglitazone', 'rosiglitazone', 'insulin'
    ]
    
    def count_meds(row):
        count = 0
        for col in diabetes_med_cols:
            if col in row.index:
                val = row[col]
                # Convertir a string para comparación segura
                val_str = str(val) if pd.notna(val) else 'No'
                if val_str not in ['No', 'Steady', 'nan', 'None']:
                    count += 1
        return count
    
    df['num_diabetes_meds'] = df.apply(count_meds, axis=1)
    
    # --- SELECCIÓN DE FEATURES ---
    # Mantener solo columnas relevantes para el modelo
    clean_columns = [
        'encounter_id', 'patient_nbr', 'race', 'gender',
        'age_numeric', 'admission_type_id', 'discharge_disposition_id', 'admission_source_id',
        'time_in_hospital', 'num_lab_procedures', 'num_procedures', 'num_medications',
        'number_outpatient', 'number_emergency', 'number_inpatient', 'number_diagnoses',
        'max_glu_serum_encoded', 'a1cresult_encoded', 'change_encoded', 'diabetesmed_encoded',
        'num_diabetes_meds', 'readmitted', 'split_type'
    ]
    
    df_clean = df[clean_columns].copy()
    
    # Eliminar filas con valores nulos en columnas críticas
    df_clean = df_clean.dropna(subset=[
        'time_in_hospital', 'num_lab_procedures', 'num_medications', 'readmitted'
    ])
    
    # Rellenar otros nulos con 0
    df_clean = df_clean.fillna(0)
    
    print(f"Datos CLEAN procesados: {len(df_clean)} registros")
    print(f"Train: {len(df_clean[df_clean['split_type'] == 'train'])}")
    print(f"Validation: {len(df_clean[df_clean['split_type'] == 'validation'])}")
    print(f"Test: {len(df_clean[df_clean['split_type'] == 'test'])}")
    
    # Guardar en CLEAN DB
    df_clean.to_sql('diabetes_clean', clean_engine, if_exists='replace', index=False)
    
    print("Preprocesamiento completado exitosamente")


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
    'diabetes_preprocessing',
    default_args=default_args,
    description='Preprocesamiento de datos de diabetes (RAW -> CLEAN)',
    schedule_interval=None,  # Trigger manual o por otro DAG
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    tags=['diabetes', 'preprocessing', 'clean-data'],
) as dag:
    
    preprocess_task = PythonOperator(
        task_id='preprocess_data',
        python_callable=preprocess_diabetes_data,
    )
