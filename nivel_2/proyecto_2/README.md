# Proyecto MLOps - Orquestación, Métricas y Modelos

Este repositorio contiene una implementación completa del entorno solicitado en el proyecto de MLOps: orquestación con **Airflow**, gestión de experimentos con **MLflow**, almacenamiento de artefactos en **MinIO**, base de metadatos dedicada y un servicio de inferencia construido con **FastAPI**. Se provee todo el código e infraestructura necesaria para ejecutar la solución con `docker compose`.

## Arquitectura

Servicios principales que se levantan con `docker compose up --build -d`:

- **Airflow** (webserver, scheduler, worker, triggerer, CLI): orquesta la obtención de datos, el preprocesamiento y el entrenamiento de modelos. Se utiliza CeleryExecutor con Redis como broker y PostgreSQL como metadata store.
- **PostgreSQL (db)**: almacena los datos crudos obtenidos de la API externa en la tabla `forest_cover_samples`.
- **MLflow Tracking Server**: expone la UI y API para gestionar experimentos y el Model Registry. Usa MySQL como backend store y MinIO para los artefactos.
- **MinIO**: almacenamiento S3-compatible donde MLflow guarda artefactos (modelos, métricas, metadata).
- **MySQL (`mlflow-db`)**: backend para metadatos de MLflow.
- **FastAPI (`inference`)**: servicio de inferencia que consume siempre la última versión en `Production` del modelo registrado en MLflow.
- **Redis y PostgreSQL (Airflow)**: dependencias internas de Airflow.

Componentes compartidos:

- `./shared`: volumen con snapshots de datos preprocesados y artefactos auxiliares.
- `docker/airflow`: imagen custom de Airflow con dependencias de ciencia de datos y MLflow instaladas para evitar reinicios por fallos en `pip`.
- `docker/mlflow`: imagen ligera para correr el servidor de MLflow.
- `services/inference`: servicio FastAPI para inferencia con MLflow Model Registry.

## Estructura del repositorio

```
.
├── dags/                        # DAGs de Airflow
│   ├── data_ingestion_pipeline.py
│   └── forest_ml_pipeline.py
├── docker/airflow/              # Imagen base de Airflow + requirements
├── docker/mlflow/               # Imagen del tracking server
├── services/inference/          # API de inferencia (FastAPI)
├── initdb/                      # Scripts SQL para PostgreSQL de aplicación
├── shared/                      # Volumen compartido (datos y artefactos)
├── docker-compose.yml
├── .env.example
└── README.md
```

## Configuración

1. Clona el repositorio y copia el archivo de variables de entorno:
   ```bash
   cp .env.example .env
   ```
2. Ajusta los valores según necesidades. Variables relevantes:
   - `SOURCE_API_BASE_URL` y `GROUP_NUMBER`: API externa para ingesta.
   - Credenciales de PostgreSQL (`POSTGRES_*`).
   - Credenciales de MinIO (`MINIO_ROOT_*`), bucket (`MLFLOW_S3_BUCKET`) y credenciales que usarán Airflow/MLflow/FastAPI (`MLFLOW_S3_ACCESS_KEY`, `MLFLOW_S3_SECRET_KEY`).
   - Parámetros de MLflow (`MLFLOW_TRACKING_URI`, `MLFLOW_EXPERIMENT_NAME`, `MLFLOW_MODEL_NAME`).
- `MLFLOW_ENABLE_MODEL_REGISTRY`: habilita el uso del Model Registry (por defecto "false" para servir desde el último run).

En Linux se recomienda actualizar `AIRFLOW_UID` con el resultado de `id -u`.

## Puesta en marcha

```bash
docker compose up --build -d
```

La primera ejecución construye las imágenes personalizadas e inicializa bases de datos y buckets. Servicios disponibles:

- Airflow UI: http://localhost:8080 (usuario y contraseña definidos en `.env`).
- MLflow UI: http://localhost:5000
- MinIO Console: http://localhost:9001
- FastAPI Inference: http://localhost:8000 (documentación interactiva Swagger en `/docs`).

> Nota: el `docker-compose.yml` se mantuvo deliberadamente sencillo y no incluye healthchecks avanzados. Después de levantar los servicios verifica su estado con `docker compose ps` o revisa logs específicos (`docker compose logs <servicio>`) antes de habilitar los DAGs.

### Orden de encendido

