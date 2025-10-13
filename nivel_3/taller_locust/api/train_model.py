"""
Script para entrenar y guardar un modelo ML simple.
En producción, este modelo debería ser consumido desde MLflow.
"""
import os
import joblib
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


def train_and_save_model():
    """Entrena un modelo simple de clasificación y lo guarda."""
    print("🔄 Cargando dataset Iris...")
    iris = load_iris()
    X, y = iris.data, iris.target
    
    # Dividir datos
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print("🔄 Entrenando modelo Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Evaluar
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"✅ Modelo entrenado con accuracy: {accuracy:.4f}")
    print("\n📊 Reporte de clasificación:")
    print(classification_report(y_test, y_pred, target_names=iris.target_names))
    
    # Crear directorio model si no existe
    model_dir = os.path.join(os.path.dirname(__file__), "..", "model")
    os.makedirs(model_dir, exist_ok=True)
    
    # Guardar modelo
    model_path = os.path.join(model_dir, "model.pkl")
    joblib.dump(model, model_path)
    print(f"💾 Modelo guardado en: {model_path}")
    
    # Guardar información del dataset para referencia
    metadata = {
        "feature_names": iris.feature_names,
        "target_names": iris.target_names.tolist(),
        "n_features": len(iris.feature_names),
        "accuracy": accuracy
    }
    metadata_path = os.path.join(model_dir, "metadata.pkl")
    joblib.dump(metadata, metadata_path)
    print(f"💾 Metadata guardada en: {metadata_path}")
    
    return model, metadata


if __name__ == "__main__":
    train_and_save_model()

