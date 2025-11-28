"""
Locust Load Testing

Escenarios de prueba:
1. Predicción individual
2. Predicción batch
3. Explicación SHAP
4. Health checks

Métricas:
- Response time
- Throughput (requests/second)
- Error rate
- Concurrent users
"""

from locust import HttpUser, task, between
import random
import json


class DiabetesPredictionUser(HttpUser):
    """
    Simula un usuario haciendo peticiones a la API
    """
    wait_time = between(1, 3)  # Espera entre 1-3 segundos entre requests
    
    def on_start(self):
        """Se ejecuta una vez al iniciar cada usuario"""
        # TODO: Inicialización si es necesaria
        pass
    
    @task(5)  # Peso 5: se ejecuta más frecuentemente
    def predict_single(self):
        """
        Test de predicción individual
        """
        # TODO: Implementar
        # - Generar datos de paciente aleatorios
        # - Hacer POST a /predict
        # - Validar response
        # Ejemplo:
        # patient_data = {
        #     "patient": {
        #         "age": random.randint(20, 90),
        #         "gender": random.choice(["Male", "Female"]),
        #         # ... resto de fields
        #     }
        # }
        # self.client.post("/predict", json=patient_data, name="/predict")
        pass
    
    @task(2)  # Peso 2: menos frecuente
    def predict_batch(self):
        """
        Test de predicción batch
        """
        # TODO: Implementar
        # - Generar lista de 10 pacientes
        # - Hacer POST a /predict-batch
        # - Validar response
        pass
    
    @task(1)  # Peso 1: aún menos frecuente
    def explain_prediction(self):
        """
        Test de explicación SHAP
        """
        # TODO: Implementar
        # - Generar datos de paciente
        # - Hacer POST a /explain
        # - Validar response (más lento que predict normal)
        pass
    
    @task(3)
    def health_check(self):
        """
        Test de health check
        """
        # TODO: Implementar
        # - Hacer GET a /health
        # - Validar response
        pass
    
    @task(2)
    def model_info(self):
        """
        Test de información del modelo
        """
        # TODO: Implementar
        # - Hacer GET a /model-info
        # - Validar response
        pass


class StressTestUser(HttpUser):
    """
    Usuario para stress testing con carga más agresiva
    """
    wait_time = between(0.1, 0.5)  # Espera muy corta
    
    @task
    def rapid_predictions(self):
        """
        Predicciones rápidas consecutivas
        """
        # TODO: Implementar predicciones rápidas
        pass


# Configuración adicional para diferentes escenarios de prueba
# puede ejecutarse con:
# locust -f locustfile.py --host=http://api:8000 -u 100 -r 10
# donde -u = usuarios, -r = spawn rate
