from datetime import datetime, timedelta
import os

from airflow import DAG
from airflow.operators.python import PythonOperator


def _ingest_penguins():
    import pandas as pd  # noqa: F401  (ensures pandas is present)
    import seaborn as sns
    from sqlalchemy import create_engine

    # Load dataset without preprocessing
    df = sns.load_dataset("penguins")

    host = os.getenv("APP_DB_HOST", "db")
    port = int(os.getenv("APP_DB_PORT", "5432"))
    db = os.getenv("APP_DB_NAME", "appdb")
    user = os.getenv("APP_DB_USER", "app")
    password = os.getenv("APP_DB_PASSWORD", "secret")

    engine = create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    )

    # Replace snapshot each run to avoid duplicates
    df.to_sql("penguins", engine, if_exists="replace", index=False)


with DAG(
    dag_id="penguins_ingest",
    description="Carga el dataset seaborn penguins a Postgres",
    schedule=timedelta(seconds=30),  # Nota: sub-minuto depende de configuración del scheduler
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["ingest", "penguins"],
):
    ingest = PythonOperator(
        task_id="ingest_penguins",
        python_callable=_ingest_penguins,
    )

