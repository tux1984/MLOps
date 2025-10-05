"""Airflow DAGs for preprocessing and training models on forest cover data."""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pandas as pd
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text

APP_DB_HOST = os.environ.get("APP_DB_HOST", "db")
APP_DB_PORT = int(os.environ.get("APP_DB_PORT", "5432"))
APP_DB_NAME = os.environ.get("APP_DB_NAME", "appdb")
APP_DB_USER = os.environ.get("APP_DB_USER", "app")
APP_DB_PASSWORD = os.environ.get("APP_DB_PASSWORD", "secret")

CONN_URI = (
    f"postgresql+psycopg2://{APP_DB_USER}:{APP_DB_PASSWORD}@{APP_DB_HOST}:{APP_DB_PORT}/{APP_DB_NAME}"
)

RAW_TABLE = "forest_cover_samples"
PROCESSED_TABLE = "forest_cover_preprocessed"


def _load_dataframe(table_name: str) -> pd.DataFrame:
    engine = create_engine(CONN_URI)
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT to_regclass(:tbl)"),
            {"tbl": f"public.{table_name}"}
        ).scalar()
    if exists is None:
        raise AirflowException(f"Table '{table_name}' not found in database {APP_DB_NAME}")
    return pd.read_sql_table(table_name, CONN_URI)


def _preprocess_forest_data() -> None:
    df = _load_dataframe(RAW_TABLE)
    if df.empty:
        raise AirflowException("No data available in forest_cover_samples to preprocess")

    df = df.dropna().copy()

    categorical_cols: List[str] = [col for col in ["wilderness_area", "soil_type"] if col in df.columns]

    if categorical_cols:
        df = pd.get_dummies(df, columns=categorical_cols, drop_first=False)

    # Drop metadata columns not needed for modelling
    for col in ["id", "ingested_at", "row_hash"]:
        if col in df.columns:
            df = df.drop(columns=col)

    engine = create_engine(CONN_URI)
    df.to_sql(PROCESSED_TABLE, engine, if_exists="replace", index=False)


def _train_forest_models() -> None:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report
    from sklearn.model_selection import GridSearchCV, train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    import joblib

    df = _load_dataframe(PROCESSED_TABLE)
    if df.empty:
        raise AirflowException("Preprocessed table is empty. Run preprocess before training.")

    if "cover_type" not in df.columns:
        raise AirflowException("Column 'cover_type' missing from preprocessed dataset")

    X = df.drop(columns=["cover_type"])
    y = df["cover_type"].astype(int)

    if X.empty:
        raise AirflowException("Feature dataframe is empty after preprocessing")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    models = {
        "logistic_regression": (
            LogisticRegression(max_iter=200, multi_class="multinomial"),
            {"C": [0.1, 1.0, 10.0]}
        ),
        "random_forest": (
            RandomForestClassifier(random_state=42),
            {"n_estimators": [100, 200], "max_depth": [None, 10, 20]}
        ),
        "svc": (
            SVC(probability=True),
            {"C": [0.5, 1.0], "kernel": ["linear", "rbf"]}
        ),
    }

    models_dir = Path("/shared/models/forest")
    models_dir.mkdir(parents=True, exist_ok=True)

    for name, (model, params) in models.items():
        grid = GridSearchCV(model, param_grid=params, cv=3, n_jobs=-1)
        grid.fit(X_train, y_train)

        y_pred = grid.predict(X_test)
        report = classification_report(y_test, y_pred)
        print(f"Model: {name}\nBest params: {grid.best_params_}\n\n{report}")

        artifact = {
            "estimator": grid.best_estimator_,
            "scaler": scaler,
            "feature_names": list(X.columns),
        }
        output_path = models_dir / f"{name}.joblib"
        joblib.dump(artifact, output_path)
        print(f"Saved model artifact to {output_path}")


preprocess_dag = DAG(
    dag_id="forest_preprocess",
    description="Clean and encode forest cover dataset for modelling",
    schedule=timedelta(minutes=5),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["forest", "preprocess"],
)

with preprocess_dag:
    preprocess = PythonOperator(
        task_id="preprocess_forest_data",
        python_callable=_preprocess_forest_data,
    )

train_dag = DAG(
    dag_id="forest_train",
    description="Train classifiers on preprocessed forest cover dataset",
    schedule=timedelta(minutes=15),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["forest", "train"],
)

with train_dag:
    train = PythonOperator(
        task_id="train_forest_models",
        python_callable=_train_forest_models,
    )
