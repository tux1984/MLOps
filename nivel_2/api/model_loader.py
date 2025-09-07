from pathlib import Path
import os, joblib

# Carpeta donde se montan los modelos
MODELS_DIR = Path(os.getenv("MODELS_DIR", "/shared/models"))

class ModelNotFound(Exception):
    pass

def load_model(model_name: str):
    """
    Carga el modelo directamente.
    """
    fname = model_name if model_name.endswith(".pkl") else f"{model_name}.pkl"
    path = MODELS_DIR / fname
    if not path.exists():
        raise ModelNotFound(f"No existe el modelo: {fname} en {MODELS_DIR}")
    return joblib.load(path)
