from __future__ import annotations
import argparse, os, json
import numpy as np
import pandas as pd
from palmerpenguins import load_penguins
from joblib import dump
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

def load_data() -> pd.DataFrame:
    return load_penguins()

def basic_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["species"]).reset_index(drop=True)
    return df

def split_features_target(df: pd.DataFrame):
    target = "species"
    num_cols = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
    cat_cols = ["island", "sex"]
    X = df[num_cols + cat_cols].copy()
    y = df[target].astype("category").copy()
    return X, y, num_cols, cat_cols

def build_preprocessor(num_cols, cat_cols) -> ColumnTransformer:
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("num", numeric_pipeline, num_cols),
        ("cat", categorical_pipeline, cat_cols),
    ])

def build_model(model_choice: str, preprocessor: ColumnTransformer) -> tuple[Pipeline, dict]:
    if model_choice == "logreg":
        estimator = Pipeline([
            ("pre", preprocessor),
            ("clf", LogisticRegression(max_iter=1000)),
        ])
        param_grid = {
            "clf__C": [0.1, 1.0, 3.0, 10.0],
            "clf__solver": ["lbfgs", "saga"],
            "clf__penalty": ["l2"],
        }
    elif model_choice == "rf":
        estimator = Pipeline([
            ("pre", preprocessor),
            ("clf", RandomForestClassifier(random_state=42)),
        ])
        param_grid = {
            "clf__n_estimators": [200, 400, 800],
            "clf__max_depth": [None, 6, 10, 14],
            "clf__min_samples_split": [2, 4, 8],
        }
    else:
        raise ValueError("Modelo no soportado. Use 'rf' o 'logreg'.")
    return estimator, param_grid

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=str, default="rf", choices=["rf", "logreg"])
    ap.add_argument("--cv", type=int, default=5)
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--outdir", type=str, default="artifacts")
    args = ap.parse_args()

    # 1) Datos
    df = load_data()
    df = basic_cleaning(df)
    X, y, num_cols, cat_cols = split_features_target(df)
    pre = build_preprocessor(num_cols, cat_cols)

    # 2) Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, stratify=y, random_state=42
    )

    # 3) Modelo + GridSearch
    est, grid_params = build_model(args.model, pre)
    cv = StratifiedKFold(n_splits=args.cv, shuffle=True, random_state=42)
    grid = GridSearchCV(est, grid_params, cv=cv, scoring="accuracy", n_jobs=-1, refit=True, verbose=1)
    grid.fit(X_train, y_train)

    # 4) Evaluación
    y_pred = grid.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print("\n=== Mejor configuración ===")
    print(grid.best_params_)
    print(f"Mejor CV accuracy: {grid.best_score_:.4f}")
    print(f"Test accuracy: {acc:.4f}")

    print("\n=== Reporte de clasificación (test) ===")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Matriz de confusión:")
    print(confusion_matrix(y_test, y_pred))

    # 5) Guardar artefactos
    os.makedirs(args.outdir, exist_ok=True)
    from joblib import dump
    dump(grid.best_estimator_, os.path.join(args.outdir, "penguins_model.joblib"))

    metrics = {
        "cv_best_params": grid.best_params_,
        "cv_best_score": float(grid.best_score_),
        "test_accuracy": float(acc),
        "classification_report": classification_report(y_test, y_pred, zero_division=0, output_dict=True),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }
    with open(os.path.join(args.outdir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    schema = {
        "version": 1,
        "features": {"numeric": num_cols, "categorical": cat_cols},
        "target": "species",
        "example": {
            "bill_length_mm": 42.0,
            "bill_depth_mm": 18.0,
            "flipper_length_mm": 200.0,
            "body_mass_g": 4200.0,
            "island": "Biscoe",
            "sex": "male",
        },
        "notes": "One-hot en categóricas; escalado en numéricas; imputación habilitada.",
    }
    with open(os.path.join(args.outdir, "schema.json"), "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"\nArtefactos guardados en: {args.outdir}/")

if __name__ == "__main__":
    main()