La composición inicia los servicios en orden básico (bases de datos → MinIO → MLflow → Airflow/inferencia). El contenedor `minio-create-buckets` espera de forma simple a que MinIO responda antes de crear el bucket por defecto. Si algún servicio tarda más de lo esperado, consulta sus logs puntuales y reinícialo con `docker compose restart <servicio>`.

## DAGs disponibles

### `forest_cover_data_pipeline`
- Solicita una muestra al endpoint `/data` cada 3 minutos.
- Deduplica, persiste en PostgreSQL y genera un CSV con la última captura.

### `forest_training_pipeline`
- Corre cada 15 minutos.
- **`preprocess_forest_data`**: limpia nulos, tipifica columnas, asegura presencia de columnas requeridas y guarda snapshot parquet.
- **`train_forest_models`**: entrena Logistic Regression, Random Forest y SVC usando un pipeline con `ColumnTransformer` que maneja imputación + OneHot en categorías. Registra métricas en MLflow, guarda artefactos, selecciona el mejor modelo por `f1_macro`, lo registra en el Model Registry y lo promueve a `Production` archivando versiones previas.

Los `XCom` de entrenamiento exponen el modelo campeón y la versión registrada.

## MLflow y MinIO

- Experimento por defecto: `forest-cover-experiment` (configurable por env var).
- Los artefactos y modelos se guardan en el bucket `mlflow-artifacts` de MinIO.
- Backend store en `mlflow-db` (MySQL).
- Para consultar métricas/modelos: http://localhost:5000.

## Servicio de inferencia

- Endpoint `GET /health`: estado general.
- Endpoint `GET /metadata`: versión del modelo en producción y columnas esperadas.
- Endpoint `POST /predict`: recibe un arreglo `samples` con las 12 features originales (numéricas + categóricas) y devuelve predicciones enteras de `cover_type`.
- Endpoint `POST /reload`: invalida la caché y recarga el modelo en caliente.

El servicio utiliza `mlflow.pyfunc.load_model("models:/<MODEL_NAME>/Production")`, por lo que siempre atiende con la versión promovida a `Production`.
Si el Model Registry está deshabilitado (`MLFLOW_ENABLE_MODEL_REGISTRY=false`), el entrenamiento deja un archivo `shared/models/latest_model.json` con el `run_id` más reciente y la API carga el modelo directo desde ese run.

Ejemplo de petición:

```bash
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{
        "samples": [
          {
            "elevation": 2596,
            "aspect": 51,
            "slope": 3,
            "horizontal_distance_to_hydrology": 258,
            "vertical_distance_to_hydrology": 0,
            "horizontal_distance_to_roadways": 510,
            "hillshade_9am": 221,
            "hillshade_noon": 232,
            "hillshade_3pm": 148,
            "horizontal_distance_to_fire_points": 6279,
            "wilderness_area": "cache",
            "soil_type": "c2702"
          }
        ]
      }'
```

## Solución al problema de reinicios en Airflow

Inicialmente los contenedores de Airflow entraban en bucle porque intentaban instalar `scikit-learn` y otras dependencias en tiempo de ejecución. La nueva imagen en `docker/airflow` instala todas las librerías (scikit-learn, mlflow, pyarrow, etc.) durante la construcción, lo que estabiliza el arranque de todos los servicios.

## Operación y monitoreo

- Logs de Airflow: carpeta `./logs` o en la UI.
- Datos preprocesados: `shared/forest_cover_preprocessed_<timestamp>.parquet`.
- Bucket MinIO: usar la consola o `mc` para inspeccionar artefactos.
- MySQL/PostgreSQL: se pueden inspeccionar conectándose a los contenedores (`docker compose exec`).

## Próximos pasos sugeridos

1. Añadir pruebas unitarias y de integración para los módulos reutilizables (p. ej. pruebas del preprocesamiento y del pipeline de entrenamiento mediante `pytest`).
2. Integrar un pipeline CI/CD (GitHub Actions o similar) para lint, pruebas y build de imágenes.
3. Versionar notebooks o scripts de análisis exploratorio en `shared/notebooks/`.
4. Implementar la interfaz (Streamlit/Gradio) solicitada en el bonus reutilizando el endpoint del servicio de inferencia.
5. Configurar observabilidad adicional: paneles en Grafana/Prometheus o alerting sobre fallos de DAGs.
