"""
Módulo de utilidades para preprocessing

Funciones para:
- Limpieza de datos
- Encoding de variables categóricas
- Normalización de features numéricas
- Feature engineering
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from sklearn.preprocessing import StandardScaler, LabelEncoder


def handle_missing_values(
    df: pd.DataFrame,
    strategy: Dict[str, str] = None
) -> pd.DataFrame:
    """
    Maneja valores faltantes según estrategia
    
    Args:
        df: DataFrame con valores faltantes
        strategy: Diccionario {columna: 'mean'|'median'|'mode'|'drop'|valor}
    
    Returns:
        pd.DataFrame: DataFrame sin valores faltantes
    """
    df_clean = df.copy()
    
    # Reemplazar '?' con NaN
    df_clean = df_clean.replace('?', np.nan)
    df_clean = df_clean.replace('Unknown', np.nan)
    
    if strategy is None:
        # Estrategia por defecto: median para numéricos, mode para categóricos
        for col in df_clean.columns:
            if df_clean[col].isna().sum() > 0:
                if df_clean[col].dtype in ['int64', 'float64']:
                    df_clean[col].fillna(df_clean[col].median(), inplace=True)
                else:
                    df_clean[col].fillna(df_clean[col].mode()[0] if len(df_clean[col].mode()) > 0 else 'Unknown', inplace=True)
    else:
        for col, strat in strategy.items():
            if col in df_clean.columns:
                if strat == 'mean':
                    df_clean[col].fillna(df_clean[col].mean(), inplace=True)
                elif strat == 'median':
                    df_clean[col].fillna(df_clean[col].median(), inplace=True)
                elif strat == 'mode':
                    df_clean[col].fillna(df_clean[col].mode()[0], inplace=True)
                elif strat == 'drop':
                    df_clean = df_clean.dropna(subset=[col])
                else:
                    df_clean[col].fillna(strat, inplace=True)
    
    print(f"✓ Valores faltantes procesados: {df.isna().sum().sum()} → {df_clean.isna().sum().sum()}")
    return df_clean


def encode_categorical_features(
    df: pd.DataFrame,
    columns: List[str],
    method: str = 'label'
) -> Tuple[pd.DataFrame, Dict]:
    """
    Codifica variables categóricas
    
    Args:
        df: DataFrame con variables categóricas
        columns: Lista de columnas a codificar
        method: 'label' o 'onehot'
    
    Returns:
        tuple: (df_encoded, encoders_dict)
    """
    df_encoded = df.copy()
    encoders = {}
    
    if method == 'label':
        for col in columns:
            if col in df_encoded.columns:
                le = LabelEncoder()
                df_encoded[f'{col}_encoded'] = le.fit_transform(df_encoded[col].astype(str))
                encoders[col] = le
                print(f"  - {col}: {len(le.classes_)} categorías")
    
    elif method == 'onehot':
        df_encoded = pd.get_dummies(df_encoded, columns=columns, prefix=columns, drop_first=True)
        encoders['method'] = 'onehot'
        encoders['columns'] = columns
    
    print(f"✓ Codificadas {len(columns)} variables categóricas ({method})")
    return df_encoded, encoders


def normalize_numerical_features(
    df: pd.DataFrame,
    columns: List[str],
    scaler: Optional[StandardScaler] = None
) -> Tuple[pd.DataFrame, StandardScaler]:
    """
    Normaliza features numéricas con StandardScaler
    
    Args:
        df: DataFrame con features numéricas
        columns: Lista de columnas a normalizar
        scaler: Scaler pre-entrenado (para validation/test)
    
    Returns:
        tuple: (df_normalized, scaler)
    """
    df_norm = df.copy()
    
    if scaler is None:
        scaler = StandardScaler()
        df_norm[columns] = scaler.fit_transform(df[columns])
        print(f"✓ Scaler entrenado en {len(columns)} columnas")
    else:
        df_norm[columns] = scaler.transform(df[columns])
        print(f"✓ Scaler aplicado a {len(columns)} columnas")
    
    return df_norm, scaler


def extract_age_numeric(age_range: str) -> int:
    """
    Convierte rangos de edad a valor numérico
    
    Args:
        age_range: Rango de edad (ej: "[50-60)")
    
    Returns:
        int: Edad promedio del rango
    """
    if pd.isna(age_range) or age_range == '?' or age_range == 'Unknown':
        return 50
    
    age_range = str(age_range).replace('[', '').replace(')', '').replace(']', '')
    
    if '-' in age_range:
        parts = age_range.split('-')
        try:
            return (int(parts[0]) + int(parts[1])) // 2
        except:
            return 50
    
    return 50


def encode_lab_results(df: pd.DataFrame) -> pd.DataFrame:
    """
    Codifica resultados de laboratorio (max_glu_serum, a1cresult)
    
    Args:
        df: DataFrame con columnas de laboratorio
    
    Returns:
        pd.DataFrame: DataFrame con columnas codificadas
    """
    df_encoded = df.copy()
    
    # max_glu_serum: None=0, Norm=1, >200=2, >300=3
    glu_mapping = {'None': 0, 'Norm': 1, '>200': 2, '>300': 3}
    df_encoded['max_glu_serum_encoded'] = df_encoded['max_glu_serum'].map(glu_mapping).fillna(0).astype(int)
    
    # a1cresult: None=0, Norm=1, >7=2, >8=3
    a1c_mapping = {'None': 0, 'Norm': 1, '>7': 2, '>8': 3}
    df_encoded['a1cresult_encoded'] = df_encoded['a1cresult'].map(a1c_mapping).fillna(0).astype(int)
    
    print(f"✓ Resultados de laboratorio codificados")
    return df_encoded


def count_diabetes_medications(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cuenta número de medicamentos para diabetes prescritos
    
    Args:
        df: DataFrame con columnas de medicamentos
    
    Returns:
        pd.DataFrame: DataFrame con columna num_diabetes_meds
    """
    df_meds = df.copy()
    
    # Lista de medicamentos para diabetes
    med_columns = [
        'metformin', 'repaglinide', 'nateglinide', 'chlorpropamide', 
        'glimepiride', 'acetohexamide', 'glipizide', 'glyburide', 
        'tolbutamide', 'pioglitazone', 'rosiglitazone', 'acarbose',
        'miglitol', 'troglitazone', 'tolazamide', 'insulin',
        'glyburide_metformin', 'glipizide_metformin', 
        'glimepiride_pioglitazone', 'metformin_rosiglitazone', 
        'metformin_pioglitazone'
    ]
    
    def count_meds(row):
        count = 0
        for col in med_columns:
            if col in row.index:
                val = str(row[col]) if pd.notna(row[col]) else 'No'
                # Contar si hay cambio en medicamento (Up, Down, Steady)
                if val not in ['No', 'nan', 'None', '?']:
                    count += 1
        return count
    
    df_meds['num_diabetes_meds'] = df_meds.apply(count_meds, axis=1)
    
    print(f"✓ Feature engineering: num_diabetes_meds creado")
    return df_meds


