# Proyecto MLOps – Ingesta, Entrenamiento e Inferencia de Cobertura Forestal

Este repositorio implementa un entorno completo de MLOps para el proyecto de clasificación de cobertura forestal del curso. La solución automatiza la ingesta de datos, el preprocesamiento, el entrenamiento y la entrega del modelo mediante **Airflow**, **MLflow**, **MinIO**, **FastAPI** y una **interfaz Streamlit**. Todo el ecosistema se despliega con **Docker Compose** para garantizar portabilidad y reproducibilidad.

---

## Tabla de contenidos
- [Proyecto MLOps – Ingesta, Entrenamiento e Inferencia de Cobertura Forestal](#proyecto-mlops--ingesta-entrenamiento-e-inferencia-de-cobertura-forestal)
  - [Tabla de contenidos](#tabla-de-contenidos)
  - [Arquitectura general](#arquitectura-general)
  - [Estructura del repositorio](#estructura-del-repositorio)
    - [Archivos destacados](#archivos-destacados)
  - [Requisitos previos](#requisitos-previos)
  - [Configuración inicial](#configuración-inicial)
  - [Puesta en marcha](#puesta-en-marcha)
  - [Servicios incluidos](#servicios-incluidos)
  - [DAGs de Airflow](#dags-de-airflow)
    - [`forest_cover_data_pipeline`](#forest_cover_data_pipeline)
    - [`forest_training_pipeline`](#forest_training_pipeline)
  - [Flujo de modelo e inferencia](#flujo-de-modelo-e-inferencia)
  - [Interfaz Streamlit](#interfaz-streamlit)
  - [Operación cotidiana](#operación-cotidiana)
  - [Solución de problemas frecuentes](#solución-de-problemas-frecuentes)
  - [Próximos pasos sugeridos](#próximos-pasos-sugeridos)

---

## Arquitectura general
```
API externa ──► Airflow (DAGs) ──► PostgreSQL (datos crudos)
       │                             │
       │                             ▼
       │                       shared/ (artefactos)
       │                             │
       └────────► MLflow Tracking ───┼──► MinIO (artefactos)
                                     │
                                     ├──► FastAPI (API de inferencia)
                                     └──► Streamlit (interfaz interactiva)
```
- **Airflow** coordina ingesta, limpieza y entrenamiento.
- **MLflow** registra parámetros, métricas, artefactos y modelos.
- **MinIO** actúa como almacenamiento S3-compatible para artefactos.
- **FastAPI** sirve predicciones consumiendo el modelo vigente.
- **Streamlit** proporciona una interfaz web para usuarios finales y analistas.

---

## Estructura del repositorio
```
.
├── dags/                       # DAGs de Airflow
│   ├── data_ingestion_pipeline.py
│   └── forest_ml_pipeline.py
├── docker/
│   ├── airflow/                # Imagen base + dependencias de Airflow
│   └── mlflow/                 # Imagen del tracking server
├── services/
│   ├── inference/              # Servicio FastAPI
│   └── streamlit/              # Interfaz Streamlit
├── initdb/                     # Scripts SQL para la BD de aplicación
├── shared/                     # Artefactos compartidos (datasets, modelos)
├── docker-compose.yml
├── .env.example
└── README.md
```

### Archivos destacados
- `docker-compose.yml`: define los servicios y redes del proyecto.
- `dags/data_ingestion_pipeline.py`: pipeline de ingesta desde la API externa.
- `dags/forest_ml_pipeline.py`: preprocesamiento, entrenamiento y registro en MLflow.
- `services/inference/app/main.py`: API de inferencia.
- `services/streamlit/app/main.py`: aplicación web para usuarios finales.

---

## Requisitos previos
- Docker ≥ 20.10 y Docker Compose ≥ 2 instalados.
- Al menos 6 GB de RAM libre para ejecutar la pila completa.
- Puertos disponibles: `8080` (Airflow), `5000` (MLflow), `8000` (FastAPI), `8501` (Streamlit), `9000/9001` (MinIO), `5432` y `3306` para bases de datos.

---

## Configuración inicial
1. Clonar el repositorio y crear el archivo `.env` a partir del ejemplo:
   ```bash
   git clone <URL-del-repositorio>
   cd proyecto_2
   cp .env.example .env
   ```
2. Ajustar el `.env`:
   - `AIRFLOW_UID`: en Linux, establecer `id -u` para evitar problemas de permisos.
   - `SOURCE_API_BASE_URL` y `GROUP_NUMBER`: parámetros de la API externa.
   - Credenciales para `POSTGRES_*`, `MINIO_ROOT_*`, `MLFLOW_*`.
   - `MLFLOW_ENABLE_MODEL_REGISTRY`: `true` para usar Model Registry, `false` para servir el último `run`.
   - Opcional: `INFERENCE_API_URL`, `MLFLOW_URL` y otros parámetros consumidos por Streamlit.

---

## Puesta en marcha
```bash
docker compose build --parallel
docker compose up -d
```
La primera ejecución construye las imágenes personalizadas, inicializa las bases y crea el bucket de MinIO.

Comprobar estado:
```bash
docker compose ps
```

Servicios disponibles:
- Airflow UI: <http://localhost:8080>
- MLflow UI: <http://localhost:5000>
- MinIO Console: <http://localhost:9001>
- FastAPI: <http://localhost:8000/docs>
- Streamlit: <http://localhost:8501>

---

## Servicios incluidos
| Servicio        | Imagen base                          | Descripción                                                |
|-----------------|--------------------------------------|------------------------------------------------------------|
| `airflow-*`     | `docker/airflow/`                    | Orquesta DAGs de ingesta y entrenamiento                    |
| `db`            | `postgres:16`                        | Base de datos de aplicación (datos crudos y preprocesados)  |
| `postgres`      | `postgres:13`                        | Metadata de Airflow                                         |
| `redis`         | `redis:latest`                       | Broker Celery                                               |
| `mlflow`        | `docker/mlflow/`                     | Tracking server + Model Registry                            |
| `mlflow-db`     | `mysql:8.0`                          | Metadata de MLflow                                          |
| `minio`         | `quay.io/minio/minio`                | Almacenamiento de artefactos S3-compatible                  |
| `inference`     | `services/inference/`                | API FastAPI que sirve el modelo activo                      |
| `streamlit`     | `services/streamlit/`                | Interfaz web para usuarios finales                          |
| `minio-create-buckets` | `quay.io/minio/mc`           | Inicializa el bucket de artefactos                          |

---

## DAGs de Airflow
### `forest_cover_data_pipeline`
- Frecuencia: cada 5 minutos.
- Pasos:
  1. `fetch_data`: descarga un lote desde la API externa y lo guarda en `shared/`.
  2. `load_postgres`: transforma, valida y escribe en `forest_cover_samples` con deduplicación.
  3. `log_summary`: muestra resumen del lote en logs de Airflow.

### `forest_training_pipeline`
- Frecuencia: cada 15 minutos.
- Pasos:
  1. `preprocess_forest_data`: limpia datos, genera variables categóricas codificadas e inserta `forest_cover_preprocessed`.
  2. `train_forest_models`: entrena `LogisticRegression`, `RandomForest` y `SVC`, registra en MLflow y publica el mejor modelo. Genera el archivo `shared/models/latest_model.json` con el estado actual.

> Habilita los DAGs en la UI de Airflow y lanza una corrida manual para validar el pipeline.

---

## Flujo de modelo e inferencia
1. Airflow ingesta y guarda datos crudos en PostgreSQL.
2. El DAG de entrenamiento preprocesa, entrena y registra modelos en MLflow.
3. El mejor modelo queda almacenado en MLflow y su estado se refleja en `shared/models/latest_model.json`.
4. FastAPI carga el modelo:
   - Si `MLFLOW_ENABLE_MODEL_REGISTRY=true`: `models:/<nombre>/Production`.
   - De lo contrario: `runs:/<run_id>/model` usando la metadata local.
5. La API expone `/health`, `/metadata`, `/predict`, `/reload` para consumo de clientes y Streamlit.

---

## Interfaz Streamlit
La aplicación Streamlit (servicio `streamlit`) agrega una capa visual para usuarios de negocio:
- **Inicio**: descripción del proyecto, métricas rápidas y tipos de cobertura.
- **Predicciones**: formularios para predicción individual, lotes editables y carga de CSV.
- **Analíticas**: gráficos interactivos (Plotly) para explorar correlaciones y distribuciones.
- **Información del modelo**: metadatos, métricas y enlace directo a MLflow.
- **Configuración**: permite verificar conectividad y personalizar opciones.

Para ejecutarla:
```bash
docker compose up -d streamlit
```
Luego abrir <http://localhost:8501>.

**CSV de ejemplo** para predicciones en batch:
```csv
elevation,aspect,slope,horizontal_distance_to_hydrology,vertical_distance_to_hydrology,horizontal_distance_to_roadways,hillshade_9am,hillshade_noon,hillshade_3pm,horizontal_distance_to_fire_points,wilderness_area,soil_type
2596,51,3,258,0,510,211,232,148,6279,Rawah,C7745
3052,80,4,170,38,85,225,232,142,716,Rawah,C7201
```

---

## Operación cotidiana
- Ver estado de contenedores: `docker compose ps`.
- Revisar logs: `docker compose logs <servicio> --tail 100`.
- Reentrenar manualmente: activar DAGs en Airflow y pulsar *Trigger DAG*.
- Recargar API tras un nuevo modelo: `docker compose restart inference` o POST `/reload`.
- Iniciar Streamlit si no está activo: `docker compose up -d streamlit`.

---

## Solución de problemas frecuentes
| Incidencia | Causa probable | Acción recomendada |
|------------|----------------|--------------------|
| **MLflow**: `Detected out-of-date database schema` | Base MySQL con esquema anterior | `docker compose run --rm --entrypoint "" mlflow mlflow db upgrade mysql+pymysql://...` y luego `docker compose up -d mlflow` |
| **FastAPI**: `numpy.dtype size changed` | Modelo entrenado con versiones distintas de `numpy`/`sklearn` | Reconstruir imágenes (`airflow` + `inference`), borrar `shared/models/latest_model.json`, reejecutar `forest_training_pipeline` |
| **Streamlit**: API desconectada | Servicio de inferencia detenido o URL incorrecta | `docker compose restart inference` y validar `INFERENCE_API_URL` |
| **Permisos de archivos** en `shared/`/`logs/` | Propiedad `root` tras ejecución en Docker | `sudo chown -R $(id -u):$(id -g) shared logs` |
| **Migraciones MLflow** recurrentes | Base `mlflow-db` quedó dañada | Respaldar (`mysqldump`), `docker compose down -v` y levantar de nuevo |

---

## Próximos pasos sugeridos
1. **Automatizar pruebas** (unitarias e integración) para DAGs y API de inferencia.
2. **Integrar CI/CD** con GitHub Actions o similar para lint + pruebas + build automatizado.
3. **Observabilidad**: añadir Prometheus/Grafana y alertas sobre fallos de DAGs o métricas del modelo.
4. **Versionado de datos**: incorporar herramientas como DVC o LakeFS.
5. **Orquestación avanzada**: habilitar notificaciones (Slack/Teams) cuando se promueva un modelo o fallen ejecuciones.
6. **Seguridad y despliegue**: asegurar accesos con HTTPS, autenticación en FastAPI y despliegues en Kubernetes u orquestadores administrados.

---
