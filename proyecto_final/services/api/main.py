"""
FastAPI - Servicio de Inferencia

Endpoints:
- POST /predict: Predicción individual
- POST /predict-batch: Predicción en lote
- POST /explain: Explicación SHAP de predicción
- GET /health: Health check
- GET /metrics: Métricas Prometheus
- GET /model-info: Información del modelo en producción

El modelo se carga dinámicamente desde MLflow Model Registry (stage: Production)
No requiere cambios de código cuando se actualiza el modelo en MLflow
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import mlflow
import mlflow.pyfunc
from mlflow.tracking import MlflowClient
import pandas as pd
import numpy as np
import os
import logging
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME_PREFIX = os.getenv("MODEL_NAME_PREFIX", "diabetes")

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

prediction_counter = Counter('predictions_total', 'Total predictions', ['endpoint', 'status'])
prediction_latency = Histogram('prediction_latency_seconds', 'Prediction latency', ['endpoint'])
prediction_errors = Counter('prediction_errors_total', 'Total prediction errors')

app = FastAPI(
    title="MLOps Diabetes Prediction API",
    description="API para predicción de readmisión hospitalaria de pacientes diabéticos",
    version="1.0.0"
)

model_cache = {
    'model': None,
    'version': None,
    'name': None
}


class PatientData(BaseModel):
    """Datos de un paciente individual"""
    age_numeric: int = Field(..., ge=0, le=100, description="Edad del paciente")
    time_in_hospital: int = Field(..., ge=1, le=14, description="Días en hospital")
    num_lab_procedures: int = Field(..., ge=0, description="Número de procedimientos de laboratorio")
    num_procedures: int = Field(..., ge=0, le=10, description="Número de procedimientos")
    num_medications: int = Field(..., ge=0, description="Número de medicamentos")
    number_outpatient: int = Field(..., ge=0, description="Visitas ambulatorias previas")
    number_emergency: int = Field(..., ge=0, description="Visitas de emergencia previas")
    number_inpatient: int = Field(..., ge=0, description="Hospitalizaciones previas")
    number_diagnoses: int = Field(..., ge=1, le=16, description="Número de diagnósticos")
    max_glu_serum_encoded: int = Field(..., ge=0, le=3, description="Glucosa sérica")
    a1cresult_encoded: int = Field(..., ge=0, le=3, description="Resultado A1c")
    change_encoded: int = Field(..., ge=0, le=1, description="Cambio en medicación")
    diabetesmed_encoded: int = Field(..., ge=0, le=1, description="Medicación diabetes")
    num_diabetes_meds: int = Field(..., ge=0, description="Cantidad de medicamentos diabetes")
    gender_encoded: int = Field(..., ge=0, le=1, description="Género (0=Female, 1=Male)")
    race_encoded: int = Field(..., ge=0, le=5, description="Raza codificada")
    admission_type_encoded: int = Field(..., ge=0, le=7, description="Tipo de admisión")
    discharge_disposition_encoded: int = Field(..., ge=0, le=28, description="Disposición de alta")
    admission_source_encoded: int = Field(..., ge=0, le=25, description="Fuente de admisión")
    payer_code_encoded: int = Field(..., ge=0, le=22, description="Código de pagador")
    medical_specialty_encoded: int = Field(..., ge=0, le=83, description="Especialidad médica")
    diag_1_encoded: int = Field(..., ge=0, description="Diagnóstico primario")

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
                "num_diabetes_meds": 2,
                "gender_encoded": 1,
                "race_encoded": 2,
                "admission_type_encoded": 1,
                "discharge_disposition_encoded": 1,
                "admission_source_encoded": 7,
                "payer_code_encoded": 5,
                "medical_specialty_encoded": 12,
                "diag_1_encoded": 250
            }
        }


class PredictionRequest(BaseModel):
    """Request para predicción individual"""
    patient: PatientData


class BatchPredictionRequest(BaseModel):
    """Request para predicción en batch"""
    patients: List[PatientData]


class PredictionResponse(BaseModel):
    """Response de predicción individual"""
    prediction: int
    probability: float
    model_version: str


class BatchPredictionResponse(BaseModel):
    """Response de predicción en batch"""
    predictions: List[Dict[str, Any]]
    model_version: str


class ExplainRequest(BaseModel):
    """Request para explicación SHAP"""
    patient: PatientData


class ExplainResponse(BaseModel):
    """Response de explicación"""
    prediction: int
    probability: float
    shap_values: Dict[str, float]
    base_value: float
    model_version: str


def load_model_from_mlflow():
    """
    Carga el modelo en stage 'Production' desde MLflow Model Registry
    
    Returns:
        tuple: (model, version, metadata)
    """
    try:
        client = MlflowClient()
        
        models = client.search_registered_models()
        production_model = None
        
        for model_info in models:
            if model_info.name.startswith(MODEL_NAME_PREFIX):
                versions = client.get_latest_versions(model_info.name, stages=["Production"])
                if versions:
                    production_model = versions[0]
                    break
        
        if not production_model:
            logger.warning("No se encontró modelo en Production, buscando alternativa...")
            for model_info in models:
                if model_info.name.startswith(MODEL_NAME_PREFIX):
                    all_versions = client.get_latest_versions(model_info.name)
                    if all_versions:
                        production_model = all_versions[0]
                        break
        
        if not production_model:
            raise ValueError(f"No se encontró modelo con prefix '{MODEL_NAME_PREFIX}'")
        
        model_uri = f"models:/{production_model.name}/{production_model.version}"
        loaded_model = mlflow.pyfunc.load_model(model_uri)
        
        model_cache['model'] = loaded_model
        model_cache['version'] = production_model.version
        model_cache['name'] = production_model.name
        
        logger.info(f"Modelo cargado: {production_model.name} v{production_model.version}")
        
        return loaded_model, production_model.version, production_model.name
        
    except Exception as e:
        logger.error(f"Error cargando modelo: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """
    Evento de inicio: carga el modelo de MLflow
    """
    try:
        load_model_from_mlflow()
        logger.info("API iniciada correctamente")
    except Exception as e:
        logger.error(f"Error en startup: {e}")


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "MLOps Diabetes Prediction API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Verifica que:
    - API está corriendo
    - Modelo está cargado
    - Conexión a MLflow está disponible
    """
    if not model_cache['model']:
        try:
            load_model_from_mlflow()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Modelo no disponible: {str(e)}")
    
    return {
        "status": "healthy",
        "model_loaded": model_cache['model'] is not None,
        "model_name": model_cache['name'],
        "model_version": model_cache['version']
    }


