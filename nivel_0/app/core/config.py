from pydantic import BaseModel
import os

class Settings(BaseModel):
    app_name: str = "Clasificador de especies de pingüinos"
    version: str = "0.1.0"
    model_path: str = os.getenv("MODEL_PATH", "artifacts/model.joblib")

settings = Settings()
