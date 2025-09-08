# MLOps Nivel 2 — Penguins Pipeline + Serving

Proyecto de MLOps con orquestación en Airflow, almacenamiento en Postgres, entrenamiento de modelos con scikit‑learn y un servicio FastAPI para inferencia, todo levantado con Docker Compose. Dataset: seaborn “penguins” (clasificación de especie).

## Resumen

- Orquesta un pipeline de ML con Airflow: ingesta → preprocesado → entrenamiento.
- Persiste datos en Postgres (servicio `db`) y metadata de Airflow en otro Postgres (servicio `postgres`).
- Sirve inferencia con FastAPI consumiendo artefactos `.pkl` generados por el entrenamiento.
- Todo se levanta con Docker Compose y un volumen compartido `shared/models`.

## Arquitectura

- **Airflow**: `airflow-webserver`, `airflow-scheduler`, `airflow-worker`, `airflow-triggerer`, `airflow-init`, con Redis y Postgres para su backend (Celery + metadatos).
- **Postgres app (`db`)**: almacena tablas del dataset (`penguins`, `penguins_preprocessed`).
- **FastAPI (`api`)**: expone `/models`, `/predict`, `/predict/compare`.
- **Volúmenes**:
  - `./dags` → `/opt/airflow/dags`
  - `./logs` → `/opt/airflow/logs`
  - `./plugins` → `/opt/airflow/plugins`
  - `./shared` → `/shared` (aquí van los modelos `.pkl`)

### Servicios y puertos

- Airflow UI: `http://localhost:8080` (usuario/clave: `airflow`/`airflow`)
- FastAPI: `http://localhost:8000` (documentación en `/docs` y `/redoc`)
- Postgres app: `localhost:5432` (db: `appdb`, user: `app`, pass: `secret`)

## Variables importantes

- En DAGs (inyectadas por `docker-compose.yaml`): `APP_DB_HOST=db`, `APP_DB_PORT=5432`, `APP_DB_NAME=appdb`, `APP_DB_USER=app`, `APP_DB_PASSWORD=secret`.
- Paquetes extra para contenedores de Airflow definidos en `.env` vía `_PIP_ADDITIONAL_REQUIREMENTS` (seaborn, pandas, psycopg2-binary, scikit‑learn).

## Estructura del repositorio

- `docker-compose.yaml`: orquesta todos los servicios y monta volúmenes.
- `dags/`
  - `dags/penguins_ingest.py`: carga dataset seaborn “penguins” a Postgres (`penguins`).
  - `dags/penguins_preprocess.py`: limpia y hace one‑hot, escribe `penguins_preprocessed`.
  - `dags/penguins_train.py`: entrena 3 modelos, hace GridSearch y guarda artefactos en `/shared/models`.
- `api/`
  - `api/main.py`: FastAPI con endpoints de inferencia.
  - `api/schemas.py`: contratos de entrada/salida (Pydantic).
  - `api/helpers.py`: preprocesa entradas igual que en entrenamiento (reindex).
  - `api/model_loader.py`: localiza y carga bundles `.pkl`.
  - `api/requirements.uv.txt`, `api/Dockerfile`: dependencias y build de la API.
- `shared/models/`: artefactos generados (`random_forest.pkl`, `logistic_regression.pkl`, `svc.pkl`).
- `.env`: credenciales de DB app y paquetes adicionales para Airflow.
- `initdb/`: scripts opcionales de inicialización para la DB de la app.
- `plugins/`, `logs/`: extensiones y logs de Airflow.

## Paso a paso: Puesta en marcha

1. Preparar entorno
   - Requisitos: Docker y Docker Compose.
   - Revisa `.env` (DB app y paquetes de Python).
2. Levantar servicios
   - `docker compose up -d --build`
   - Verifica salud: `docker compose ps`
3. Inicializar y acceder a Airflow
   - El servicio `airflow-init` corre automáticamente (crea DB de Airflow, usuario web).
   - Abre `http://localhost:8080` e inicia sesión (`airflow`/`airflow`).
4. Activar y ejecutar DAGs
   - Despausa `penguins_ingest` (cada 30s) o ejecútalo manualmente.
   - Despausa `penguins_preprocess` (cada 1 min) si quieres snapshot limpio adicional.
   - Despausa `penguins_train` (cada 5 min) o ejecútalo manualmente para generar artefactos.
5. Verificar artefactos y API
   - `ls -l shared/models` debe mostrar `random_forest.pkl`, `logistic_regression.pkl`, `svc.pkl`.
   - GET `http://localhost:8000/models` lista los modelos disponibles.

## Paso a paso: Pipeline de datos y modelos

### Ingesta — `dags/penguins_ingest.py`

- Fuente: `seaborn.load_dataset("penguins")`.
- Conexión a BD por `APP_DB_*`.
- Escribe snapshot en tabla `penguins`, reemplazando en cada corrida (evita duplicados).
- Programación: cada 30 segundos.

