# 🚀 Taller MLflow - Proyecto de Predicción de Credit Score

Este proyecto implementa un flujo completo de **MLOps con MLflow**, incluyendo:

- Base de datos PostgreSQL para almacenar datos de entrenamiento y resultados
- MinIO como backend S3 para almacenar artefactos de modelos
- MLflow Tracking Server + UI para gestionar experimentos y modelos
- JupyterLab para entrenar y registrar modelos
- API robusta con FastAPI para servir predicciones en tiempo real
- pgAdmin y MinIO Console como herramientas de administración

---

## 📦 Estructura del Proyecto

```
.
├── api/                # Código de la API FastAPI
│   └── main.py
├── data/               # Archivos de datos (ej. sample_data.csv)
├── jupyterlab/         # Notebooks de entrenamiento
│   └── notebook.ipynb
├── mlflow/             # Configuración de MLflow server
├── scripts/            # Scripts auxiliares (ej. load_data.py)
├── docker-compose.yml  # Orquestación de servicios
├── .env                # Variables de entorno
└── README.md           # Este archivo
```

---

## ⚙️ Requisitos

- Docker y Docker Compose
- Python 3.9+ (solo si quieres correr notebooks localmente)

---

## 🔑 Variables de Entorno

Archivo `.env`:

```env
# PostgreSQL
POSTGRES_USER=mlflow_user
POSTGRES_PASSWORD=mlflow_pass
POSTGRES_DB=mlflowdb

# MinIO / S3
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=minio123
MLFLOW_S3_ENDPOINT=http://minio:9000
MLFLOW_ARTIFACT_URI=s3://mlflow-artifacts/

# API / MLflow
MLFLOW_MODEL_NAME=CreditScoreModel
MLFLOW_MODEL_STAGE=None
```

---

## ▶️ Ejecución

Levanta todos los servicios:

```bash
docker compose up -d --build
```

Accede a:

