"""Airflow DAG for preprocessing and training models on forest cover data with MLflow."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import mlflow
from mlflow.models.signature import infer_signature
from mlflow.exceptions import RestException
import pandas as pd
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator, get_current_context
from mlflow.tracking import MlflowClient
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
MLFLOW_EXPERIMENT_NAME = os.environ.get("MLFLOW_EXPERIMENT_NAME", "forest-cover-experiment")
MLFLOW_MODEL_NAME = os.environ.get("MLFLOW_MODEL_NAME", "forest-cover-classifier")
SHARED_DIR = Path(os.environ.get("SHARED_DIR", "/shared"))
TARGET_COLUMN = "cover_type"
NUMERIC_FEATURES = [
    "elevation",
    "aspect",
    "slope",
    "horizontal_distance_to_hydrology",
    "vertical_distance_to_hydrology",
    "horizontal_distance_to_roadways",
    "hillshade_9am",
    "hillshade_noon",
    "hillshade_3pm",
    "horizontal_distance_to_fire_points",
]
CATEGORICAL_FEATURES = ["wilderness_area", "soil_type"]


def _persist_model_state(state: Dict[str, Any]) -> None:
    models_dir = SHARED_DIR / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    path = models_dir / "latest_model.json"
    with path.open("w", encoding="utf-8") as fp:
        json.dump(state, fp, indent=2)



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
    summary: Dict[str, int] = {
        "feature_columns": 0,
        "row_count": 0,
    }

    df = _load_dataframe(RAW_TABLE)
    if df.empty:
        raise AirflowException("No data available in forest_cover_samples to preprocess")

    if TARGET_COLUMN not in df.columns:
        raise AirflowException(f"Target column '{TARGET_COLUMN}' missing in source dataset")

    df = df.drop_duplicates().copy()
    df = df[df[TARGET_COLUMN].notna()]
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)

    for column in NUMERIC_FEATURES:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        else:
            df[column] = pd.NA

    for column in CATEGORICAL_FEATURES:
        if column in df.columns:
            df[column] = df[column].astype(str).str.lower()
        else:
            df[column] = ""

    drop_columns = {"id", "ingested_at", "row_hash", "group_number", "batch_number"}
    existing_drop = [col for col in drop_columns if col in df.columns]
    df = df.drop(columns=existing_drop)

    feature_columns = [col for col in df.columns if col != TARGET_COLUMN]
    if not feature_columns:
        raise AirflowException("No feature columns available after preprocessing")

    engine = create_engine(CONN_URI)
    df.to_sql(PROCESSED_TABLE, engine, if_exists="replace", index=False)

    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    parquet_path = SHARED_DIR / f"forest_cover_preprocessed_{timestamp}.parquet"
    df.to_parquet(parquet_path, index=False)

    summary["feature_columns"] = len(feature_columns)
    summary["row_count"] = len(df)

    ti = get_current_context()["ti"]
    ti.xcom_push(key="preprocessed_parquet", value=str(parquet_path))
    ti.xcom_push(key="preprocess_summary", value=summary)


def _train_forest_models() -> None:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        f1_score,
        precision_score,
        recall_score,
    )
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.model_selection import GridSearchCV, train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.svm import SVC

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI"))
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    df = _load_dataframe(PROCESSED_TABLE)
    if df.empty:
        raise AirflowException("Preprocessed table is empty. Run preprocess before training.")

    if "cover_type" not in df.columns:
        raise AirflowException("Column 'cover_type' missing from preprocessed dataset")

    X = df.drop(columns=["cover_type"])
    y = df["cover_type"].astype(int)

    if X.empty:
        raise AirflowException("Feature dataframe is empty after preprocessing")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    def _build_preprocessor() -> ColumnTransformer:
        numeric_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )

        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]
        )

        return ColumnTransformer(
            transformers=[
                ("numeric", numeric_transformer, NUMERIC_FEATURES),
                ("categorical", categorical_transformer, CATEGORICAL_FEATURES),
            ]
        )

    models = {
        "logistic_regression": (
            Pipeline(
                steps=[
                    ("preprocessor", _build_preprocessor()),
                    (
                        "model",
                        LogisticRegression(
                            max_iter=300,
                            multi_class="multinomial",
                        ),
                    ),
                ]
            ),
            {"model__C": [0.5, 1.0]},
        ),
        "random_forest": (
            Pipeline(
                steps=[
                    ("preprocessor", _build_preprocessor()),
                    (
                        "model",
                        RandomForestClassifier(
                            random_state=42,
                            n_estimators=120,
                            max_depth=15,
                        ),
                    ),
                ]
            ),
            {"model__n_estimators": [120], "model__max_depth": [15]},
        ),
        "svc": (
            Pipeline(
                steps=[
                    ("preprocessor", _build_preprocessor()),
                    (
                        "model",
                        SVC(
                            probability=True,
                            kernel="rbf",
                            C=1.0,
                            gamma="scale",
                            max_iter=300,
                        ),
                    ),
                ]
            ),
            {"model__C": [1.0]},
        ),
    }

    results: List[Dict[str, float]] = []
    client = MlflowClient()

    preprocess_context = get_current_context()["ti"].xcom_pull(
        key="preprocess_summary", task_ids="preprocess_forest_data"
    ) or {}

    for name, (pipeline, params) in models.items():
        grid = GridSearchCV(
            pipeline,
            param_grid=params,
            cv=2,
            n_jobs=1,
            scoring="f1_macro",
        )
        grid.fit(X_train, y_train)

        y_pred = grid.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        f1_macro = f1_score(y_test, y_pred, average="macro")
        precision_macro = precision_score(y_test, y_pred, average="macro")
        recall_macro = recall_score(y_test, y_pred, average="macro")

        report_dict = classification_report(y_test, y_pred, output_dict=True)

        with mlflow.start_run(run_name=f"{name}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}") as run:
            best_params = {k.replace("model__", ""): v for k, v in grid.best_params_.items()}
            mlflow.log_params(best_params)
            mlflow.log_metrics(
                {
                    "accuracy": accuracy,
                    "f1_macro": f1_macro,
                    "precision_macro": precision_macro,
                    "recall_macro": recall_macro,
                    "train_rows": len(X_train),
                    "test_rows": len(X_test),
                }
            )

            if preprocess_context:
                mlflow.log_dict(preprocess_context, "data/preprocess_summary.json")

            mlflow.log_dict(report_dict, f"metrics/{name}_classification_report.json")

            # Fit the best estimator on the full dataset before logging to MLflow
            best_pipeline = grid.best_estimator_
            best_pipeline.fit(X, y)

            signature = infer_signature(X, best_pipeline.predict(X))
            mlflow.sklearn.log_model(
                best_pipeline,
                artifact_path="model",
                signature=signature,
                input_example=X.head(5),
            )

            feature_metadata = {
                "feature_names": list(X.columns),
                "target_name": "cover_type",
                "trained_at": datetime.utcnow().isoformat(),
            }
            mlflow.log_dict(feature_metadata, "model/feature_metadata.json")

            results.append(
                {
                    "name": name,
                    "run_id": run.info.run_id,
                    "f1_macro": f1_macro,
                    "accuracy": accuracy,
                    "precision_macro": precision_macro,
                    "recall_macro": recall_macro,
                    "feature_metadata": feature_metadata,
                }
            )

    if not results:
        raise AirflowException("No models were trained")

    best_model = max(results, key=lambda item: item["f1_macro"])
    run_id = best_model["run_id"]
    model_uri = f"runs:/{run_id}/model"

    ti = get_current_context()["ti"]

    state = {
        "run_id": run_id,
        "model_uri": model_uri,
        "metrics": best_model,
        "feature_metadata": best_model.get("feature_metadata", {}),
        "updated_at": datetime.utcnow().isoformat(),
    }

    registry_enabled = os.environ.get("MLFLOW_ENABLE_MODEL_REGISTRY", "false").lower() == "true"

    if not registry_enabled:
        state["registry_status"] = "disabled"
        _persist_model_state(state)
        ti.xcom_push(key="best_model", value=best_model)
        ti.xcom_push(key="registered_model_version", value=run_id)
        return

    try:
        client.create_registered_model(MLFLOW_MODEL_NAME)
    except RestException as exc:
        if getattr(exc, "error_code", None) != "RESOURCE_ALREADY_EXISTS":
            state["registry_status"] = "error"
            state["error"] = str(exc)
            _persist_model_state(state)
            ti.xcom_push(key="best_model", value=best_model)
            ti.xcom_push(key="registered_model_version", value="registry-error")
            ti.xcom_push(key="registry_error", value=str(exc))
            return

    try:
        registered_version = client.create_model_version(
            name=MLFLOW_MODEL_NAME,
            source=model_uri,
            run_id=run_id,
        )
    except RestException as exc:
        state["registry_status"] = "error"
        state["error"] = str(exc)
        _persist_model_state(state)
        ti.xcom_push(key="best_model", value=best_model)
        ti.xcom_push(key="registered_model_version", value="registry-error")
        ti.xcom_push(key="registry_error", value=str(exc))
        return

    version_number = registered_version.version

    for _ in range(30):
        model_version = client.get_model_version(
            name=MLFLOW_MODEL_NAME,
            version=version_number,
        )
        if model_version.status == "READY":
            break
        time.sleep(2)
    else:
        raise AirflowException(
            f"Model version {version_number} for {MLFLOW_MODEL_NAME} did not become READY"
        )

    client.transition_model_version_stage(
        name=MLFLOW_MODEL_NAME,
        version=version_number,
        stage="Production",
        archive_existing_versions=True,
    )

    state["registry_status"] = "synced"
    state["registered_version"] = version_number
    state["model_stage"] = "Production"
    _persist_model_state(state)

    ti.xcom_push(key="best_model", value=best_model)
    ti.xcom_push(key="registered_model_version", value=version_number)


with DAG(
    dag_id="forest_training_pipeline",
    description=(
        "Preprocess forest cover samples, train multiple models and register the best one in MLflow"
    ),
    schedule=timedelta(minutes=15),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["forest", "training", "mlflow"],
) as training_dag:
    preprocess = PythonOperator(
        task_id="preprocess_forest_data",
        python_callable=_preprocess_forest_data,
    )

    train = PythonOperator(
        task_id="train_forest_models",
        python_callable=_train_forest_models,
    )

    preprocess >> train
