# app/main.py
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.utils import load_model_or_raise
from app.models.schemas import (
    HealthResponse, BatchInput, Prediction, PredictionResponse
)

import pandas as pd

tags_metadata = [
    {"name": "health", "description": "Verificación de estado y metadatos"},
    {"name": "inference", "description": "Predicción de especies de pingüinos"},
]

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    openapi_tags=tags_metadata,
    contact={"name": "Nombre o número del equipo"},
)

# --- Manejador de errores de validación (respuesta consistente) ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "ValidationError", "detail": exc.errors()},
    )

# --- Carga del modelo al iniciar ---
@app.on_event("startup")
def _load_artifacts():
    try:
        bundle = load_model_or_raise(settings.model_path)
        app.state.model = bundle["pipeline"]
        app.state.target_names = bundle["target_names"]
    except Exception as e:
        app.state.model = None
        app.state.target_names = []
        app.state.load_error = str(e)

def _ensure_model():
    if app.state.model is None:
        # 503 → servicio no disponible: no hay modelo cargado
        raise HTTPException(status_code=503, detail=getattr(app.state, "load_error", "Modelo no cargado"))

# --- Endpoints ---
@app.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    return HealthResponse(version=settings.version)

@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["inference"],
    responses={
        200: {"description": "Predicción exitosa"},
        400: {"description": "Solicitud incorrecta"},
        503: {"description": "Modelo no disponible"},
    },
)
def predict(payload: BatchInput):
    _ensure_model()
    model = app.state.model
    target_names = app.state.target_names

    # Convertimos a DataFrame (mismo orden que en entrenamiento)
    df = pd.DataFrame([
        {
            "island": it.island,
            "bill_length_mm": it.bill_length_mm,
            "bill_depth_mm": it.bill_depth_mm,
            "flipper_length_mm": it.flipper_length_mm,
            "body_mass_g": it.body_mass_g,
            "sex": it.sex,
            "bill_ratio": it.bill_ratio,
        }
        for it in payload.items
    ])

    try:
        probs = model.predict_proba(df)
        idx = probs.argmax(axis=1)
        preds = []
        for i, row in enumerate(probs):
            species = target_names[idx[i]]
            preds.append(Prediction(
                species=species,
                probabilities={name: float(row[j]) for j, name in enumerate(target_names)}
            ))
        return PredictionResponse(predictions=preds)
    except Exception as e:
        # 400 → error del cliente (datos incompatibles con el pipeline)
        raise HTTPException(status_code=400, detail=str(e))
