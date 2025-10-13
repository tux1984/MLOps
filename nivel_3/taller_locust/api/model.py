"""
Módulo para cargar y usar el modelo de ML.
En producción, esto debería conectarse a MLflow para obtener el modelo.
"""
import os
import joblib
from typing import List, Optional


class ModelLoader:
    """Gestor del modelo de Machine Learning."""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Inicializa el loader del modelo.
        
        Args:
            model_path: Ruta al modelo. Si es None, usa la ruta por defecto.
        """
        if model_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base_dir, "..", "model", "model.pkl")
        
        self.model_path = model_path
        self.model = None
        self.metadata = None
        self._load_model()
    
    def _load_model(self):
        """Carga el modelo desde disco."""
        try:
            self.model = joblib.load(self.model_path)
            print(f"✅ Modelo cargado desde: {self.model_path}")
            
            # Intentar cargar metadata
            metadata_path = self.model_path.replace("model.pkl", "metadata.pkl")
            if os.path.exists(metadata_path):
                self.metadata = joblib.load(metadata_path)
                print(f"✅ Metadata cargada desde: {metadata_path}")
        except Exception as e:
            print(f"❌ Error al cargar el modelo: {e}")
            raise
    
    def predict(self, features: List[float]) -> dict:
        """
        Realiza una predicción.
        
        Args:
            features: Lista de características para la predicción.
            
        Returns:
            Diccionario con la predicción y probabilidades.
        """
        if self.model is None:
            raise ValueError("Modelo no cargado")
        
        # Validar entrada
        if self.metadata:
            expected_features = self.metadata["n_features"]
            if len(features) != expected_features:
                raise ValueError(
                    f"Se esperan {expected_features} características, "
                    f"se recibieron {len(features)}"
                )
        
        # Realizar predicción
        import numpy as np
        features_array = np.array(features).reshape(1, -1)
        prediction = self.model.predict(features_array)[0]
        probabilities = self.model.predict_proba(features_array)[0]
        
        # Preparar respuesta
        result = {
            "prediction": int(prediction),
            "probabilities": probabilities.tolist()
        }
        
        # Agregar nombre de la clase si hay metadata
        if self.metadata and "target_names" in self.metadata:
            result["class_name"] = self.metadata["target_names"][int(prediction)]
        
        return result
    
    def is_loaded(self) -> bool:
        """Verifica si el modelo está cargado."""
        return self.model is not None
    
    def get_metadata(self) -> Optional[dict]:
        """Retorna la metadata del modelo."""
        return self.metadata