- **MLflow UI**: [http://localhost:5000](http://localhost:5000)
- **FastAPI docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **JupyterLab**: [http://localhost:8888](http://localhost:8888)
- **pgAdmin**: [http://localhost:5050](http://localhost:5050)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001)

---

## 🗄️ Carga de Datos

1. Coloca el archivo `sample_data.csv` (con 1000 registros) en `data/`
2. El script `scripts/load_data.py` carga los datos a PostgreSQL:

```bash
docker compose exec jupyterlab python scripts/load_data.py
```

Esto poblará la tabla `credit_data` en la base de datos `mlflowdb`.

---

## 🧠 Entrenamiento de Modelos

1. Abre [JupyterLab](http://localhost:8888)
2. Ejecuta el notebook `jupyterlab/notebook.ipynb`
3. El notebook:
   - Carga los datos desde PostgreSQL
   - Divide en train/val/test
   - Entrena varios modelos con hiperparámetros distintos
   - Compara resultados (`r2`, `rmse`, etc.)
   - Registra runs en MLflow
   - Registra el mejor modelo bajo el nombre `CreditScoreModel`

Ejemplo de registro en el notebook:

```python
mlflow.sklearn.log_model(
    sk_model=model,
    artifact_path="model",
    registered_model_name="CreditScoreModel"
)
```

---

## 🌐 API de Predicción

La API `FastAPI` carga el modelo registrado desde MLflow y expone endpoints REST.

### Endpoints principales

- `POST /predict` → Predice credit score
- `GET /health` → Verifica que el modelo esté cargado
- `GET /info` → Configuración de la API y modelo
- `GET /experiments` → Lista experimentos
- `GET /experiments/{experiment_name}/best_run` → Mejor run de un experimento
- `GET /runs/{run_id}` → Detalles de un run
- `GET /model/latest` → Descarga el modelo

### Ejemplo de petición

```bash
curl -X POST "http://localhost:8000/predict"   -H "Content-Type: application/json"   -d '{
    "age": 35,
    "income": 85000,
    "education_level": "Master"
  }'
```

Respuesta:

```json
{
  "credit_score": 702.15
}
```

---

## 🧪 Obtener el mejor modelo desde MLflow

Ejemplo en un notebook o script:

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()
experiment = client.get_experiment_by_name("CreditScorePrediction")

runs = client.search_runs(
    experiment_ids=[experiment.experiment_id],
    order_by=["metrics.r2 DESC"],
)

best_run = runs[0]
print("Best run ID:", best_run.info.run_id)
print("Metrics:", best_run.data.metrics)
```

---

## 🛠️ Debug & Tips

- Si la API lanza `RESOURCE_DOES_NOT_EXIST`, significa que aún no registraste un modelo con el nombre esperado (`CreditScoreModel`).
- Si falla con `Unable to locate credentials`, revisa las variables de entorno `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, y `MLFLOW_S3_ENDPOINT_URL` en el servicio `api`.
- Para borrar datos y empezar de cero:
  ```bash
  docker compose down -v
  ```

---

## 🛠️ Uso del Makefile

Este proyecto incluye un **Makefile** que simplifica la ejecución de los comandos más comunes de Docker, carga de datos y pruebas de la API.  
En lugar de recordar comandos largos, puedes usar accesos directos con `make`.

### 📋 Principales comandos

- **Levantar servicios**
  ```bash
  make up
  ```
  Inicia todos los contenedores definidos en `docker-compose.yml`.

- **Reconstruir imágenes**
  ```bash
  make build
  ```

- **Detener servicios**
  ```bash
  make down
  ```

- **Ver logs en tiempo real**
  ```bash
  make logs
  ```

- **Reiniciar todo**
  ```bash
  make restart
  ```

- **Resetear base de datos**
  ```bash
  make reset-db
  ```
  Elimina los volúmenes de PostgreSQL y vuelve a crear la base limpia.

- **Resetear almacenamiento MinIO**
  ```bash
  make reset-minio
  ```
  Borra el volumen usado por MinIO.

---

### 📊 Carga de datos

El comando `load-data` carga automáticamente el archivo `data/sample_data.csv` en la base de datos PostgreSQL:

```bash
make load-data
```

Esto ejecuta el script `scripts/load_data.py` dentro del contenedor `jupyterlab`.

---

### 🧑‍💻 Accesos rápidos para desarrollo

- **Abrir JupyterLab**
  ```bash
  make notebook
  ```
  (abre en tu navegador `http://localhost:8888`).

- **Abrir API Docs (Swagger)**
  ```bash
  make api
  ```
  (abre en tu navegador `http://localhost:8000/docs`).

- **Listar notebooks activos**
  ```bash
  make notebook-list
  ```

---

### 🌐 Probar la API

Ejecuta un request de prueba contra el endpoint `/predict`:

```bash
make test-api
```

Ejemplo de respuesta:

```json
{"credit_score": 710.42}
```

---

### 🧹 Limpieza

Para detener todo, borrar volúmenes y liberar espacio:

```bash
make clean
```

---

### ⚠️ Nota Importante sobre el uso de la API

Antes de poder usar la API de predicción (`/predict`), es necesario:

1. **Ejecutar un experimento desde JupyterLab**  
   - Abre [http://localhost:8888](http://localhost:8888)
   - Corre el notebook `jupyterlab/notebook.ipynb`
   - Esto entrenará varios modelos y registrará el mejor en MLflow con el nombre `CreditScoreModel`.

2. **Confirmar que el modelo está registrado en MLflow**  
   - Ingresa a la UI de MLflow: [http://localhost:5000](http://localhost:5000)
   - Verifica que existe un modelo registrado como `CreditScoreModel` en la pestaña **Models**.

3. **Recién entonces usar la API**  
   Una vez registrado, la API podrá cargar el modelo automáticamente y `/predict` funcionará sin errores.

> Si intentas llamar la API sin haber corrido antes el experimento y registrado el modelo, obtendrás un error tipo:  
> `RESOURCE_DOES_NOT_EXIST: Registered Model with name=CreditScoreModel not found`

## 🧪 Flujo de Entrenamiento y Registro de Modelos

En esta solución se implementó un flujo completo de **entrenamiento, experimentación y registro de modelos con MLflow**, asegurando buenas prácticas de MLOps.  

### 🔹 1. Notebook de Entrenamiento
Se creó un notebook (`jupyterlab/notebook.ipynb`) que:
- Conecta a la base de datos PostgreSQL (`mlflowdb`) para leer los datos.
- Preprocesa las variables y asegura que los datos procesados se escriban nuevamente en la base de datos.
- Ejecuta múltiples experimentos de entrenamiento (al menos **20 corridas**), variando hiperparámetros como:
  - Número de árboles y profundidad en RandomForest
  - Diferentes regresores lineales
  - Otras configuraciones de modelos
- Registra cada corrida en **MLflow Tracking Server**, incluyendo:
  - Hiperparámetros
  - Métricas (`r2`, `rmse`, etc.)
  - Artefactos generados (gráficos, modelos serializados, etc.)

### 🔹 2. Persistencia de Datos
- Los **datos crudos** se cargan desde `sample_data.csv` a PostgreSQL con el script `scripts/load_data.py`.
- Los **datos procesados** (ya con transformaciones como one-hot encoding) también se almacenan en PostgreSQL para garantizar reproducibilidad.

### 🔹 3. Registro de Modelos en MLflow
- Una vez completados los experimentos, se selecciona el mejor modelo según métricas de validación.
- Este modelo se registra en el **MLflow Model Registry** bajo el nombre `CreditScoreModel`.
- Ejemplo del registro en el notebook:

```python
import mlflow.sklearn

mlflow.sklearn.log_model(
    sk_model=model,
    artifact_path="model",
    registered_model_name="CreditScoreModel"
)
```

### 🔹 4. Integración con la API
- La API FastAPI (`api/main.py`) carga automáticamente el modelo registrado en MLflow.
- Esto garantiza que cualquier cliente pueda consumir predicciones de manera consistente sin necesidad de reentrenar.
- Si no existe un modelo registrado, la API retornará un error informando que primero se debe entrenar y registrar el modelo.

---
