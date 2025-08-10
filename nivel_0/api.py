# api.py (multi-modelo)
from __future__ import annotations
import os, json
from typing import List, Optional, Dict, Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from joblib import load

# === Config ===
# Puedes cambiar dirs por variables de entorno:
#   RF_DIR, LOGREG_DIR, DEFAULT_MODEL
MODELS_CONFIG = {
    "rf": os.getenv("RF_DIR", "artifacts_rf"),
    "logreg": os.getenv("LOGREG_DIR", "artifacts_logreg"),
}
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "rf")

REQUIRED_FILES = ["penguins_model.joblib"]  # schema.json y metrics.json son opcionales

app = FastAPI(title="Penguins Classifier API (Multi-model)", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción, delimita orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Pydantic ===
class PenguinIn(BaseModel):
    bill_length_mm: Optional[float] = Field(None)
    bill_depth_mm: Optional[float] = Field(None)
    flipper_length_mm: Optional[float] = Field(None)
    body_mass_g: Optional[float] = Field(None)
    island: Optional[str] = Field(None)
    sex: Optional[str] = Field(None)

class PredictRequest(BaseModel):
    records: List[PenguinIn]
    model: Optional[str] = Field(None, description="Nombre del modelo a usar (rf - logreg)")

class PredictResponse(BaseModel):
    model: str
    predictions: List[str]
    probabilities: Optional[List[Dict[str, float]]] = None
    classes: Optional[List[str]] = None

class CompareResponse(BaseModel):
    results: Dict[str, PredictResponse]  # nombre_modelo -> respuesta

# === Almacenamos bundles de modelos ===
class ModelBundle:
    def __init__(self, name: str, dirpath: str):
        self.name = name
        self.dir = dirpath
        self.model = None
        self.classes: Optional[List[str]] = None
        self.schema: Optional[Dict[str, Any]] = None
        self.metrics: Optional[Dict[str, Any]] = None

    def load(self):
        # Verifica archivos obligatorios
        for f in REQUIRED_FILES:
            full = os.path.join(self.dir, f)
            if not os.path.exists(full):
                raise RuntimeError(f"Falta {f} en {self.dir}")
        # Carga modelo
        self.model = load(os.path.join(self.dir, "penguins_model.joblib"))

        # Clases
        clf = getattr(self.model, "named_steps", {}).get("clf", None)
        self.classes = clf.classes_.tolist() if getattr(clf, "classes_", None) is not None else None

        # Opcionales
        schema_path = os.path.join(self.dir, "schema.json")
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                self.schema = json.load(f)

        metrics_path = os.path.join(self.dir, "metrics.json")
        if os.path.exists(metrics_path):
            with open(metrics_path, "r", encoding="utf-8") as f:
                self.metrics = json.load(f)

    def align_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # Si hay schema, garantizamos columnas y orden
        if self.schema and "features" in self.schema:
            expected = self.schema["features"].get("numeric", []) + self.schema["features"].get("categorical", [])
            for c in expected:
                if c not in df.columns:
                    df[c] = None
            df = df[expected]
        return df

MODELS: Dict[str, ModelBundle] = {}

@app.on_event("startup")
def _load_all_models():
    # Carga todo lo configurado
    failed = []
    for name, dirpath in MODELS_CONFIG.items():
        try:
            bundle = ModelBundle(name, dirpath)
            bundle.load()
            MODELS[name] = bundle
        except Exception as e:
            failed.append((name, str(e)))

    if not MODELS:
        raise RuntimeError(f"No se cargó ningún modelo. Errores: {failed}")

# === Endpoints ===
@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "loaded_models": list(MODELS.keys()),
        "default_model": DEFAULT_MODEL,
    }

@app.get("/models")
def list_models():
    out = {}
    for name, b in MODELS.items():
        info = {
            "dir": b.dir,
            "classes": b.classes,
        }
        if b.metrics:
            info.update({
                "test_accuracy": b.metrics.get("test_accuracy"),
                "cv_best_score": b.metrics.get("cv_best_score"),
                "cv_best_params": b.metrics.get("cv_best_params"),
            })
        out[name] = info
    return out

@app.get("/model/schema")
def model_schema(model: Optional[str] = Query(None, description="rf - logreg")):
    mname = model or DEFAULT_MODEL
    b = MODELS.get(mname)
    if not b:
        raise HTTPException(status_code=404, detail=f"Modelo '{mname}' no existe.")
    if not b.schema:
        raise HTTPException(status_code=404, detail=f"schema.json no disponible para '{mname}'.")
    return b.schema

@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest, model: Optional[str] = Query(None, description="rf - logreg")):
    # Prioridad: query param > campo en body > DEFAULT_MODEL
    mname = model or payload.model or DEFAULT_MODEL
    b = MODELS.get(mname)
    if not b:
        raise HTTPException(status_code=404, detail=f"Modelo '{mname}' no existe. Disponibles: {list(MODELS.keys())}")

    df = pd.DataFrame([rec.model_dump() for rec in payload.records])
    df = b.align_df(df)

    try:
        preds = b.model.predict(df)
        probs = None
        if hasattr(b.model, "predict_proba"):
            proba = b.model.predict_proba(df)
            if b.classes:
                probs = [{b.classes[i]: float(p[i]) for i in range(len(b.classes))} for p in proba]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al predecir con '{mname}': {e}")

    return PredictResponse(
        model=mname,
        predictions=[str(p) for p in preds],
        probabilities=probs,
        classes=b.classes,
    )

@app.post("/predict/compare", response_model=CompareResponse)
def predict_compare(payload: PredictRequest):
    df = pd.DataFrame([rec.model_dump() for rec in payload.records])
    results: Dict[str, PredictResponse] = {}

    for mname, b in MODELS.items():
        dfi = b.align_df(df.copy())
        try:
            preds = b.model.predict(dfi)
            probs = None
            if hasattr(b.model, "predict_proba"):
                proba = b.model.predict_proba(dfi)
                if b.classes:
                    probs = [{b.classes[i]: float(p[i]) for i in range(len(b.classes))} for p in proba]
            results[mname] = PredictResponse(
                model=mname,
                predictions=[str(p) for p in preds],
                probabilities=probs,
                classes=b.classes,
            )
        except Exception as e:
            # Si un modelo falla, devolvemos el error contextualizado
            raise HTTPException(status_code=400, detail=f"Error con modelo '{mname}': {e}")

    return CompareResponse(results=results)
