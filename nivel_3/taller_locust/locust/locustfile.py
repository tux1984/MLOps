"""
Script de pruebas de carga con Locust para la API de inferencia.

Este script simula usuarios realizando peticiones de predicción a la API.
"""
from locust import HttpUser, task, between
import random


class MLInferenceUser(HttpUser):
    """
    Simula un usuario realizando peticiones a la API de inferencia.
    """
    # Tiempo de espera entre peticiones (entre 1 y 3 segundos)
    wait_time = between(1, 3)
    
    def on_start(self):
        """
        Se ejecuta cuando un usuario inicia.
        Verifica que la API esté disponible.
        """
        response = self.client.get("/health")
        if response.status_code != 200:
            print("⚠️ Advertencia: API no está saludable")
    
    @task(10)
    def predict_iris(self):
        """
        Tarea principal: realizar predicciones.
        
        Esta tarea tiene un peso de 10, lo que significa que se ejecutará
        10 veces más frecuentemente que otras tareas.
        """
        # Generar características aleatorias (simulando datos de Iris)
        # Iris dataset típico:
        # - Sepal length: 4.3 - 7.9
        # - Sepal width: 2.0 - 4.4
        # - Petal length: 1.0 - 6.9
        # - Petal width: 0.1 - 2.5
        features = [
            round(random.uniform(4.3, 7.9), 1),  # sepal length
            round(random.uniform(2.0, 4.4), 1),  # sepal width
            round(random.uniform(1.0, 6.9), 1),  # petal length
            round(random.uniform(0.1, 2.5), 1),  # petal width
        ]
        
        payload = {
            "features": features
        }
        
        with self.client.post(
            "/predict",
            json=payload,
            catch_response=True,
            name="/predict"
        ) as response:
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    # Validar que la respuesta tenga los campos esperados
                    if "prediction" in json_response and "probabilities" in json_response:
                        response.success()
                    else:
                        response.failure("Respuesta inválida: faltan campos esperados")
                except Exception as e:
                    response.failure(f"Error al parsear respuesta: {e}")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(2)
    def health_check(self):
        """
        Tarea secundaria: verificar el estado de la API.
        
        Esta tarea tiene un peso de 2, se ejecuta menos frecuentemente.
        """
        self.client.get("/health", name="/health")
    
    @task(1)
    def get_root(self):
        """
        Tarea ocasional: acceder al endpoint raíz.
        """
        self.client.get("/", name="/")


class MLInferenceHeavyLoadUser(HttpUser):
    """
    Usuario para pruebas de carga pesada.
    Hace peticiones más frecuentes sin tiempo de espera.
    """
    wait_time = between(0.1, 0.5)  # Espera muy corta entre peticiones
    
    @task
    def predict_continuous(self):
        """Realizar predicciones continuas."""
        features = [
            round(random.uniform(4.3, 7.9), 1),
            round(random.uniform(2.0, 4.4), 1),
            round(random.uniform(1.0, 6.9), 1),
            round(random.uniform(0.1, 2.5), 1),
        ]
        
        self.client.post(
            "/predict",
            json={"features": features},
            name="/predict"
        )


# Comentarios sobre configuración de Locust:
#
# Para ejecutar Locust con los parámetros del taller:
#
# locust -f locustfile.py --host=http://localhost:8000 \
#        --users=10000 \
#        --spawn-rate=500 \
#        --run-time=5m \
#        --headless
#
# Parámetros:
# - --users: Número máximo de usuarios simultáneos (10,000)
# - --spawn-rate: Usuarios agregados por segundo (500)
# - --run-time: Duración de la prueba
# - --headless: Modo sin interfaz gráfica (opcional)
#
# Para usar la interfaz web (recomendado):
# locust -f locustfile.py --host=http://localhost:8000
# Luego abrir: http://localhost:8089