### Preprocesado — `dags/penguins_preprocess.py`

- Lee `penguins`, elimina nulos y aplica one‑hot a `species`, `island`, `sex`.
- Escribe `penguins_preprocessed` (tabla limpia de referencia).
- Programación: cada 1 minuto.

### Entrenamiento — `dags/penguins_train.py`

- Lee `penguins` y aplica su propio preprocesamiento consistente con la API de serving:
  - Elimina nulos.
  - `LabelEncoder` para `species` (target 0/1/2).
  - `pd.get_dummies(drop_first=True)` para features categóricas.
- Split: train/test 80/20 (`random_state=42`).
- Modelos y búsqueda de hiperparámetros (GridSearchCV, `cv=3`):
  - `logistic_regression`: `C=[0.1, 1.0, 10.0]`, `max_iter=1000`.
  - `random_forest`: `n_estimators=[50, 100]`.
  - `svc`: `probability=True`, `C=[0.1, 1.0]`, `kernel=["linear", "rbf"]`.
- Métricas: imprime `classification_report` en logs del task.
- Artefactos (“bundles”) guardados en `/shared/models/{name}.pkl` con:
  - `model`: mejor estimador (GridSearchCV).
  - `label_encoder`: para decodificar clases.
  - `feature_columns`: columnas exactas de entrenamiento (sirven al serving para reindexar y evitar drift).
- Programación: cada 5 minutos.

> Nota: aunque existe `penguins_preprocessed`, el entrenamiento actual lee `penguins` y se autoconsistente en su preprocesamiento. Esto permite a la API replicar exactamente el pipeline con `feature_columns`.

## Servicio de inferencia (FastAPI)

- Listar modelos: GET `/models` → lista `.pkl` en `/shared/models`.
- Inferencia con un modelo: POST `/predict` (query opcional `model=<nombre>` o en body `model`; por defecto `random_forest.pkl`).
- Comparar múltiples modelos: POST `/predict/compare` (query `models=name&models=...`).

### Esquema de entrada

Body (`PredictRequest`) con lista de registros:

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

- `api/helpers.py` aplica one‑hot a `island` y `sex` con `drop_first=True` y reindexa a `feature_columns` del bundle. Si el estimador expone `feature_names_in_`, se usa esa referencia.
- `api/model_loader.py` busca en `/shared/models` y carga el bundle con `joblib`.

## Comandos de uso rápido

- Levantar todo: `docker compose up -d --build`
- Ver logs API: `docker compose logs -f fastapi`
- Ver logs de tareas: en Airflow UI o `logs/`.

Ejemplos `curl`:

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


## Verificación end‑to‑end

1. Trigger manual de `penguins_ingest` → verifica filas en `penguins`.
2. Trigger `penguins_train` → espera finalización y revisa `shared/models` y logs del task.
3. Verifica FastAPI:
   - GET `/models` lista `.pkl`.
   - POST `/predict` devuelve `predictions` y, si aplica, `probabilities` y `classes`.

## Decisiones técnicas y rationale

- Airflow 2.6.0 con CeleryExecutor: simula distribución y separa responsabilidades.
- Dos Postgres:
  - `postgres`: metadata de Airflow.
  - `db`: base de datos de la aplicación para datasets/tablas (facilita limpieza y control).
- Bundle de artefactos:
  - Guardar `label_encoder` y `feature_columns` junto al `model` simplifica el serving y evita inconsistencias de features.
- Preprocesamiento reproducible:
  - Entrenamiento y serving comparten estrategia (get_dummies + reindex), reduciendo errores por columnas faltantes o distinto orden.

## Problemas comunes y soluciones

- No aparecen modelos en `/models`:
  - Asegúrate de que corrió `penguins_train` y que `shared` está montado en webserver/worker y en la API.
- Error “No existe el modelo”:
  - `api/model_loader.py` busca `<nombre>.pkl`. Usa `random_forest`, `logistic_regression` o `svc` (con o sin `.pkl`).
- Tareas de Airflow no corren:
  - Revisa recursos Docker (≥ 4 GB RAM, 2 CPU), healthy checks en compose, y que `_PIP_ADDITIONAL_REQUIREMENTS` instaló dependencias.
- Conexión a DB:
  - Verifica variables `APP_DB_*` y la salud del servicio `db`.

## Cómo extender

- Usar `penguins_preprocessed` como input del entrenamiento si deseas mayor separación entre etapas.
- Registrar experimentos y artefactos en MLflow.
- Validación de datos con Great Expectations antes de entrenar.
- Versionado y promoción de modelos (staging/prod) y “modelo por defecto” en la API.
- Añadir tests unitarios para helpers y endpoints (contratos Pydantic y preprocesamiento).
