# MLOps Nivel 2 — Penguins Pipeline + Serving

En este proyecto construí un pipeline de MLOps que orquesta ingesta, preprocesado y entrenamiento con Airflow; persiste datos en Postgres; y sirve inferencia con FastAPI consumiendo artefactos de scikit‑learn. Todo lo levanto con Docker Compose. El dataset es “penguins” de seaborn (clasificación de especies).

## Resumen

- Orquesto el pipeline de ML en Airflow: ingesta → preprocesado → entrenamiento.
- Persisto datos en Postgres (servicio `db`) y la metadata de Airflow en otro Postgres (servicio `postgres`).
- Sirvo inferencia con FastAPI usando los artefactos `.pkl` generados durante el entrenamiento.
- Utilizo un volumen compartido `shared/models` para conectar entrenamiento y serving.

## Arquitectura

- Uso **Airflow** con `airflow-webserver`, `airflow-scheduler`, `airflow-worker`, `airflow-triggerer` y `airflow-init`, respaldado por Redis (broker Celery) y Postgres (metadatos de Airflow).
- Mantengo un **Postgres de aplicación (`db`)** para las tablas del dataset (`penguins`, `penguins_preprocessed`).
- Expongo una **API FastAPI (`api`)** con `/models`, `/predict` y `/predict/compare`.
- **Volúmenes** que monto:
  - `./dags` → `/opt/airflow/dags`
  - `./logs` → `/opt/airflow/logs`
  - `./plugins` → `/opt/airflow/plugins`
  - `./shared` → `/shared` (aquí dejo los modelos `.pkl`)

### Servicios y puertos

- Airflow UI: `http://localhost:8080` (usuario/clave: `airflow`/`airflow`)
- FastAPI: `http://localhost:8000` (documentación en `/docs` y `/redoc`)
- Postgres app: `localhost:5432` (db: `appdb`, user: `app`, pass: `secret`)

## Variables importantes

- En mis DAGs (inyectadas por `docker-compose.yaml`) uso `APP_DB_HOST=db`, `APP_DB_PORT=5432`, `APP_DB_NAME=appdb`, `APP_DB_USER=app`, `APP_DB_PASSWORD=secret`.
- Defino paquetes extra para los contenedores de Airflow en `.env` con `_PIP_ADDITIONAL_REQUIREMENTS` (seaborn, pandas, psycopg2-binary, scikit‑learn).

## Estructura del repositorio

- `docker-compose.yaml`: orquesto todos los servicios y monto los volúmenes.
- `dags/`
  - `dags/penguins_ingest.py`: cargo el dataset seaborn “penguins” a Postgres (`penguins`).
  - `dags/penguins_preprocess.py`: limpio y hago one‑hot, escribiendo `penguins_preprocessed`.
  - `dags/penguins_train.py`: entreno 3 modelos, hago GridSearch y guardo artefactos en `/shared/models`.
- `api/`
  - `api/main.py`: implemento FastAPI con endpoints de inferencia.
  - `api/schemas.py`: defino contratos de entrada/salida (Pydantic).
  - `api/helpers.py`: replico el preprocesamiento del entrenamiento (reindex a `feature_columns`).
  - `api/model_loader.py`: localizo y cargo bundles `.pkl`.
  - `api/requirements.uv.txt`, `api/Dockerfile`: dependencias y build de la API.
- `shared/models/`: artefactos generados (`random_forest.pkl`, `logistic_regression.pkl`, `svc.pkl`).
- `.env`: credenciales de DB app y paquetes adicionales para Airflow.
- `initdb/`: scripts opcionales para inicializar la DB de la app.
- `plugins/`, `logs/`: extensiones y logs de Airflow.

## Paso a paso: Puesta en marcha

1. Preparo el entorno
   - Requisitos: Docker y Docker Compose.
   - Reviso `.env` (DB app y paquetes de Python).
2. Levanto los servicios
   - `docker compose up -d --build`
   - Verifico salud: `docker compose ps`
3. Inicializo y accedo a Airflow
   - Dejo que `airflow-init` corra automáticamente (crea DB de Airflow y usuario web).
   - Abro `http://localhost:8080` e inicio sesión (`airflow`/`airflow`).
4. Activo y ejecuto los DAGs
   - Despauso `penguins_ingest` (cada 30s) o lo ejecuto manualmente.
   - Despauso `penguins_preprocess` (cada 1 min) si quiero un snapshot limpio adicional.
   - Despauso `penguins_train` (cada 5 min) o lo ejecuto manualmente para generar artefactos.
5. Verifico artefactos y API
   - `ls -l shared/models` debe mostrar `random_forest.pkl`, `logistic_regression.pkl`, `svc.pkl`.
   - GET `http://localhost:8000/models` lista los modelos disponibles.

## Paso a paso: Pipeline de datos y modelos

### Ingesta — `dags/penguins_ingest.py`

- Uso `seaborn.load_dataset("penguins")` como fuente.
- Me conecto a la BD con `APP_DB_*`.
- Escribo un snapshot en `penguins` reemplazándolo en cada corrida (evito duplicados).
- Programo el DAG cada 30 segundos.

### Preprocesado — `dags/penguins_preprocess.py`

- Leo `penguins`, elimino nulos y aplico one‑hot a `species`, `island`, `sex`.
- Guardo `penguins_preprocessed` como tabla limpia de referencia.
- Programo el DAG cada 1 minuto.

### Entrenamiento — `dags/penguins_train.py`

