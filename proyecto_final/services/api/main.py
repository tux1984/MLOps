"""
FastAPI - API de Inferencia para Predicción de Precios Inmobiliarios

Características:
- Consume modelo desde MLflow Model Registry (stage: Production)
- Predicción individual y batch
- Explicabilidad con SHAP
- Guarda todas las inferencias en RAW DB para reentrenamiento
- Métricas para Prometheus
- No requiere cambios de código al actualizar modelo
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
import psycopg2
import psycopg2.extras
from datetime import datetime
import shap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "realtor_price_model")

# Configuración de base de datos RAW para guardar inferencias
RAW_DB_HOST = os.getenv("RAW_DB_HOST", "db-raw")
RAW_DB_PORT = int(os.getenv("RAW_DB_PORT", "5432"))
RAW_DB_NAME = os.getenv("RAW_DB_NAME", "mlops_raw")
RAW_DB_USER = os.getenv("RAW_DB_USER", "mlops")
RAW_DB_PASSWORD = os.getenv("RAW_DB_PASSWORD", "mlops123")

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Métricas Prometheus
prediction_counter = Counter('predictions_total', 'Total predictions', ['endpoint', 'status'])
prediction_latency = Histogram('prediction_latency_seconds', 'Prediction latency', ['endpoint'])
prediction_errors = Counter('prediction_errors_total', 'Total prediction errors')

app = FastAPI(
    title="MLOps Realtor Price Prediction API",
    description="API para predicción de precios de propiedades inmobiliarias",
    version="1.0.0"
)

# CORS para frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache del modelo
model_cache = {
    'model': None,
    'version': None,
    'name': None,
    'stage': None
}


class PropertyData(BaseModel):
    """Datos de una propiedad inmobiliaria"""
    brokered_by: str = Field(..., description="Agencia/corredor")
    status: str = Field(..., description="Estado: for_sale o ready_to_build")
    bed: int = Field(..., ge=0, le=20, description="Número de habitaciones")
    bath: float = Field(..., ge=0, le=10, description="Número de baños")
    acre_lot: float = Field(..., ge=0, description="Tamaño del terreno en acres")
    street: str = Field(..., description="Dirección de la calle")
    city: str = Field(..., description="Ciudad")
    state: str = Field(..., description="Estado")
    zip_code: str = Field(..., description="Código postal")
    house_size: int = Field(..., ge=0, description="Tamaño de la casa (sq ft)")
    prev_sold_date: Optional[str] = Field(None, description="Fecha de venta anterior (YYYY-MM-DD)")

    class Config:
        json_schema_extra = {
            "example": {
                "brokered_by": "Century 21",
                "status": "for_sale",
                "bed": 3,
                "bath": 2.0,
                "acre_lot": 0.25,
                "street": "123 Main St",
                "city": "Miami",
                "state": "Florida",
                "zip_code": "33101",
                "house_size": 1500,
                "prev_sold_date": "2020-01-15"
            }
        }


class PredictionRequest(BaseModel):
    """Request para predicción individual"""
    property: PropertyData


class BatchPredictionRequest(BaseModel):
    """Request para predicción batch"""
    properties: List[PropertyData]


class PredictionResponse(BaseModel):
    """Respuesta de predicción"""
    predicted_price: float
    model_name: str
    model_version: str
    model_stage: str
    timestamp: str


class BatchPredictionResponse(BaseModel):
    """Respuesta de predicción batch"""
    predictions: List[Dict[str, Any]]
    model_name: str
    model_version: str
    model_stage: str
    total_predictions: int


def get_raw_db_connection():
    """Establece conexión a base de datos RAW"""
    return psycopg2.connect(
        host=RAW_DB_HOST,
        port=RAW_DB_PORT,
        dbname=RAW_DB_NAME,
        user=RAW_DB_USER,
        password=RAW_DB_PASSWORD
    )


def save_inference_to_raw_db(property_data: dict, predicted_price: float):
    """
    Guarda datos de inferencia en RAW DB para futuros reentrenamientos
    
    Args:
        property_data: Datos de la propiedad
        predicted_price: Precio predicho
    """
    try:
        conn = get_raw_db_connection()
        cur = conn.cursor()
        
        # Crear tabla si no existe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inference_log (
                id SERIAL PRIMARY KEY,
                brokered_by VARCHAR(500),
                status VARCHAR(50),
                predicted_price FLOAT,
                bed INTEGER,
                bath FLOAT,
                acre_lot FLOAT,
                street VARCHAR(500),
                city VARCHAR(200),
                state VARCHAR(100),
                zip_code VARCHAR(20),
                house_size INTEGER,
                prev_sold_date DATE,
                inference_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_version VARCHAR(50)
            )
        """)
        
        # Insertar inferencia
        cur.execute("""
            INSERT INTO inference_log 
            (brokered_by, status, predicted_price, bed, bath, acre_lot, 
             street, city, state, zip_code, house_size, prev_sold_date, model_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            property_data.get('brokered_by'),
            property_data.get('status'),
            predicted_price,
            property_data.get('bed'),
            property_data.get('bath'),
            property_data.get('acre_lot'),
            property_data.get('street'),
            property_data.get('city'),
            property_data.get('state'),
            property_data.get('zip_code'),
            property_data.get('house_size'),
            property_data.get('prev_sold_date'),
            model_cache.get('version', 'unknown')
        ))
        
        conn.commit()
        logger.info(f"Inference saved to RAW DB")
        
    except Exception as e:
        logger.error(f"Error saving inference to RAW DB: {str(e)}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def load_production_model():
    """
    Carga el modelo en stage Production desde MLflow
    
    Returns:
        Model: Modelo cargado
    """
    try:
        client = MlflowClient()
        
        # Buscar modelo en stage Production
        models = client.search_model_versions(f"name='{MODEL_NAME}'")
        production_models = [m for m in models if m.current_stage == 'Production']
        
        if not production_models:
            logger.error(f"No model found in Production stage for {MODEL_NAME}")
            return None
        
        # Tomar el primero (debería haber solo uno)
        production_model = production_models[0]
        model_uri = f"models:/{MODEL_NAME}/Production"
        
        logger.info(f"Loading model: {MODEL_NAME} v{production_model.version} from Production")
        model = mlflow.pyfunc.load_model(model_uri)
        
        # Actualizar cache
        model_cache['model'] = model
        model_cache['name'] = MODEL_NAME
        model_cache['version'] = production_model.version
        model_cache['stage'] = 'Production'
        
        logger.info(f"Model loaded successfully: {MODEL_NAME} v{production_model.version}")
        return model
        
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return None


@app.on_event("startup")
async def startup_event():
    """Inicializa el modelo al arrancar la API"""
    logger.info("Starting API and loading model...")
    load_production_model()
    if model_cache['model']:
        logger.info(f"API ready with model {model_cache['name']} v{model_cache['version']}")
    else:
        logger.warning("API started but no model loaded. Check MLflow.")


@app.get("/")
def root():
    """Endpoint raíz"""
    return {
        "service": "MLOps Realtor Price Prediction API",
        "status": "running",
        "model_loaded": model_cache['model'] is not None,
        "endpoints": {
            "health": "/health",
            "model_info": "/model-info",
            "predict": "/predict",
            "predict_batch": "/predict-batch",
            "explain": "/explain",
            "metrics": "/metrics",
            "reload_model": "/reload-model"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    model_loaded = model_cache['model'] is not None
    return {
        "status": "healthy" if model_loaded else "degraded",
        "model_loaded": model_loaded,
        "model_name": model_cache.get('name'),
        "model_version": model_cache.get('version'),
        "mlflow_uri": MLFLOW_TRACKING_URI
    }


@app.get("/model-info")
def model_info():
    """Información del modelo actual"""
    if not model_cache['model']:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {
        "model_name": model_cache['name'],
        "model_version": model_cache['version'],
        "model_stage": model_cache['stage'],
        "mlflow_tracking_uri": MLFLOW_TRACKING_URI
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    """
    Predicción individual de precio de propiedad
    
    Args:
        request: Datos de la propiedad
        
    Returns:
        PredictionResponse: Precio predicho y metadata del modelo
    """
    start_time = time.time()
    
    try:
        if not model_cache['model']:
            prediction_counter.labels(endpoint='predict', status='error').inc()
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Convertir a DataFrame
        property_dict = request.property.dict()
        df = pd.DataFrame([property_dict])
        
        # Realizar predicción
        prediction = model_cache['model'].predict(df)[0]
        
        # Guardar inferencia en RAW DB
        save_inference_to_raw_db(property_dict, float(prediction))
        
        # Métricas
        latency = time.time() - start_time
        prediction_latency.labels(endpoint='predict').observe(latency)
        prediction_counter.labels(endpoint='predict', status='success').inc()
        
        return PredictionResponse(
            predicted_price=float(prediction),
            model_name=model_cache['name'],
            model_version=model_cache['version'],
            model_stage=model_cache['stage'],
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        prediction_errors.inc()
        prediction_counter.labels(endpoint='predict', status='error').inc()
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/predict-batch", response_model=BatchPredictionResponse)
def predict_batch(request: BatchPredictionRequest):
    """
    Predicción batch de múltiples propiedades
    
    Args:
        request: Lista de propiedades
        
    Returns:
        BatchPredictionResponse: Predicciones y metadata
    """
    start_time = time.time()
    
    try:
        if not model_cache['model']:
            prediction_counter.labels(endpoint='predict_batch', status='error').inc()
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Convertir a DataFrame
        properties_list = [prop.dict() for prop in request.properties]
        df = pd.DataFrame(properties_list)
        
        # Realizar predicciones
        predictions = model_cache['model'].predict(df)
        
        # Construir respuesta
        results = []
        for i, (prop_dict, pred) in enumerate(zip(properties_list, predictions)):
            # Guardar cada inferencia
            save_inference_to_raw_db(prop_dict, float(pred))
            
            results.append({
                "index": i,
                "property": prop_dict,
                "predicted_price": float(pred)
            })
        
        # Métricas
        latency = time.time() - start_time
        prediction_latency.labels(endpoint='predict_batch').observe(latency)
        prediction_counter.labels(endpoint='predict_batch', status='success').inc()
        
        return BatchPredictionResponse(
            predictions=results,
            model_name=model_cache['name'],
            model_version=model_cache['version'],
            model_stage=model_cache['stage'],
            total_predictions=len(results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        prediction_errors.inc()
        prediction_counter.labels(endpoint='predict_batch', status='error').inc()
        logger.error(f"Batch prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")


@app.post("/explain")
def explain_prediction(request: PredictionRequest):
    """
    Explicación SHAP de una predicción
    
    Args:
        request: Datos de la propiedad
        
    Returns:
        dict: Valores SHAP y explicación
    """
    try:
        if not model_cache['model']:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Convertir a DataFrame
        property_dict = request.property.dict()
        df = pd.DataFrame([property_dict])
        
        # Realizar predicción
        prediction = model_cache['model'].predict(df)[0]
        
        # Calcular SHAP values
        # Nota: Esto asume que el modelo tiene un modelo subyacente
        try:
            explainer = shap.Explainer(model_cache['model'])
            shap_values = explainer(df)
            
            # Extraer valores
            feature_names = df.columns.tolist()
            shap_vals = shap_values.values[0].tolist()
            base_value = shap_values.base_values[0] if hasattr(shap_values, 'base_values') else 0
            
            # Crear lista ordenada por impacto
            feature_importance = [
                {"feature": name, "value": float(val), "data_value": df[name].values[0]}
                for name, val in zip(feature_names, shap_vals)
            ]
            feature_importance.sort(key=lambda x: abs(x['value']), reverse=True)
            
            return {
                "predicted_price": float(prediction),
                "base_value": float(base_value),
                "shap_values": feature_importance,
                "model_name": model_cache['name'],
                "model_version": model_cache['version']
            }
            
        except Exception as e:
            logger.warning(f"SHAP calculation failed: {str(e)}")
            # Fallback: retornar feature importance del modelo si está disponible
            return {
                "predicted_price": float(prediction),
                "message": "SHAP not available for this model type",
                "model_name": model_cache['name'],
                "model_version": model_cache['version']
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Explanation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")


@app.post("/reload-model")
def reload_model():
    """
    Recarga el modelo desde MLflow (útil después de un nuevo deployment)
    
    Returns:
        dict: Información del modelo recargado
    """
    try:
        load_production_model()
        
        if model_cache['model']:
            return {
                "status": "success",
                "message": "Model reloaded successfully",
                "model_name": model_cache['name'],
                "model_version": model_cache['version'],
                "model_stage": model_cache['stage']
            }
        else:
            raise HTTPException(status_code=503, detail="Failed to reload model")
            
    except Exception as e:
        logger.error(f"Model reload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Model reload failed: {str(e)}")


@app.get("/metrics")
def metrics():
    """Endpoint de métricas para Prometheus"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/models/history")