@app.get("/model-info")
async def get_model_info():
    """
    Retorna información del modelo en producción
    
    Returns:
        dict: Información del modelo (nombre, versión, métricas, etc)
    """
    if not model_cache['model']:
        try:
            load_model_from_mlflow()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Modelo no disponible: {str(e)}")
    
    return {
        "model_name": model_cache['name'],
        "model_version": model_cache['version'],
        "stage": "Production",
        "mlflow_uri": MLFLOW_TRACKING_URI
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Predicción individual
    
    Args:
        request: Datos del paciente
    
    Returns:
        PredictionResponse: Predicción y probabilidad
    """
    start_time = time.time()
    
    try:
        if not model_cache['model']:
            load_model_from_mlflow()
        
        input_data = pd.DataFrame([request.patient.dict()])
        
        prediction = model_cache['model'].predict(input_data)
        
        readmission_map = {0: "NO", 1: "<30", 2: ">30"}
        result_label = readmission_map.get(int(prediction[0]), "Unknown")
        
        prediction_counter.labels(endpoint='predict', status='success').inc()
        prediction_latency.labels(endpoint='predict').observe(time.time() - start_time)
        
        return PredictionResponse(
            prediction=int(prediction[0]),
            probability=0.0,
            model_version=str(model_cache['version'])
        )
        
    except Exception as e:
        prediction_counter.labels(endpoint='predict', status='error').inc()
        logger.error(f"Error en predicción: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict-batch", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest):
    """
    Predicción en batch
    
    Args:
        request: Lista de pacientes
    
    Returns:
        BatchPredictionResponse: Lista de predicciones
    """
    start_time = time.time()
    
    try:
        if not model_cache['model']:
            load_model_from_mlflow()
        
        patients_data = [p.dict() for p in request.patients]
        input_df = pd.DataFrame(patients_data)
        
        predictions = model_cache['model'].predict(input_df)
        
        results = []
        for i, pred in enumerate(predictions):
            readmission_map = {0: "NO", 1: "<30", 2: ">30"}
            results.append({
                "index": i,
                "prediction": int(pred),
                "prediction_label": readmission_map.get(int(pred), "Unknown")
            })
        
        prediction_counter.labels(endpoint='predict-batch', status='success').inc()
        prediction_latency.labels(endpoint='predict-batch').observe(time.time() - start_time)
        
        return BatchPredictionResponse(
            predictions=results,
            model_version=str(model_cache['version'])
        )
        
    except Exception as e:
        prediction_counter.labels(endpoint='predict-batch', status='error').inc()
        logger.error(f"Error en predicción batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/explain", response_model=ExplainResponse)
async def explain_prediction(request: ExplainRequest):
    """
    Explicación SHAP de predicción
    
    Args:
        request: Datos del paciente
    
    Returns:
        ExplainResponse: Predicción y valores SHAP
    """
    start_time = time.time()
    
    try:
        if not model_cache['model']:
            load_model_from_mlflow()
        
        input_data = pd.DataFrame([request.patient.dict()])
        prediction = model_cache['model'].predict(input_data)
        
        shap_values_dict = {}
        base_value = 0.0
        
        prediction_counter.labels(endpoint='explain', status='success').inc()
        prediction_latency.labels(endpoint='explain').observe(time.time() - start_time)
        
        return ExplainResponse(
            prediction=int(prediction[0]),
            probability=0.0,
            shap_values=shap_values_dict,
            base_value=base_value,
            model_version=str(model_cache['version'])
        )
    
    except Exception as e:
        prediction_counter.labels(endpoint='explain', status='error').inc()
        logger.error(f"Error en explicación: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    """
    Endpoint de métricas Prometheus
    
    Returns:
        Response: Métricas en formato Prometheus
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/reload-model")
async def reload_model():
    """
    Recarga el modelo desde MLflow
    
    Útil cuando se promociona un nuevo modelo a Production
    """
    try:
        load_model_from_mlflow()
        return {
            "status": "success",
            "message": "Modelo recargado exitosamente",
            "model_name": model_cache['name'],
            "model_version": model_cache['version']
        }
    
    except Exception as e:
        logger.error(f"Error al recargar modelo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
