import pandas as pd
from typing import List

def preprocess_like_training(df_raw: pd.DataFrame, expected_cols: List[str]) -> pd.DataFrame:
    """
    Repite el preprocesamiento del entrenamiento:
      - one-hot en 'island' y 'sex' con drop_first=True
      - reindex al orden/columnas que el modelo espera (expected_cols)
    """
    df = df_raw.copy()

    # get_dummies como en training
    cat_cols = [c for c in ["island", "sex"] if c in df.columns]
    if cat_cols:
        df = pd.get_dummies(df, columns=cat_cols, drop_first=True)

    # Reindex para coincidir exactamente con lo que vio el modelo
    X = df.reindex(columns=expected_cols, fill_value=0)
    return X