def get_models_history():
    """
    Obtiene historial de todos los modelos registrados
    
    Returns:
        dict: Lista de modelos con sus métricas y stages
    """
    try:
        client = MlflowClient()
        
        # Obtener todas las versiones del modelo
        models = client.search_model_versions(f"name='{MODEL_NAME}'")
        
        history = []
        for model_version in models:
            # Obtener métricas del run asociado
            run = client.get_run(model_version.run_id)
            metrics = run.data.metrics
            
            history.append({
                "version": model_version.version,
                "stage": model_version.current_stage,
                "run_id": model_version.run_id,
                "creation_timestamp": model_version.creation_timestamp,
                "metrics": {
                    "rmse": metrics.get("rmse"),
                    "mae": metrics.get("mae"),
                    "r2": metrics.get("r2"),
                    "mape": metrics.get("mape")
                },
                "description": model_version.description or "",
                "tags": model_version.tags
            })
        
        # Ordenar por versión descendente
        history.sort(key=lambda x: int(x['version']), reverse=True)
        
        return {
            "model_name": MODEL_NAME,
            "total_versions": len(history),
            "history": history
        }
        
    except Exception as e:
        logger.error(f"Error getting models history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get models history: {str(e)}")


@app.get("/inference-stats")
def get_inference_stats():
    """
    Estadísticas de inferencias realizadas
    
    Returns:
        dict: Estadísticas de uso
    """
    try:
        conn = get_raw_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Total de inferencias
        cur.execute("SELECT COUNT(*) as total FROM inference_log")
        total = cur.fetchone()['total'] if cur.rowcount > 0 else 0
        
        # Inferencias por modelo
        cur.execute("""
            SELECT model_version, COUNT(*) as count
            FROM inference_log
            GROUP BY model_version
            ORDER BY count DESC
        """)
        by_model = cur.fetchall()
        
        # Inferencias recientes (últimas 24h)
        cur.execute("""
            SELECT COUNT(*) as recent
            FROM inference_log
            WHERE inference_timestamp > NOW() - INTERVAL '24 hours'
        """)
        recent = cur.fetchone()['recent'] if cur.rowcount > 0 else 0
        
        return {
            "total_inferences": total,
            "recent_24h": recent,
            "by_model_version": by_model
        }
        
    except Exception as e:
        logger.error(f"Error getting inference stats: {str(e)}")
        return {"total_inferences": 0, "error": str(e)}
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
