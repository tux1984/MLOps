from datetime import datetime, timedelta
import os

from airflow import DAG
from airflow.operators.python import PythonOperator


def _preprocess_penguins():
    import pandas as pd
    from sqlalchemy import create_engine

    host = os.getenv("APP_DB_HOST", "db")
    port = int(os.getenv("APP_DB_PORT", "5432"))
    db = os.getenv("APP_DB_NAME", "appdb")
    user = os.getenv("APP_DB_USER", "app")
    password = os.getenv("APP_DB_PASSWORD", "secret")

    engine = create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    )

    # Lee datos crudos
    df = pd.read_sql("penguins", con=engine)

    # Preprocesamiento mínimo para entrenamiento: eliminar nulos y codificar categóricas
    df = df.dropna()

    # Seaborn penguins: columnas categóricas comunes
    cat_cols = [c for c in ["species", "island", "sex"] if c in df.columns]
    df_proc = pd.get_dummies(df, columns=cat_cols, drop_first=False)

    # Guarda snapshot limpio en una nueva tabla
    df_proc.to_sql("penguins_preprocessed", engine, if_exists="replace", index=False)


with DAG(
    dag_id="penguins_preprocess",
    description="Lee penguins de Postgres, limpia y guarda tabla para entrenamiento",
    schedule=timedelta(minutes=1),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["preprocess", "penguins"],
):
    preprocess = PythonOperator(
        task_id="preprocess_penguins",
        python_callable=_preprocess_penguins,
    )

