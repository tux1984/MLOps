from fastapi import FastAPI
from pathlib import Path

app = FastAPI(
    title="ML Model Serving API",
    description="API para servir modelos de clasificación entrenados desde JupyterLab",
    version="0.1.0"
)

MODELS_DIR = Path("/shared/models")


@app.get("/")
def root():
    return {
        "message": "Bienvenido a la API de inferencia de modelos ML",
        "endpoints": ["/models", "/predict/{model_name}"]
    }


@app.get("/models")
def list_models():
    """
    Retorna la lista de modelos .pkl disponibles en el volumen compartido.
    """
    models = [f.name for f in MODELS_DIR.glob("*.pkl")]
    return {"modelos_disponibles": models}
