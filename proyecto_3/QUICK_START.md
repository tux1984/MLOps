# Guía Rápida de Despliegue

## Inicio Rápido (5 minutos)

### 1. Preparación

Copiar el archivo de variables de entorno:

```bash
cd proyecto_3
copy .env.example .env
```

El archivo `.env` contiene todas las configuraciones necesarias:

```env
# Airflow
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow

# RAW Database
RAW_DB_HOST=db-raw
RAW_DB_PORT=5432
RAW_DB_NAME=rawdb
RAW_DB_USER=postgres
RAW_DB_PASSWORD=postgres

# CLEAN Database
CLEAN_DB_HOST=db-clean
CLEAN_DB_PORT=5432
CLEAN_DB_NAME=cleandb
CLEAN_DB_USER=postgres
CLEAN_DB_PASSWORD=postgres

# MLflow Metadata Database
MLFLOW_DB_HOST=postgres-mlflow
MLFLOW_DB_PORT=5432
MLFLOW_DB_NAME=mlflowdb
MLFLOW_DB_USER=mlflow
MLFLOW_DB_PASSWORD=mlflow

# MinIO (S3 Bucket)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_API_PORT=9010
MINIO_CONSOLE_PORT=9011
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin

# MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_BACKEND_STORE_URI=postgresql://mlflow:mlflow@postgres-mlflow:5432/mlflowdb
MLFLOW_ARTIFACT_ROOT=s3://mlflow/
MLFLOW_S3_ENDPOINT_URL=http://minio:9000

# API
MODEL_NAME_PREFIX=diabetes
API_PORT=8000

# Streamlit
STREAMLIT_PORT=8501

# Observability
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# Locust
LOCUST_PORT=8089

# Shared
SHARED_DIR=/shared
```

### 2. Construir y levantar servicios

```bash
docker-compose up --build -d
```

### 3. Verificar servicios

```bash
docker-compose ps
```

Todos los servicios deben estar en estado "Up" y "healthy".

### 4. Acceder a interfaces

- **Airflow**: http://localhost:8080 (user: `airflow`, pass: `airflow`)
- **MLflow**: http://localhost:5000
- **API**: http://localhost:8000
- **Streamlit**: http://localhost:8501
- **Grafana**: http://localhost:3000 (user: `admin`, pass: `admin`)
- **Prometheus**: http://localhost:9090
- **MinIO Console**: http://localhost:9011 (user: `minioadmin`, pass: `minioadmin`)
- **Locust**: http://localhost:8089

## Flujo Completo de Ejecución

### Paso 1: Ingesta de Datos

