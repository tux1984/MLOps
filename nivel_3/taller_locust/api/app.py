"""
API de inferencia usando FastAPI.
Proporciona endpoints para realizar predicciones con un modelo ML.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import time
import os

from api.model import ModelLoader


# Inicializar FastAPI
app = FastAPI(
    title="ML Inference API",
    description="API para realizar inferencia con modelo de Machine Learning",
    version="1.0.0"
)

# Cargar modelo al iniciar la aplicación
model_loader = None


@app.on_event("startup")
async def startup_event():
    """Evento que se ejecuta al iniciar la aplicación."""
    global model_loader
    print("🚀 Iniciando API de inferencia...")
    model_loader = ModelLoader()
    print("✅ API lista para recibir peticiones")


# Modelos Pydantic para validación
class PredictionRequest(BaseModel):
    """Modelo para la solicitud de predicción."""
    features: List[float] = Field(
        ...,
        description="Lista de características para la predicción",
        example=[5.1, 3.5, 1.4, 0.2]
    )


class PredictionResponse(BaseModel):
    """Modelo para la respuesta de predicción."""
    prediction: int = Field(..., description="Clase predicha")
    class_name: str = Field(None, description="Nombre de la clase predicha")
    probabilities: List[float] = Field(..., description="Probabilidades por clase")
    inference_time_ms: float = Field(..., description="Tiempo de inferencia en ms")


class HealthResponse(BaseModel):
    """Modelo para la respuesta de health check."""
    status: str
    model_loaded: bool
    metadata: dict = None


# Endpoints
@app.get("/", response_model=dict)
async def root():
    """Endpoint raíz - Health check básico."""
    return {
        "message": "ML Inference API",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check detallado."""
    return HealthResponse(
        status="healthy" if model_loader and model_loader.is_loaded() else "unhealthy",
        model_loaded=model_loader.is_loaded() if model_loader else False,
        metadata=model_loader.get_metadata() if model_loader else None
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Realiza una predicción usando el modelo cargado.
    
    Args:
        request: Solicitud con las características para la predicción.
        
    Returns:
        Respuesta con la predicción y probabilidades.
    """
    if not model_loader or not model_loader.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="Modelo no disponible"
        )
    
    try:
        # Medir tiempo de inferencia
        start_time = time.time()
        result = model_loader.predict(request.features)
        inference_time = (time.time() - start_time) * 1000  # Convertir a ms
        
        return PredictionResponse(
            prediction=result["prediction"],
            class_name=result.get("class_name", "unknown"),
            probabilities=result["probabilities"],
            inference_time_ms=round(inference_time, 2)
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción: {str(e)}")


@app.get("/metrics")
async def metrics():
    """Endpoint para métricas básicas."""
    return {
        "model_loaded": model_loader.is_loaded() if model_loader else False,
        "model_path": model_loader.model_path if model_loader else None,
        "metadata": model_loader.get_metadata() if model_loader else None
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=1
    )

