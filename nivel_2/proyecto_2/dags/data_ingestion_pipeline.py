"""Airflow DAG to collect forest cover samples directly from external API."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pendulum
import requests
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator, get_current_context
from sqlalchemy import create_engine, text

APP_DB_HOST = os.environ.get("APP_DB_HOST", "db")
APP_DB_PORT = os.environ.get("APP_DB_PORT", "5432")
APP_DB_NAME = os.environ.get("APP_DB_NAME", "appdb")
APP_DB_USER = os.environ.get("APP_DB_USER", "app")
APP_DB_PASSWORD = os.environ.get("APP_DB_PASSWORD", "secret")
SOURCE_API_BASE_URL = os.environ.get("SOURCE_API_BASE_URL", "http://10.43.100.103:8080")
GROUP_NUMBER = int(os.environ.get("GROUP_NUMBER", "8"))
SHARED_DIR = Path(os.environ.get("SHARED_DIR", "/shared"))


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS forest_cover_samples (
    id SERIAL PRIMARY KEY,
    group_number INTEGER NOT NULL,
    batch_number INTEGER NOT NULL,
    elevation INTEGER,
    aspect INTEGER,
    slope INTEGER,
    horizontal_distance_to_hydrology INTEGER,
    vertical_distance_to_hydrology INTEGER,
    horizontal_distance_to_roadways INTEGER,
    hillshade_9am INTEGER,
    hillshade_noon INTEGER,
    hillshade_3pm INTEGER,
    horizontal_distance_to_fire_points INTEGER,
    wilderness_area TEXT,
    soil_type TEXT,
    cover_type INTEGER,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_hash TEXT UNIQUE
);
"""

CREATE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_forest_cover_samples_row_hash
    ON forest_cover_samples (row_hash);
