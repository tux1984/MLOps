import os
import mlflow.pyfunc
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
from mlflow.tracking import MlflowClient
from typing import Optional
from fastapi.responses import FileResponse
import tempfile
import shutil

# ------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "CreditScoreModel")
MODEL_STAGE = os.getenv("MLFLOW_MODEL_STAGE", "None")  # Valores: "None", "Production", "Staging"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# ------------------------------------------------
# CARGA DEL MODELO
# ------------------------------------------------
try:
    if MODEL_STAGE == "None":
        model_uri = f"models:/{MODEL_NAME}/latest"
    else:
        model_uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"

    model = mlflow.pyfunc.load_model(model_uri)
except Exception as e:
    raise RuntimeError(f"❌ Error al cargar el modelo desde MLflow: {e}")

# ------------------------------------------------
# FASTAPI APP
# ------------------------------------------------
app = FastAPI(
    title="Credit Score Prediction API",
    description="Predice el puntaje crediticio usando un modelo registrado en MLflow.",
    version="1.0.0"
)

# ------------------------------------------------
# ESTRUCTURA DEL REQUEST
# ------------------------------------------------
class CreditData(BaseModel):
    age: int
    income: float
    education_level: str  # Opciones válidas: "High School", "Bachelor", "Master", "PhD"

# ------------------------------------------------
# ENDPOINT DE PREDICCIÓN
# ------------------------------------------------
@app.post("/predict")
def predict(data: CreditData):
    try:
        # Convertir a DataFrame
        df = pd.DataFrame([data.dict()])

        # Definir todas las columnas esperadas del modelo
        expected_cols = ["age", "income",
                         "education_level_High School",
                         "education_level_Bachelor",
                         "education_level_Master",
                         "education_level_PhD"]

        # One-hot encoding manual con todos los niveles
        for level in ["High School", "Bachelor", "Master", "PhD"]:
            col = f"education_level_{level}"
            df[col] = (df["education_level"] == level).astype(int)

        df.drop(columns=["education_level"], inplace=True)

        # Asegurar que estén en orden correcto y que no falte ninguna
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0
        df = df[expected_cols]

        # Hacer predicción
        prediction = model.predict(df)[0]
        return {"credit_score": round(float(prediction), 2)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error en predicción: {e}")


# ------------------------------------------------
# HEALTH CHECK
# ------------------------------------------------
@app.get("/health")
def health_check():
    try:
        _ = model.predict(pd.DataFrame([[0, 0, 0, 0, 0]], columns=[
            "age", "income", "education_level_Bachelor", "education_level_Master", "education_level_PhD"
        ]))
        return {"status": "ok", "message": "✅ Modelo cargado correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Falló health check: {e}")

# ------------------------------------------------
# INFO DEL MODELO
# ------------------------------------------------
@app.get("/info")
def get_info():
    return {
        "tracking_uri": MLFLOW_TRACKING_URI,
        "model_name": MODEL_NAME,
        "model_stage": MODEL_STAGE,
        "model_uri": model_uri
    }

# ------------------------------------------------
# LISTADO DE EXPERIMENTOS
# ------------------------------------------------
@app.get("/experiments")
def list_experiments():
    client = MlflowClient()
    experiments = client.list_experiments()
    return [{"id": exp.experiment_id, "name": exp.name} for exp in experiments]

# ------------------------------------------------
# MEJOR RUN POR MÉTRICA
# ------------------------------------------------
@app.get("/experiments/{experiment_name}/best_run")
def get_best_run(experiment_name: str, metric: str = "r2"):
    client = MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise HTTPException(status_code=404, detail="🧪 Experimento no encontrado")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=[f"metrics.{metric} DESC"],
    )

    if not runs:
        raise HTTPException(status_code=404, detail="⚠️ No se encontraron runs")

    best_run = runs[0]
    return {
        "run_id": best_run.info.run_id,
        "metrics": best_run.data.metrics,
        "params": best_run.data.params,
        "tags": best_run.data.tags,
    }

# ------------------------------------------------
# DETALLES DE UN RUN ESPECÍFICO
# ------------------------------------------------
@app.get("/runs/{run_id}")
def get_run_details(run_id: str):
    client = MlflowClient()
    try:
        run = client.get_run(run_id)
        return {
            "run_id": run.info.run_id,
            "status": run.info.status,
            "metrics": run.data.metrics,
            "params": run.data.params,
            "tags": run.data.tags,
            "artifact_uri": run.info.artifact_uri,
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Run no encontrado")

# ------------------------------------------------
# DESCARGAR MODELO (opcional)
# ------------------------------------------------
@app.get("/model/latest")
def download_latest_model():
    try:
        temp_dir = tempfile.mkdtemp()
        local_path = mlflow.pyfunc.load_model(model_uri, dst_path=temp_dir)
        pkl_path = os.path.join(local_path, "model.pkl")

        if not os.path.exists(pkl_path):
            raise FileNotFoundError("model.pkl no encontrado")

        return FileResponse(pkl_path, filename="model.pkl", media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error descargando modelo: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
