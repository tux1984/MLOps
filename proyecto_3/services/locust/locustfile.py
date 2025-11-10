"""
Locust load testing para API de predicción de diabetes.
Determina la capacidad máxima de usuarios concurrentes.
"""
from locust import HttpUser, task, between
import random


class DiabetesAPIUser(HttpUser):
    """Usuario que realiza requests a la API de predicción."""
    
    wait_time = between(1, 3)  # Espera entre 1 y 3 segundos entre requests
    
    def on_start(self):
        """Se ejecuta al iniciar cada usuario."""
        # Health check al inicio
        self.client.get("/")
    
    @task(3)
    def predict_readmission(self):
        """Tarea principal: predicción (peso 3)."""
        # Generar datos aleatorios pero realistas
        payload = {
            "age_numeric": random.randint(30, 90),
            "time_in_hospital": random.randint(1, 14),
            "num_lab_procedures": random.randint(10, 100),
            "num_procedures": random.randint(0, 6),
            "num_medications": random.randint(5, 30),
            "number_outpatient": random.randint(0, 5),
            "number_emergency": random.randint(0, 3),
            "number_inpatient": random.randint(0, 2),
            "number_diagnoses": random.randint(1, 16),
            "max_glu_serum_encoded": random.randint(0, 3),
            "a1cresult_encoded": random.randint(0, 3),
            "change_encoded": random.randint(0, 1),
            "diabetesmed_encoded": random.randint(0, 1),
            "num_diabetes_meds": random.randint(0, 5)
        }
        
        with self.client.post(
            "/predict",
            json=payload,
            catch_response=True,
            name="predict"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(1)
    def get_model_info(self):
        """Tarea secundaria: consultar info del modelo (peso 1)."""
        with self.client.get("/model/info", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Tarea de health check (peso 1)."""
        self.client.get("/")
