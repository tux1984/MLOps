from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import List

import mlflow
import pandas as pd
from fastapi import FastAPI, HTTPException
from mlflow.tracking import MlflowClient
from pydantic import BaseModel, Field

MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "forest-cover-classifier")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
MLFLOW_S3_ENDPOINT_URL = os.getenv("MLFLOW_S3_ENDPOINT_URL")
REGISTRY_ENABLED = os.getenv("MLFLOW_ENABLE_MODEL_REGISTRY", "false").lower() == "true"
MODEL_STATE_PATH = Path(os.getenv("MODEL_STATE_PATH", "/shared/models/latest_model.json"))

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


class ForestCoverSample(BaseModel):
    elevation: float = Field(..., description="Elevation in meters")
    aspect: float = Field(..., description="Aspect in degrees")
    slope: float = Field(..., description="Slope in degrees")
    horizontal_distance_to_hydrology: float
    vertical_distance_to_hydrology: float
    horizontal_distance_to_roadways: float
    hillshade_9am: float
    hillshade_noon: float
    hillshade_3pm: float
    horizontal_distance_to_fire_points: float
    wilderness_area: str = Field(..., description="Wilderness area identifier")
    soil_type: str = Field(..., description="Soil type identifier")


class PredictionRequest(BaseModel):
    samples: List[ForestCoverSample]


class PredictionResponse(BaseModel):
    predictions: List[int]
    model_version: str


app = FastAPI(title="Forest Cover Inference API", version="1.1.0")


def _load_metadata(client: MlflowClient, run_id: str) -> dict:
    try:
        path = client.download_artifacts(run_id=run_id, path="model/feature_metadata.json")
        with open(path, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def _load_model_state_from_file() -> dict:
    if not MODEL_STATE_PATH.exists():
        raise HTTPException(status_code=503, detail="Local model metadata not found")
    try:
        with MODEL_STATE_PATH.open("r", encoding="utf-8") as fp:
            state = json.load(fp)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Corrupted model metadata: {exc}") from exc

    if not state.get("run_id"):
        raise HTTPException(status_code=503, detail="Model metadata missing run identifier")
    return state


@lru_cache(maxsize=1)
def _load_production_model():
    client = MlflowClient()

    if REGISTRY_ENABLED:
        versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        if not versions:
            raise HTTPException(status_code=503, detail="No production model available")

        version_info = versions[0]
        model_uri = f"models:/{MODEL_NAME}/Production"
        try:
            model = mlflow.pyfunc.load_model(model_uri)
        except Exception as exc:  # pragma: no cover - runtime guard
            raise HTTPException(status_code=500, detail=f"Failed to load model from registry: {exc}") from exc

        metadata = _load_metadata(client, version_info.run_id)
        return {
            "model": model,
            "metadata": metadata,
            "version": str(version_info.version),
        }

    state = _load_model_state_from_file()
    run_id = state["run_id"]
    model_uri = state.get("model_uri") or f"runs:/{run_id}/model"

    try:
        model = mlflow.pyfunc.load_model(model_uri)
    except Exception as exc:  # pragma: no cover - runtime guard
        raise HTTPException(status_code=500, detail=f"Failed to load model run {run_id}: {exc}") from exc

    metadata = state.get("feature_metadata") or _load_metadata(client, run_id)
    version = state.get("registered_version") or run_id

    return {
        "model": model,
        "metadata": metadata,
        "version": str(version),
    }


@app.get("/health")
def health() -> dict:
    status = "ok"
    detail = ""
    if not REGISTRY_ENABLED and not MODEL_STATE_PATH.exists():
        status = "degraded"
        detail = "Model registry disabled and local state missing"
    return {
        "status": status,
        "model_name": MODEL_NAME,
        "registry_enabled": REGISTRY_ENABLED,
        "detail": detail,
    }


@app.get("/metadata")
def metadata() -> dict:
    model_info = _load_production_model()
    return {
        "model_name": MODEL_NAME,
        "version": model_info["version"],
        "feature_names": model_info["metadata"].get("feature_names", []),
        "trained_at": model_info["metadata"].get("trained_at"),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    if not request.samples:
        raise HTTPException(status_code=400, detail="No samples provided")

    model_info = _load_production_model()
    model = model_info["model"]

    data = pd.DataFrame([sample.dict() for sample in request.samples])
    
    # Convert numeric columns to int64 to match training data format
    numeric_columns = [
        "elevation", "aspect", "slope", "horizontal_distance_to_hydrology",
        "vertical_distance_to_hydrology", "horizontal_distance_to_roadways",
        "hillshade_9am", "hillshade_noon", "hillshade_3pm",
        "horizontal_distance_to_fire_points"
    ]
    
    for col in numeric_columns:
        if col in data.columns:
            data[col] = data[col].astype('int64')

    try:
        predictions = model.predict(data)
    except Exception as exc:  # pragma: no cover - defensive against runtime issues
        raise HTTPException(status_code=500, detail=f"Model inference failed: {exc}") from exc

    return PredictionResponse(
        predictions=[int(pred) for pred in predictions],
        model_version=str(model_info["version"]),
    )


@app.post("/reload")
def reload_model() -> dict:
    _load_production_model.cache_clear()
    _load_production_model()
    return {"status": "reloaded"}
