from typing import List, Dict, Literal
from pydantic import BaseModel, Field, field_validator

class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str

class PenguinInput(BaseModel):
    island: Literal["Biscoe", "Dream", "Torgersen"] = Field(..., description="Island", examples=["Biscoe"])
    bill_length_mm: float = Field(..., gt=0, description="Bill length (mm)", examples=[39.1])
    bill_depth_mm: float = Field(..., gt=0, description="Bill depth (mm)", examples=[18.7])
    flipper_length_mm: float = Field(..., gt=0, description="Flipper length (mm)", examples=[181])
    body_mass_g: float = Field(..., gt=0, description="Body mass (g)", examples=[3750])
    sex: Literal["male", "female"] = Field(..., description="Sex", examples=["male"])
    bill_ratio: float = Field(..., gt=0, description="Bill ratio", examples=[2.1])

    @field_validator("bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g")
    def _positive(cls, v):
        if v <= 0:
            raise ValueError("Debe ser positivo")
        return float(v)

class BatchInput(BaseModel):
    items: List[PenguinInput] = Field(..., min_items=1)

class Prediction(BaseModel):
    species: Literal["Adelie", "Chinstrap", "Gentoo"]
    probabilities: Dict[str, float]

class PredictionResponse(BaseModel):
    predictions: List[Prediction]
