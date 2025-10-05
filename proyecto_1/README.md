# Proyecto MLOps - Airflow para ingesta de datos

Este repositorio contiene una configuración mínima basada en Docker Compose para ejecutar Airflow y orquestar la ingesta de datos desde la **Data API del Proyecto 2** (grupo 8). El objetivo es recolectar las porciones de dataset que expone el endpoint `/data` y almacenarlas en una base de datos PostgreSQL para su posterior procesamiento/modelado.

## Componentes levantados

- **Airflow** (`airflow-webserver`, `airflow-scheduler`, `airflow-worker`, `airflow-triggerer`, `airflow-cli` y perfil opcional `flower`): orquesta y ejecuta el DAG que consulta la API externa.
- **PostgreSQL (Airflow)** (`postgres`): almacena la metadata interna de Airflow.
- **PostgreSQL de aplicación** (`db`): recibe los registros recolectados de la API en la tabla `forest_cover_samples`.
- **Redis (`redis`)**: broker requerido por el `CeleryExecutor`.

Los servicios comparten el directorio `./shared` para guardar copias de los lotes descargados (`.json` y `.csv`) y permitir su inspección fuera de Airflow.

## Estructura del proyecto

```
.
├── dags/                     # DAGs de Airflow (forest_cover_data_pipeline.py)
├── initdb/                   # Scripts SQL para la base de datos de aplicación
├── logs/                     # Logs locales de Airflow
├── plugins/                  # Plugins personalizados (vacío por defecto)
├── shared/                   # Volumen compartido con snapshots de datos
├── docker-compose.yml
├── .env.example
└── README.md
```

## Configuración inicial

1. Crea tu archivo `.env` a partir del ejemplo y ajusta las variables necesarias:
   ```bash
   cp .env.example .env
   # Edita .env si quieres cambiar credenciales, grupo u origen de la API
   ```
2. (Opcional en Linux) reemplaza `AIRFLOW_UID` por el resultado de `id -u` para evitar problemas de permisos.

Variables principales:
- `SOURCE_API_BASE_URL`: URL base de la Data API (`http://10.43.100.103:8080`).
- `GROUP_NUMBER`: número de grupo asignado (8).
- Credenciales de la base PostgreSQL de aplicación (`POSTGRES_*`).

## Puesta en marcha

1. Construye y levanta los contenedores:
   ```bash
   docker compose up --build -d
   ```
2. Espera a que `airflow-init` finalice; esto creará el usuario admin (por defecto `airflow`/`airflow`).
3. Interfaces disponibles:
   - Airflow UI: http://localhost:8080
   - Flower (opcional, si se ejecuta con `--profile flower`): http://localhost:5555
   - PostgreSQL de aplicación: disponible en `localhost:5432` (credenciales de `.env`).

## DAG `forest_cover_data_pipeline`

El DAG corre cada 3 minutos (`*/3 * * * *`) y sigue estos pasos:

1. **`fetch_data`**: realiza una petición GET a `SOURCE_API_BASE_URL/data` con el `group_number` configurado (un solo intento por ejecución). El lote recibido se guarda en `shared/group{N}_batch{M}_<timestamp>.json` y se publican metadatos en XCom.
2. **`load_postgres`**: transforma las filas en un `DataFrame`, elimina duplicados y calcula un hash único por fila antes de insertarlas en `forest_cover_samples`; también genera un CSV actualizado (`shared/forest_cover_latest.csv`).
3. **`log_summary`**: deja un resumen de filas descargadas, deduplicadas e insertadas (incluye cuántas se omitieron por existir previamente).

La tabla de destino se crea automáticamente al iniciar PostgreSQL mediante `initdb/01_create_tables.sql`. Sus columnas corresponden al orden suministrado por la API:

- `elevation`, `aspect`, `slope`, `horizontal_distance_to_hydrology`,
- `vertical_distance_to_hydrology`, `horizontal_distance_to_roadways`,
- `hillshade_9am`, `hillshade_noon`, `hillshade_3pm`, `horizontal_distance_to_fire_points`,
- `wilderness_area`, `soil_type`, `cover_type`.

Cada registro también almacena `group_number`, `batch_number`, `row_hash` (clave única) e `ingested_at`.


## Nuevos DAGs de preprocesamiento y entrenamiento

- `forest_preprocess`: cada 5 minutos toma `forest_cover_samples`, elimina nulos, codifica variables categóricas (`wilderness_area`, `soil_type`) y guarda una versión lista para modelado en la tabla `forest_cover_preprocessed`.
- `forest_train`: cada 15 minutos lee la tabla preprocesada, normaliza los atributos y entrena tres clasificadores (Logistic Regression, Random Forest, SVC) realizando búsqueda de hiperparámetros. Los artefactos se guardan en `shared/models/forest/` como archivos `.joblib` junto con el `StandardScaler` y las columnas usadas.

Para que estos DAGs funcionen, asegúrate de que el DAG de ingesta (`forest_cover_data_pipeline`) esté activo para mantener la tabla origen actualizada. Si el entorno de Airflow ya está levantado, reinicia los contenedores tras actualizar `_PIP_ADDITIONAL_REQUIREMENTS` para instalar `scikit-learn` y `seaborn`.

## Operación y pruebas

- Habilita el DAG en la UI de Airflow y gatilla una ejecución manual para verificar conectividad a la API y escritura en la base.
- Revisa `shared/` para inspeccionar el JSON y el CSV más recientes.
- Para depurar, puedes conectarte a la base de aplicación:
  ```bash
  psql -h localhost -U app -d appdb -c 'SELECT COUNT(*) FROM forest_cover_samples;'
  ```

## Detener y limpiar

```bash
docker compose down
# Añade -v si quieres eliminar los volúmenes persistentes (bases de datos).
# docker compose down -v
```

Esta configuración constituye la base de Airflow. Puedes extenderla posteriormente con MLflow, MinIO u otros servicios conforme avance el proyecto.
