from datetime import datetime, timedelta
import os
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator


def _train_penguins_models():
    import pandas as pd
    from sqlalchemy import create_engine
    from sklearn.model_selection import train_test_split, GridSearchCV
    from sklearn.preprocessing import LabelEncoder
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.svm import SVC
    from sklearn.metrics import classification_report
    import pickle

    host = os.getenv("APP_DB_HOST", "db")
    port = int(os.getenv("APP_DB_PORT", "5432"))
    db = os.getenv("APP_DB_NAME", "appdb")
    user = os.getenv("APP_DB_USER", "app")
    password = os.getenv("APP_DB_PASSWORD", "secret")

    engine = create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    )

    # Leer datos crudos desde Postgres
    df = pd.read_sql("penguins", con=engine)

    # Preprocesamiento según la lógica indicada
    df = df.dropna()

    le = LabelEncoder()
    df["species"] = le.fit_transform(df["species"])  # target: 0,1,2

    X = df.drop(columns=["species"])
    X = pd.get_dummies(X, drop_first=True)
    y = df["species"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    models = {
        "logistic_regression": (
            LogisticRegression(max_iter=1000),
            {"C": [0.1, 1.0, 10.0]},
        ),
        "random_forest": (
            RandomForestClassifier(),
            {"n_estimators": [50, 100]},
        ),
        "svc": (
            SVC(probability=True),
            {"C": [0.1, 1.0], "kernel": ["linear", "rbf"]},
        ),
    }

    output_dir = Path("/shared/models")
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, (model, params) in models.items():
        print(f"\nEntrenando modelo: {name}")
        grid = GridSearchCV(model, param_grid=params, cv=3)
        grid.fit(X_train, y_train)

        print(f"Mejor modelo para {name}: {grid.best_params_}")
        y_pred = grid.predict(X_test)
        print(classification_report(y_test, y_pred))

        bundle = {
            "model": grid.best_estimator_,
            "label_encoder": le,
            "feature_columns": list(X.columns),
        }
        model_path = output_dir / f"{name}.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"Guardado en: {model_path}")


with DAG(
    dag_id="penguins_train",
    description="Entrena modelos sobre penguins y guarda artefactos",
    schedule=timedelta(minutes=5),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["train", "penguins"],
):
    train = PythonOperator(
        task_id="train_penguins_models",
        python_callable=_train_penguins_models,
    )
