from fastapi import FastAPI, HTTPException, Query
from pathlib import Path

from fastapi import FastAPI, HTTPException
from schemas import PredictRequest, PredictResponse, CompareResponse
from model_loader import load_model, ModelNotFound
from helpers import preprocess_like_training

from typing import Optional, List
import pandas as pd




app = FastAPI(
    title="ML Model Serving API",
    description="API para servir modelos de clasificación entrenados desde JupyterLab",
    version="0.1.0"
)

DEFAULT_MODEL = "random_forest.pkl" 
DEFAULT_COMPARE = ["random_forest", "logistic_regression", "svc"]
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
    models = sorted(f.name for f in MODELS_DIR.glob("*.pkl"))
    return {
        "path": str(MODELS_DIR),
        "modelos_disponibles_total": len(models),
        "modelos_disponibles": models
    }

@app.post("/predict", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    model: Optional[str] = Query(
        None, description="Nombre del modelo (con o sin .pkl)"
    )
):
    # 1) Resolver modelo (query > body > default)
    mname = model or payload.model or DEFAULT_MODEL
    if not mname or mname == "string":
        raise HTTPException(
            status_code=400,
            detail=f"Indica un modelo válido. Disponibles: {DEFAULT_MODEL}"
        )

    # 2) Cargar modelo + encoder desde el bundle
    try:
        bundle = load_model(mname)   
        clf = bundle["model"]
        le = bundle["label_encoder"]
    except (FileNotFoundError, ModelNotFound) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cargando modelo: {repr(e)}")
    
    # 2) DF crudo desde PenguinIn
    df_raw = pd.DataFrame([rec.model_dump() for rec in payload.records])

    # 4) Preprocesar igual que en el training
    # Columnas esperadas: preferimos atributo del estimador; si no, usamos las del bundle
    expected = getattr(clf, "feature_names_in_", None) or bundle.get("feature_columns")
    if expected is None:
        df = pd.get_dummies(
            df_raw,
            columns=[c for c in ["island", "sex"] if c in df_raw.columns],
            drop_first=True
        )
    else:
        df = preprocess_like_training(df_raw, list(expected))

    # 5) Predecir
    try:
        y_pred = clf.predict(df)
        predictions = le.inverse_transform(y_pred).tolist()

        probs = None
        classes = None
        if hasattr(clf, "predict_proba"):
            proba = clf.predict_proba(df)
            classes = le.inverse_transform(clf.classes_).tolist()
            probs = [
                {classes[i]: round(float(p[i]), 4) for i in range(len(classes))}
                for p in proba
            ]
        elif hasattr(clf, "classes_"):
            classes = le.inverse_transform(clf.classes_).tolist()

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error al predecir con '{mname}': {e}"
        )

    # 6) Respuesta final
    return PredictResponse(
        model=mname if mname.endswith(".pkl") else f"{mname}.pkl",
        predictions=predictions,
        probabilities=probs,
        classes=classes
    )

@app.post("/predict/compare", response_model=CompareResponse)
def predict_compare(
    payload: PredictRequest,
    models: Optional[List[str]] = Query(
        None,
        description="Lista de modelos a comparar (con o sin .pkl). Ej: random_forest, logistic_regression y svc"
    )
):
    # 0) Validación rápida de entrada
    if not payload.records:
        raise HTTPException(status_code=400, detail="Debes enviar al menos un registro en 'records'.")

    # 1) Lista de modelos a correr
    names = models or DEFAULT_COMPARE

    # 2) DF crudo desde PenguinIn
    df_raw = pd.DataFrame([rec.model_dump() for rec in payload.records])

    results: dict[str, PredictResponse] = {}

    for name in names:
        mname = name  # respetamos el nombre que pasó el usuario
        try:
            # 3) Cargar bundle (modelo + label encoder)
            bundle = load_model(mname)
            clf = bundle["model"]
            le  = bundle["label_encoder"]

            # 4) Preprocesar como en training
            expected = getattr(clf, "feature_names_in_", None) or bundle.get("feature_columns")
            if expected is None:
                X = pd.get_dummies(
                    df_raw,
                    columns=[c for c in ["island", "sex"] if c in df_raw.columns],
                    drop_first=True
                )
            else:
                X = preprocess_like_training(df_raw, list(expected))

            # 5) Inferencia
            y_pred = clf.predict(X)
            predictions = le.inverse_transform(y_pred).tolist()

            probs = None
            classes = None
            if hasattr(clf, "predict_proba"):
                proba = clf.predict_proba(X)
                classes = le.inverse_transform(clf.classes_).tolist()
                # Redondeo 
                probs = [
                    {classes[i]: round(float(p[i]), 4) for i in range(len(classes))}
                    for p in proba
                ]
            elif hasattr(clf, "classes_"):
                classes = le.inverse_transform(clf.classes_).tolist()

            results[mname if mname.endswith(".pkl") else f"{mname}.pkl"] = PredictResponse(
                model=mname if mname.endswith(".pkl") else f"{mname}.pkl",
                predictions=predictions,
                probabilities=probs,
                classes=classes
            )

        except FileNotFoundError as e:
            # Modelo no existe
            results[mname if mname.endswith(".pkl") else f"{mname}.pkl"] = PredictResponse(
                model=mname if mname.endswith(".pkl") else f"{mname}.pkl",
                predictions=[f"ERROR: {e}"],
                probabilities=None,
                classes=None
            )
        except Exception as e:
            results[mname if mname.endswith(".pkl") else f"{mname}.pkl"] = PredictResponse(
                model=mname if mname.endswith(".pkl") else f"{mname}.pkl",
                predictions=[f"ERROR: {e}"],
                probabilities=None,
                classes=None
            )

    return CompareResponse(results=results)
