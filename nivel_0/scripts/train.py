"""
Entrena un clasificador de especies de pingüinos usando el dataset palmerpenguins.

Dos categorías principales:
1) Preparación de datos: Cargar -> Limpiar -> Transformar -> Validar -> Ingeniería de características -> Dividir
2) Creación del modelo: Construir -> Entrenar -> Validar

Salida:
    artifacts/model.joblib  (pipeline de sklearn + metadatos + métricas)
"""

from __future__ import annotations
import os
import joblib
import pandas as pd
from typing import Tuple

RANDOM_STATE = 42
OUT_PATH = os.getenv("MODEL_PATH", "artifacts/model.joblib")

# --------------------------- Preparación de datos ---------------------------

def load_data() -> pd.DataFrame:
    """Carga: descarga el dataset de palmerpenguins."""
    from palmerpenguins import load_penguins
    df = load_penguins()
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Limpieza: quita filas con nulos en columnas clave y reindexa,
    y selecciona las columnas que se usarán en el modelo."""
    cols = [
        "species", "island",
        "bill_length_mm", "bill_depth_mm",
        "flipper_length_mm", "body_mass_g",
        "sex",
    ]
    
    # Si 'year' está presente, la eliminamos (no describe al pingüino sino al contexto de la medición.)
    if "year" in df.columns:
        df = df.drop(columns=["year"])

    # Filtramos solo las columnas necesarias (en caso de que haya otras extras)
    df = df[[c for c in cols if c in df.columns]]
    
    return df[cols].dropna().reset_index(drop=True)


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Transformación: normaliza strings/categorías básicas."""
    df = df.copy()
    df["sex"] = df["sex"].str.lower()
    df["island"] = df["island"].astype(str)
    return df


def validate(df: pd.DataFrame) -> None:
    """Validación: checks simples de dominio."""
    assert (df["bill_length_mm"] > 0).all(), "bill_length_mm must be > 0"
    assert (df["bill_depth_mm"] > 0).all(), "bill_depth_mm must be > 0"
    assert (df["flipper_length_mm"] > 0).all(), "flipper_length_mm must be > 0"
    assert (df["body_mass_g"] > 0).all(), "body_mass_g must be > 0"
    assert set(df["sex"].unique()) <= {"male", "female"}, "sex must be male/female"


def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """Ingeniería de características: nuevas variables simples y robustas."""
    df = df.copy()
    df["bill_ratio"] = df["bill_length_mm"] / df["bill_depth_mm"]
    return df


def split(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """División: train/test estratificado."""
    from sklearn.model_selection import train_test_split

    X = df.drop(columns=["species"])
    y = df["species"]
    return train_test_split(
        X, y, test_size=0.3, stratify=y, random_state=RANDOM_STATE
    )


# ----------------------------- Creación del modelo ---------------------------

def build_pipeline():
    """Construcción: preprocesamiento + clasificador."""
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LogisticRegression

    num = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g", "bill_ratio"]
    cat = ["island", "sex"]

    preprocess = ColumnTransformer(
        transformers=[
            ("num", Pipeline(steps=[("sc", StandardScaler())]), num),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
        ]
    )

    clf = LogisticRegression(max_iter=1000)
    return Pipeline(steps=[("prep", preprocess), ("clf", clf)])


def train_and_validate(pipeline, X_train, y_train, X_test, y_test):
    """Entrenamiento + Validación."""
    from sklearn.metrics import accuracy_score, classification_report

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    return pipeline, {"accuracy": acc, "classification_report": report}


def main():
    # Preparación de datos
    df = load_data()
    df = clean(df)
    df = transform(df)
    validate(df)
    df = feature_engineering(df)
    X_train, X_test, y_train, y_test = split(df)

    # Creación del modelo
    pipe = build_pipeline()
    pipe, metrics = train_and_validate(pipe, X_train, y_train, X_test, y_test)

    # Persistencia
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipe,
            "target_names": sorted(df["species"].unique()),
            "metrics": metrics,
        },
        OUT_PATH,
    )
    print(f"[OK] Modelo guardado en {OUT_PATH} | accuracy={metrics['accuracy']:.3f}")


if __name__ == "__main__":
    main()