"""


INDEX_EXISTS_SQL = """
SELECT 1
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname = 'uq_forest_cover_samples_row_hash'
LIMIT 1;
"""

TABLE_EXISTS_SQL = """
SELECT to_regclass('public.forest_cover_samples');
"""

CONN_TEMPLATE = "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

COLUMN_NAMES = [
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
    "wilderness_area",
    "soil_type",
    "cover_type",
]

NUMERIC_COLUMNS = {
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
    "cover_type",
}




def _ensure_schema(connection) -> None:
    """Create table and unique index if they do not exist."""
    table_exists = connection.execute(text(TABLE_EXISTS_SQL)).scalar()
    if table_exists is None:
        connection.execute(text(CREATE_TABLE_SQL))
    index_exists = connection.execute(text(INDEX_EXISTS_SQL)).scalar()
    if not index_exists:
        connection.execute(text(CREATE_INDEX_SQL))

def _fetch_external_data() -> str:
    """Call external API and persist payload into shared storage."""
    context = get_current_context()
    url = f"{SOURCE_API_BASE_URL.rstrip('/')}/data"
    params = {"group_number": GROUP_NUMBER}

    try:
        response = requests.get(
            url,
            params=params,
            timeout=(10, 40),
            headers={"Accept": "application/json", "Connection": "close"},
        )
    except requests.exceptions.RequestException as exc:
        raise AirflowException(f"Error connecting to Data API: {exc}") from exc

    if response.status_code == 400:
        raise AirflowException(
            f"API returned 400 for group {GROUP_NUMBER}. Details: {response.text}"
        )

    response.raise_for_status()
    payload: Dict[str, Any] = response.json()

    batch_number = payload.get("batch_number")
    if batch_number is None:
        raise AirflowException("batch_number missing from API payload")

    rows = payload.get("data", [])
    if not rows:
        raise AirflowException("API returned empty dataset")

    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"group{GROUP_NUMBER}_batch{batch_number}_{timestamp}.json"
    payload_path = SHARED_DIR / filename

    with payload_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    ti = context["ti"]
    ti.xcom_push(key="payload_path", value=str(payload_path))
    ti.xcom_push(key="batch_number", value=batch_number)
    ti.xcom_push(key="row_count", value=len(rows))
    return str(payload_path)




def _load_into_postgres() -> int:
    """Load the previously fetched payload into the application database."""
    context = get_current_context()
    ti = context["ti"]
    payload_path = ti.xcom_pull(key="payload_path", task_ids="fetch_data")
    if not payload_path:
        raise AirflowException("No payload path found in XCom")

    path = Path(payload_path)
    if not path.exists():
        raise AirflowException(f"Payload file not found: {payload_path}")

    with path.open("r", encoding="utf-8") as fh:
        payload: Dict[str, Any] = json.load(fh)

    rows: List[List[Any]] = payload.get("data", [])
    batch_number = payload.get("batch_number")
    if not rows:
        raise AirflowException("Payload did not contain data rows")

    df = pd.DataFrame(rows, columns=COLUMN_NAMES)
    df.drop_duplicates(subset=COLUMN_NAMES, inplace=True)

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["group_number"] = GROUP_NUMBER
    df["batch_number"] = batch_number
    df["ingested_at"] = datetime.utcnow()

    def _compute_hash(row: pd.Series) -> str:
        parts = ["" if pd.isna(row[col]) else str(row[col]) for col in COLUMN_NAMES]
        parts.append(str(GROUP_NUMBER))
        parts.append(str(batch_number))
        signature = "|".join(parts)
        return hashlib.md5(signature.encode("utf-8")).hexdigest()

    df["row_hash"] = df.apply(_compute_hash, axis=1)
    df.drop_duplicates(subset="row_hash", inplace=True)

    csv_latest = SHARED_DIR / "forest_cover_latest.csv"
    df.to_csv(csv_latest, index=False)
    ti.xcom_push(key="csv_path", value=str(csv_latest))
    ti.xcom_push(key="dedup_rows", value=len(df))

    engine = create_engine(
        CONN_TEMPLATE.format(
            user=APP_DB_USER,
            password=APP_DB_PASSWORD,
            host=APP_DB_HOST,
            port=APP_DB_PORT,
            db=APP_DB_NAME,
        )
    )

    hashes = df["row_hash"].tolist()
    records: List[Dict[str, Any]] = df.to_dict(orient="records")

    insert_stmt = text(
        """
        INSERT INTO forest_cover_samples (
            group_number,
            batch_number,
            elevation,
            aspect,
            slope,
            horizontal_distance_to_hydrology,
            vertical_distance_to_hydrology,
            horizontal_distance_to_roadways,
            hillshade_9am,
            hillshade_noon,
            hillshade_3pm,
            horizontal_distance_to_fire_points,
            wilderness_area,
            soil_type,
            cover_type,
            ingested_at,
            row_hash
        ) VALUES (
            :group_number,
            :batch_number,
            :elevation,
            :aspect,
            :slope,
            :horizontal_distance_to_hydrology,
            :vertical_distance_to_hydrology,
            :horizontal_distance_to_roadways,
            :hillshade_9am,
            :hillshade_noon,
            :hillshade_3pm,
            :horizontal_distance_to_fire_points,
            :wilderness_area,
            :soil_type,
            :cover_type,
            :ingested_at,
            :row_hash
        )
        """
    )

    with engine.begin() as conn:
        _ensure_schema(conn)

        existing_hashes = set()
        if hashes:
            existing_hashes = set(
                conn.execute(
                    text("SELECT row_hash FROM forest_cover_samples WHERE row_hash = ANY(:hashes)"),
                    {"hashes": hashes},
                ).scalars()
            )

        new_records = [record for record in records if record["row_hash"] not in existing_hashes]

        if new_records:
            conn.execute(insert_stmt, new_records)

    inserted = len(new_records)
    ti.xcom_push(key="inserted_rows", value=inserted)
    ti.xcom_push(key="skipped_existing", value=len(records) - inserted)
    return inserted


def _log_summary() -> None:
    context = get_current_context()
    ti = context["ti"]
    batch_number = ti.xcom_pull(key="batch_number", task_ids="fetch_data")
    row_count = ti.xcom_pull(key="row_count", task_ids="fetch_data")
    dedup_rows = ti.xcom_pull(key="dedup_rows", task_ids="load_postgres")
    inserted = ti.xcom_pull(key="inserted_rows", task_ids="load_postgres")
    skipped = ti.xcom_pull(key="skipped_existing", task_ids="load_postgres")
    csv_path = ti.xcom_pull(key="csv_path", task_ids="load_postgres")

    log_message = (
        f"Batch {batch_number} for group {GROUP_NUMBER}: "
        f"fetched {row_count} rows, deduplicated to {dedup_rows}, "
        f"inserted {inserted} new rows (skipped {skipped}). Latest CSV at {csv_path}."
    )
    print(log_message)


with DAG(
    dag_id="forest_cover_data_pipeline",
    schedule_interval="*/5 * * * *",  # cada 5 minutos
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    default_args={"owner": "mlops", "retries": 0},
    tags=["ingestion", "forest-cover"],
) as dag:
    fetch_data = PythonOperator(
        task_id="fetch_data",
        python_callable=_fetch_external_data,
    )

    load_postgres = PythonOperator(
        task_id="load_postgres",
        python_callable=_load_into_postgres,
    )

    log_summary = PythonOperator(
        task_id="log_summary",
        python_callable=_log_summary,
    )

    fetch_data >> load_postgres >> log_summary
