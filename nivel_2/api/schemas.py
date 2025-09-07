from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from typing_extensions import Literal  # si usas Python < 3.11

class PenguinIn(BaseModel):
    bill_length_mm: float = Field(..., gt=0, description="Bill length (mm)", examples=[39.1])
    bill_depth_mm: float = Field(..., gt=0, description="Bill depth (mm)", examples=[18.7])
    flipper_length_mm: float = Field(..., gt=0, description="Flipper length (mm)", examples=[181])
    body_mass_g: float = Field(..., gt=0, description="Body mass (g)", examples=[3750])
    island: Literal["Biscoe", "Dream", "Torgersen"] = Field(..., description="Island", examples=["Biscoe"])
    sex: Literal["male", "female"] = Field(..., description="Sex", examples=["male"])

class PredictRequest(BaseModel):
    records: List[PenguinIn]
    model: Optional[str] = None

class PredictResponse(BaseModel):
    model: str
    predictions: List[str]
    probabilities: Optional[List[Dict[str, float]]] = None
    classes: Optional[List[str]] = None

class CompareResponse(BaseModel):
    results: Dict[str, PredictResponse]