def encode_binary_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Codifica features binarias (change, diabetesmed)
    
    Args:
        df: DataFrame con features binarias
    
    Returns:
        pd.DataFrame: DataFrame con features codificadas
    """
    df_binary = df.copy()
    
    # change: No=0, Ch=1
    df_binary['change_encoded'] = (df_binary['change'] == 'Ch').astype(int)
    
    # diabetesmed: No=0, Yes=1
    df_binary['diabetesmed_encoded'] = (df_binary['diabetesmed'] == 'Yes').astype(int)
    
    print(f"✓ Features binarias codificadas")
    return df_binary


def encode_gender(df: pd.DataFrame) -> pd.DataFrame:
    """
    Codifica género (Male=1, Female=0)
    
    Args:
        df: DataFrame con columna gender
    
    Returns:
        pd.DataFrame: DataFrame con gender_encoded
    """
    df_gender = df.copy()
    gender_mapping = {'Male': 1, 'Female': 0, 'Unknown/Invalid': 0}
    df_gender['gender_encoded'] = df_gender['gender'].map(gender_mapping).fillna(0).astype(int)
    
    print(f"✓ Género codificado")
    return df_gender


def encode_race(df: pd.DataFrame) -> pd.DataFrame:
    """
    Codifica raza con LabelEncoder
    
    Args:
        df: DataFrame con columna race
    
    Returns:
        pd.DataFrame: DataFrame con race_encoded
    """
    df_race = df.copy()
    
    # Reemplazar valores desconocidos
    df_race['race'] = df_race['race'].fillna('Unknown')
    
    le = LabelEncoder()
    df_race['race_encoded'] = le.fit_transform(df_race['race'].astype(str))
    
    print(f"✓ Raza codificada: {len(le.classes_)} categorías")
    return df_race


def encode_readmitted_target(df: pd.DataFrame) -> pd.DataFrame:
    """
    Codifica variable objetivo readmitted
    NO = 0, <30 = 1, >30 = 1 (problema binario: readmitido o no)
    
    Args:
        df: DataFrame con columna readmitted
    
    Returns:
        pd.DataFrame: DataFrame con readmitted como 0/1
    """
    df_target = df.copy()
    
    # Convertir a binario: NO=0, cualquier readmisión=1
    df_target['readmitted'] = df_target['readmitted'].apply(
        lambda x: 0 if x == 'NO' else 1
    ).astype(int)
    
    print(f"✓ Target codificado (binario)")
    return df_target


def select_features_for_model(df: pd.DataFrame) -> pd.DataFrame:
    """
    Selecciona features finales para el modelo
    
    Args:
        df: DataFrame preprocesado
    
    Returns:
        pd.DataFrame: DataFrame con features seleccionadas
    """
    # Features finales a mantener
    selected_features = [
        'encounter_id',
        'patient_nbr',
        'race_encoded',
        'gender_encoded',
        'age_encoded',
        'admission_type_id',
        'discharge_disposition_id',
        'admission_source_id',
        'time_in_hospital',
        'num_lab_procedures',
        'num_procedures',
        'num_medications',
        'number_outpatient',
        'number_emergency',
        'number_inpatient',
        'number_diagnoses',
        'max_glu_serum_encoded',
        'a1cresult_encoded',
        'num_diabetes_meds',
        'change_encoded',
        'diabetesmed_encoded',
        'readmitted'
    ]
    
    # Verificar que existan todas las columnas
    available = [col for col in selected_features if col in df.columns]
    missing = [col for col in selected_features if col not in df.columns]
    
    if missing:
        print(f"⚠ Columnas faltantes: {missing}")
    
    df_selected = df[available].copy()
    print(f"✓ Seleccionadas {len(available)} features para el modelo")
    
    return df_selected


def full_preprocessing_pipeline(
    df: pd.DataFrame,
    is_training: bool = True,
    scaler: Optional[StandardScaler] = None
) -> Tuple[pd.DataFrame, Optional[StandardScaler]]:
    """
    Pipeline completo de preprocessing
    
    Args:
        df: DataFrame raw
        is_training: Si True, entrena encoders/scalers
        scaler: Scaler pre-entrenado (para validation/test)
    
    Returns:
        tuple: (df_clean, scaler)
    """
    print("=" * 50)
    print("INICIANDO PREPROCESSING PIPELINE")
    print("=" * 50)
    
    # 1. Limpieza de valores faltantes
    df_clean = handle_missing_values(df)
    
    # 2. Extraer edad numérica
    df_clean['age_encoded'] = df_clean['age'].apply(extract_age_numeric)
    
    # 3. Codificar resultados de laboratorio
    df_clean = encode_lab_results(df_clean)
    
    # 4. Contar medicamentos diabetes
    df_clean = count_diabetes_medications(df_clean)
    
    # 5. Codificar features binarias
    df_clean = encode_binary_features(df_clean)
    
    # 6. Codificar género
    df_clean = encode_gender(df_clean)
    
    # 7. Codificar raza
    df_clean = encode_race(df_clean)
    
    # 8. Codificar target
    df_clean = encode_readmitted_target(df_clean)
    
    # 9. Seleccionar features finales
    df_final = select_features_for_model(df_clean)
    
    # 10. Normalizar features numéricas (opcional, comentado por ahora)
    # numerical_cols = [
    #     'time_in_hospital', 'num_lab_procedures', 'num_procedures',
    #     'num_medications', 'number_outpatient', 'number_emergency',
    #     'number_inpatient', 'number_diagnoses'
    # ]
    # df_final, scaler = normalize_numerical_features(df_final, numerical_cols, scaler)
    
    print("=" * 50)
    print(f"PREPROCESSING COMPLETADO: {len(df_final)} registros")
    print("=" * 50)
    
    return df_final, scaler