- Leo `penguins` y aplico un preprocesamiento consistente con mi API de serving:
  - Elimino nulos.
  - Aplico `LabelEncoder` a `species` (target 0/1/2).
  - Hago `pd.get_dummies(drop_first=True)` para las categóricas en features.
- Hago split train/test 80/20 (`random_state=42`).
- Entreno con GridSearchCV (`cv=3`):
  - `logistic_regression`: `C=[0.1, 1.0, 10.0]`, `max_iter=1000`.
  - `random_forest`: `n_estimators=[50, 100]`.
  - `svc`: `probability=True`, `C=[0.1, 1.0]`, `kernel=["linear", "rbf"]`.
- Reporto métricas con `classification_report` en los logs del task.
- Guardo “bundles” en `/shared/models/{name}.pkl` con:
  - `model`: mejor estimador (GridSearchCV).
  - `label_encoder`: para decodificar clases.
  - `feature_columns`: columnas exactas de entrenamiento (las uso en serving para reindexar y evitar drift).
- Programo este DAG cada 5 minutos.

> Nota: aunque tengo `penguins_preprocessed`, el entrenamiento actual lee `penguins` y es autoconsistente en su preprocesamiento. Así la API puede replicar exactamente el pipeline usando `feature_columns`.

## Servicio de inferencia (FastAPI)

- Listo modelos: GET `/models` → `.pkl` en `/shared/models`.
- Predigo con un modelo: POST `/predict` (query opcional `model=<nombre>` o en body `model`; por defecto uso `random_forest.pkl`).
- Comparo múltiples modelos: POST `/predict/compare` (query `models=name&models=...`).

### Esquema de entrada

Envio un `PredictRequest` con una lista de registros:

```json
{
  "records": [
    {
      "bill_length_mm": 39.1,
      "bill_depth_mm": 18.7,
      "flipper_length_mm": 181,
      "body_mass_g": 3750,
      "island": "Biscoe",
      "sex": "male"
    }
  ]
}
```

### Preprocesamiento en serving

- En `api/helpers.py` aplico one‑hot a `island` y `sex` con `drop_first=True` y reindexo a `feature_columns` del bundle. Si el estimador expone `feature_names_in_`, priorizo esa referencia.
- En `api/model_loader.py` busco en `/shared/models` y cargo el bundle con `joblib`.

## Comandos de uso rápido

- Levanto todo: `docker compose up -d --build`
- Veo logs de la API: `docker compose logs -f fastapi`
- Consulto logs de tareas: en la UI de Airflow o en `logs/`.

Ejemplos `curl` que uso:

- Listar modelos: `curl http://localhost:8000/models`
- Predecir (default):
  ```bash
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"records":[{"bill_length_mm":39.1,"bill_depth_mm":18.7,"flipper_length_mm":181,"body_mass_g":3750,"island":"Biscoe","sex":"male"}]}'
  ```
- Predecir con `svc`:
  ```bash
  curl -X POST "http://localhost:8000/predict?model=svc" \
    -H "Content-Type: application/json" \
    -d '{"records":[{"bill_length_mm":39.1,"bill_depth_mm":18.7,"flipper_length_mm":181,"body_mass_g":3750,"island":"Biscoe","sex":"male"}]}'
  ```
- Comparar modelos:
  ```bash
  curl -X POST "http://localhost:8000/predict/compare?models=random_forest&models=logistic_regression&models=svc" \
    -H "Content-Type: application/json" \
    -d '{"records":[{"bill_length_mm":39.1,"bill_depth_mm":18.7,"flipper_length_mm":181,"body_mass_g":3750,"island":"Biscoe","sex":"male"}]}'
  ```

Para consultar tablas en el Postgres de la app:

```bash
docker compose exec -T db psql -U app -d appdb -c "SELECT count(*) FROM penguins;"
docker compose exec -T db psql -U app -d appdb -c "\dt"
```

## Verificación end‑to‑end

1. Hago trigger manual de `penguins_ingest` y verifico filas en `penguins`.
2. Hago trigger de `penguins_train`, espero finalización y reviso `shared/models` y los logs del task.
3. Verifico FastAPI:
   - GET `/models` lista `.pkl`.
   - POST `/predict` devuelve `predictions` y, si aplica, `probabilities` y `classes`.

## Decisiones técnicas y rationale

- Uso Airflow 2.6.0 con CeleryExecutor para simular un entorno distribuido y separar responsabilidades.
- Mantengo dos Postgres:
  - `postgres`: metadata de Airflow.
  - `db`: base de datos de la aplicación para datasets/tablas (facilita limpieza y control).
- Empaqueto el artefacto como bundle:
  - Guardo `label_encoder` y `feature_columns` junto al `model` para simplificar el serving y evitar inconsistencias de features.
- Hago preprocesamiento reproducible:
  - Entrenamiento y serving comparten estrategia (get_dummies + reindex), reduciendo errores por columnas faltantes o distinto orden.

## Problemas comunes y cómo los resuelvo

- No aparecen modelos en `/models`:
  - Verifico que corrió `penguins_train` y que `shared` está montado en webserver/worker y en la API.
- Error “No existe el modelo”:
  - `api/model_loader.py` busca `<nombre>.pkl`. Uso `random_forest`, `logistic_regression` o `svc` (con o sin `.pkl`).
- Tareas de Airflow no corren:
  - Reviso recursos Docker (≥ 4 GB RAM, 2 CPU), healthy checks en compose, y que `_PIP_ADDITIONAL_REQUIREMENTS` instaló dependencias.
- Conexión a DB:
  - Verifico variables `APP_DB_*` y la salud del servicio `db`.

