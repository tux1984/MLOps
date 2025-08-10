import os
import joblib

def load_model_or_raise(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Modelo no encontrado en {path}. Ejecuta scripts/train.py primero."
        )
    return joblib.load(path)