1. Abrir Airflow UI (http://localhost:8080)
2. Login: `airflow` / `airflow`
3. Buscar el DAG `diabetes_data_ingestion`
4. Activar el toggle (ON)
5. Click en "Trigger DAG" (icono de play)
6. Esperar 5-10 minutos (descarga y procesa 101,766 registros en batches de 15k)

### Paso 2: Preprocesamiento

1. En Airflow UI
2. Buscar el DAG `diabetes_preprocessing`
3. Activar el toggle (ON)
4. Click en "Trigger DAG"
5. Esperar 2-3 minutos (transforma RAW a CLEAN data)

### Paso 3: Entrenamiento de Modelos

1. En Airflow UI
2. Buscar el DAG `diabetes_training`
3. Activar el toggle (ON)
4. Click en "Trigger DAG"
5. Esperar 5-10 minutos (entrena 3 modelos: LogisticRegression, RandomForest, GradientBoosting)
6. El mejor modelo se promueve automáticamente a "Production" en MLflow

### Paso 4: Verificar Experimentos en MLflow

1. Abrir MLflow UI (http://localhost:5000)
2. Ver experimento `diabetes_readmission_prediction`
3. Comparar métricas de los 3 modelos
4. Ir a pestaña "Models" para ver modelos registrados
5. Verificar que el mejor modelo está en stage "Production"

### Paso 5: Hacer Predicciones

1. Abrir Streamlit UI (http://localhost:8501)
2. Completar el formulario con datos del paciente:
   - Edad: 55
   - Tiempo en hospital: 3
   - Procedimientos de laboratorio: 45
   - Medicamentos: 15
   - Diagnósticos: 9
   - etc.
3. Click en "Realizar Predicción"
4. Ver resultado y versión del modelo utilizado

### Paso 6: Configurar Monitoreo en Grafana

1. Abrir Grafana UI (http://localhost:3000)
2. Login: `admin` / `admin`
3. Ir a Connections > Data sources
4. Click en "Add data source"
5. Seleccionar "Prometheus"
6. Configurar:
   - URL: `http://prometheus:9090`
   - Click en "Save & Test"
7. Crear dashboard:
   - Ir a Dashboards > New > New Dashboard
   - Agregar paneles con queries como:
     - `rate(api_requests_total[1m])` - Request rate
     - `histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))` - Latency P95
     - `sum(predictions_total)` - Total predictions

### Paso 7: Pruebas de Carga con Locust

1. Abrir Locust UI (http://localhost:8089)
2. Configurar:
   - Number of users: 100
   - Spawn rate: 10
   - Host: http://api:8000
3. Click en "Start swarming"
4. Observar resultados en tiempo real
5. Analizar métricas:
   - RPS (requests/segundo)
   - Latencia (mediana, P95, P99)
   - Tasa de errores

## Comandos Útiles

### Ver logs de un servicio específico

```bash
docker-compose logs -f <servicio>
# Ejemplo:
docker-compose logs -f api
docker-compose logs -f mlflow
docker-compose logs -f airflow-scheduler
```

### Reiniciar un servicio

```bash
docker-compose restart <servicio>
# Ejemplo:
docker-compose restart api
```

### Detener todos los servicios

```bash
docker-compose down
```

### Detener y eliminar volúmenes (reset completo)

```bash
docker-compose down -v
```

### Ver uso de recursos

```bash
docker stats
```

### Probar API directamente con curl

```bash
curl -X POST http://localhost:8000/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"age_numeric\":55,\"time_in_hospital\":3,\"num_lab_procedures\":45,\"num_procedures\":1,\"num_medications\":15,\"number_outpatient\":0,\"number_emergency\":0,\"number_inpatient\":0,\"number_diagnoses\":9,\"max_glu_serum_encoded\":0,\"a1cresult_encoded\":0,\"change_encoded\":1,\"diabetesmed_encoded\":1,\"num_diabetes_meds\":2}"
```

### Ver información del modelo cargado en la API

```bash
curl http://localhost:8000/model/info
```

### Verificar datos en PostgreSQL

```bash
# RAW database
docker exec -it db-raw psql -U postgres -d rawdb -c "SELECT COUNT(*) FROM diabetes_raw;"

# CLEAN database
docker exec -it db-clean psql -U postgres -d cleandb -c "SELECT COUNT(*) FROM diabetes_clean;"
```

## Solución de Problemas

### Servicios no inician correctamente

1. Verificar logs:
```bash
docker-compose logs
```

2. Verificar que no hay conflictos de puertos:
```bash
netstat -ano | findstr :8080
netstat -ano | findstr :5000
```

3. Reintentar:
```bash
docker-compose down
docker-compose up -d
```

### MLflow no encuentra el modelo

1. Verificar que el DAG de training se ejecutó correctamente
2. Verificar modelos registrados en MLflow UI
3. Recargar modelo en la API:
```bash
curl -X POST http://localhost:8000/reload-model
```

### DAGs no aparecen en Airflow

1. Verificar que el volumen está montado correctamente:
```bash
docker-compose exec airflow-webserver ls /opt/airflow/dags
```

2. Reiniciar scheduler:
```bash
docker-compose restart airflow-scheduler
```

3. Esperar 30 segundos y refrescar la página de Airflow UI

### Permisos de volúmenes en Windows

Si hay problemas con permisos de volúmenes compartidos:

1. Verificar que Docker Desktop tiene acceso a la unidad C:
   - Docker Desktop > Settings > Resources > File Sharing
2. Reiniciar Docker Desktop
3. Volver a ejecutar `docker-compose up`

## Checklist Pre-Entrega

- [ ] Todos los servicios en estado "Up" y "healthy"
- [ ] DAG `diabetes_data_ingestion` ejecutado exitosamente
- [ ] DAG `diabetes_preprocessing` ejecutado exitosamente
- [ ] DAG `diabetes_training` ejecutado exitosamente
- [ ] Modelo en stage "Production" en MLflow
- [ ] API respondiendo correctamente (probar /predict y /model/info)
- [ ] Streamlit UI funcional y muestra versión del modelo
- [ ] Prometheus recolectando métricas de la API
- [ ] Grafana configurado con Prometheus como data source
- [ ] Dashboard de Grafana creado con al menos 3 paneles
- [ ] Locust ejecutado con 100 usuarios concurrentes
- [ ] Resultados de Locust documentados (RPS, latencia, errores)
- [ ] Código en repositorio público de GitHub
- [ ] README completo con instrucciones
- [ ] Manifiestos de Kubernetes listos
- [ ] Video de sustentación (máximo 10 minutos)

## Métricas Clave a Reportar

### Datos
- Total registros procesados: 101,766
- Split: train (71,236 / 70%), validation (15,265 / 15%), test (15,265 / 15%)
- Batches de ingesta: 7 batches de 15k para training

### Modelos
- Modelos entrenados: 3 (Logistic Regression, Random Forest, Gradient Boosting)
- Modelo en Production: Logistic Regression
- Métricas del mejor modelo:
  - Accuracy: 57.11%
  - Precision: 54.77%
  - Recall: 57.11%
  - F1-Score: 49.46%

### Performance de la API
- Throughput: 50.6 requests/segundo
- Latencia mediana: 7ms
- Latencia P95: 14ms
- Latencia P99: 57ms
- Tasa de error: 0%

### Capacidad del Sistema
- Usuarios concurrentes probados: 100
- Total requests en prueba: 2,973
- Estabilidad: 0% failures bajo carga
- No se observó degradación con 100 usuarios concurrentes


## Flujo Completo de Ejecución

### Paso 1: Ingesta de Datos

1. Abrir Airflow UI (http://localhost:8080)
2. Login: `airflow` / `airflow`
3. Buscar el DAG `diabetes_data_ingestion`
4. Activar el toggle (ON)
5. Click en "Trigger DAG" (icono de play)
6. Esperar 5-10 minutos (descarga y procesa 101,766 registros en batches de 15k)

### Paso 2: Preprocesamiento

1. En Airflow UI
2. Buscar el DAG `diabetes_preprocessing`
3. Activar el toggle (ON)
4. Click en "Trigger DAG"
5. Esperar 2-3 minutos (transforma RAW a CLEAN data)

### Paso 3: Entrenamiento de Modelos

1. En Airflow UI
2. Buscar el DAG `diabetes_training`
3. Activar el toggle (ON)
4. Click en "Trigger DAG"
5. Esperar 5-10 minutos (entrena 3 modelos: LogisticRegression, RandomForest, GradientBoosting)
6. El mejor modelo se promueve automáticamente a "Production" en MLflow

### Paso 4: Verificar Experimentos en MLflow

1. Abrir MLflow UI (http://localhost:5000)
2. Ver experimento `diabetes_readmission_prediction`
3. Comparar métricas de los 3 modelos
4. Ir a pestaña "Models" para ver modelos registrados
5. Verificar que el mejor modelo está en stage "Production"

### Paso 5: Hacer Predicciones

1. Abrir Streamlit UI (http://localhost:8501)
2. Completar el formulario con datos del paciente:
   - Edad: 55
   - Tiempo en hospital: 3
   - Procedimientos de laboratorio: 45
   - Medicamentos: 15
   - Diagnósticos: 9
   - etc.
3. Click en "Realizar Predicción"
4. Ver resultado y versión del modelo utilizado

### Paso 6: Configurar Monitoreo en Grafana

1. Abrir Grafana UI (http://localhost:3000)
2. Login: `admin` / `admin`
3. Ir a Connections > Data sources
4. Click en "Add data source"
5. Seleccionar "Prometheus"
6. Configurar:
   - URL: `http://prometheus:9090`
   - Click en "Save & Test"
7. Crear dashboard:
   - Ir a Dashboards > New > New Dashboard
   - Agregar paneles con queries como:
     - `rate(api_requests_total[1m])` - Request rate
     - `histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))` - Latency P95
     - `sum(predictions_total)` - Total predictions

### Paso 7: Pruebas de Carga con Locust

1. Abrir Locust UI (http://localhost:8089)
2. Configurar:
   - Number of users: 100
   - Spawn rate: 10
   - Host: http://api:8000
3. Click en "Start swarming"
4. Observar resultados en tiempo real
5. Analizar métricas:
   - RPS (requests/segundo)
   - Latencia (mediana, P95, P99)
   - Tasa de errores
- [ ] Video de sustentación (máximo 10 minutos)

## Métricas Clave a Reportar

### Datos
- Total registros procesados: 101,766
- Split: train (71,236 / 70%), validation (15,265 / 15%), test (15,265 / 15%)
- Batches de ingesta: 7 batches de 15k para training

### Modelos
- Modelos entrenados: 3 (Logistic Regression, Random Forest, Gradient Boosting)
- Modelo en Production: Logistic Regression
- Métricas del mejor modelo:
  - Accuracy: 57.11%
  - Precision: 54.77%
  - Recall: 57.11%
  - F1-Score: 49.46%

### Performance de la API
- Throughput: 50.6 requests/segundo
- Latencia mediana: 7ms
- Latencia P95: 14ms
- Latencia P99: 57ms
- Tasa de error: 0%

### Capacidad del Sistema
- Usuarios concurrentes probados: 100
- Total requests en prueba: 2,973
- Estabilidad: 0% failures bajo carga
- No se observó degradación con 100 usuarios concurrentes
