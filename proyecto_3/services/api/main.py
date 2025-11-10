"""
API de inferencia para modelo de diabetes.
Consume el modelo en stage 'Production' de MLflow.
Expone métricas para Prometheus.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import mlflow.pyfunc
from mlflow.tracking import MlflowClient
import pandas as pd
import numpy as np
import os
import logging
from typing import Dict, Any

# Configuración
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME_PREFIX = os.environ.get("MODEL_NAME_PREFIX", "diabetes")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Diabetes Readmission Prediction API",
    description="API para predicción de readmisión de pacientes diabéticos",
    version="1.0.0"
)

# Métricas Prometheus
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method'])
REQUEST_LATENCY = Histogram('api_request_duration_seconds', 'Request latency', ['endpoint'])
PREDICTION_COUNT = Counter('predictions_total', 'Total predictions made', ['model_version'])
PREDICTION_ERRORS = Counter('prediction_errors_total', 'Total prediction errors')

# Cache del modelo
model_cache = {
    'model': None,
    'version': None,
    'name': None
}


class PredictionRequest(BaseModel):
    """Schema de entrada para predicción."""
    age_numeric: int = Field(..., ge=0, le=100, description="Edad del paciente")
    time_in_hospital: int = Field(..., ge=1, le=14, description="Días en hospital (1-14)")
    num_lab_procedures: int = Field(..., ge=0, description="Número de procedimientos de laboratorio")
    num_procedures: int = Field(..., ge=0, le=10, description="Número de procedimientos")
    num_medications: int = Field(..., ge=0, description="Número de medicamentos")
    number_outpatient: int = Field(..., ge=0, description="Visitas ambulatorias previas")
    number_emergency: int = Field(..., ge=0, description="Visitas de emergencia previas")
    number_inpatient: int = Field(..., ge=0, description="Hospitalizaciones previas")
    number_diagnoses: int = Field(..., ge=1, le=16, description="Número de diagnósticos")
    max_glu_serum_encoded: int = Field(..., ge=0, le=3, description="Glucosa sérica (0=None, 1=Norm, 2=>200, 3=>300)")
    a1cresult_encoded: int = Field(..., ge=0, le=3, description="Resultado A1c (0=None, 1=Norm, 2=>7, 3=>8)")
    change_encoded: int = Field(..., ge=0, le=1, description="Cambio en medicación (0=No, 1=Sí)")
    diabetesmed_encoded: int = Field(..., ge=0, le=1, description="Medicación diabetes (0=No, 1=Sí)")
    num_diabetes_meds: int = Field(..., ge=0, description="Cantidad de medicamentos para diabetes")

    class Config:
        schema_extra = {
            "example": {
                "age_numeric": 55,
                "time_in_hospital": 3,
                "num_lab_procedures": 45,
                "num_procedures": 1,
                "num_medications": 15,
                "number_outpatient": 0,
                "number_emergency": 0,
                "number_inpatient": 0,
                "number_diagnoses": 9,
                "max_glu_serum_encoded": 0,
                "a1cresult_encoded": 0,
                "change_encoded": 1,
                "diabetesmed_encoded": 1,
                "num_diabetes_meds": 2
            }
        }


def load_production_model():
    """Carga el modelo en stage 'Production' desde MLflow."""
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = MlflowClient()
        
        # Buscar modelos en Production
        models = client.search_registered_models()
        
        production_model = None
        for model in models:
            if model.name.startswith(MODEL_NAME_PREFIX):
                versions = client.get_latest_versions(model.name, stages=["Production"])
                if versions:
                    production_model = versions[0]
                    break
        
        if not production_model:
            logger.warning("No se encontró modelo en Production, buscando alternativa...")
            # Fallback: buscar cualquier modelo del prefix
            for model in models:
                if model.name.startswith(MODEL_NAME_PREFIX):
                    all_versions = client.get_latest_versions(model.name)
                    if all_versions:
                        production_model = all_versions[0]
                        break
        
        if not production_model:
            raise ValueError(f"No se encontró ningún modelo con prefix '{MODEL_NAME_PREFIX}'")
        
        model_uri = f"models:/{production_model.name}/{production_model.version}"
        loaded_model = mlflow.pyfunc.load_model(model_uri)
        
        model_cache['model'] = loaded_model
        model_cache['version'] = production_model.version
        model_cache['name'] = production_model.name
        
        logger.info(f"Modelo cargado: {production_model.name} v{production_model.version}")
        
        return loaded_model, production_model.name, production_model.version
        
    except Exception as e:
        logger.error(f"Error cargando modelo: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """Carga el modelo al iniciar la API."""
    try:
        load_production_model()
    except Exception as e:
        logger.error(f"Error en startup: {e}")


@app.get("/")
def root():
    """Health check."""
    REQUEST_COUNT.labels(endpoint='/', method='GET').inc()
    return {
        "service": "Diabetes Readmission Prediction API",
        "status": "healthy",
        "model_loaded": model_cache['model'] is not None
    }


@app.get("/model/info")
def model_info():
    """Información del modelo actualmente cargado."""
    REQUEST_COUNT.labels(endpoint='/model/info', method='GET').inc()
    
    if not model_cache['model']:
        try:
            load_production_model()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Modelo no disponible: {str(e)}")
    
    return {
        "model_name": model_cache['name'],
        "model_version": model_cache['version'],
        "stage": "Production",
        "mlflow_uri": MLFLOW_TRACKING_URI
    }


@app.post("/predict")
@REQUEST_LATENCY.labels(endpoint='/predict').time()
def predict(request: PredictionRequest):
    """Realiza predicción de readmisión."""
    REQUEST_COUNT.labels(endpoint='/predict', method='POST').inc()
    
    try:
        # Cargar modelo si no está en cache
        if not model_cache['model']:
            load_production_model()
        
        # Preparar datos
        input_data = pd.DataFrame([request.dict()])
        
        # Predicción
        prediction = model_cache['model'].predict(input_data)
        
        # Decodificar resultado (asumiendo NO, <30, >30)
        readmission_map = {0: "NO", 1: "<30", 2: ">30"}
        result = readmission_map.get(int(prediction[0]), "Unknown")
        
        PREDICTION_COUNT.labels(model_version=model_cache['version']).inc()
        
        return {
            "prediction": result,
            "model_name": model_cache['name'],
            "model_version": model_cache['version'],
            "input_features": request.dict()
        }
        
    except Exception as e:
        PREDICTION_ERRORS.inc()
        logger.error(f"Error en predicción: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reload-model")
def reload_model():
    """Recarga el modelo desde MLflow (útil después de nuevo despliegue)."""
    REQUEST_COUNT.labels(endpoint='/reload-model', method='POST').inc()
    
    try:
        load_production_model()
        return {
            "status": "success",
            "model_name": model_cache['name'],
            "model_version": model_cache['version']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def metrics():
    """Endpoint de métricas para Prometheus."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
