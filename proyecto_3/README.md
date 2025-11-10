# Proyecto 3: MLOps - Sistema Completo de Predicción de Readmisión de Pacientes Diabéticos

## Descripción

Sistema MLOps completo end-to-end para la predicción de readmisión hospitalaria de pacientes diabéticos. Está listo para despliegue en Kubernetes.

### Componentes Principales

- **Airflow**: Orquestación de pipelines de datos y entrenamiento (3 DAGs completos)
- **MLflow**: Seguimiento de experimentos, registro de modelos y promoción automática a Production
- **PostgreSQL**: Bases de datos separadas para RAW DATA, CLEAN DATA y metadatos de MLflow
- **MinIO**: Almacenamiento de artefactos en bucket S3-compatible
- **FastAPI**: API de inferencia que consume modelos dinámicamente desde MLflow sin cambios de código
- **Streamlit**: Interfaz gráfica de usuario para predicciones
- **Prometheus + Grafana**: Observabilidad y métricas del sistema
- **Locust**: Pruebas de carga y determinación de capacidad máxima
- **Kubernetes**: Manifiestos completos para despliegue en producción

## Arquitectura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Airflow   │────▶│   RAW DATA   │────▶│ CLEAN DATA  │
│ (Orquestador)│     │  (PostgreSQL)│     │ (PostgreSQL)│
└─────────────┘     └──────────────┘     └─────────────┘
       │                                         │
       │                                         ▼
       │                                  ┌─────────────┐
       └─────────────────────────────────▶│   MLflow    │
                                          │ Experiments │
                                          └─────────────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │   MLflow    │
                                          │   Models    │
                                          │(Production) │
                                          └─────────────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐     ┌─────────────┐
                                          │  FastAPI    │────▶│  Streamlit  │
                                          │     API     │     │     UI      │
                                          └─────────────┘     └─────────────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │ Prometheus  │
                                          │  + Grafana  │
                                          └─────────────┘
```

## Estructura del Proyecto

```
proyecto_3/
├── dags/                           # DAGs de Airflow
│   ├── diabetes_data_ingestion.py  # Ingesta de datos en batches
│   ├── diabetes_preprocessing.py   # Preprocesamiento (RAW → CLEAN)
│   └── diabetes_training.py        # Entrenamiento con MLflow
├── initdb/                         # Scripts de inicialización de BD
│   ├── 01_create_tables.sql
│   └── 02_add_row_hash.sql
├── services/                       # Microservicios
│   ├── api/                        # API de inferencia
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── streamlit/                  # UI
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── requirements.txt
│   ├── mlflow/                     # MLflow server
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── locust/                     # Load testing
│       ├── Dockerfile
│       ├── locustfile.py
│       └── requirements.txt
├── config/                         # Configuraciones
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── grafana/
│       └── dashboard.json
├── kubernetes/                     # Manifiestos K8s
│   ├── namespace.yaml
│   ├── pvc.yaml
│   ├── databases.yaml
│   ├── mlflow.yaml
│   ├── api.yaml
│   ├── streamlit.yaml
│   └── observability.yaml
├── docker-compose.yml              # Orquestación con Docker
├── .env.example                    # Variables de entorno
└── README.md                       # Este archivo
```

## Despliegue

### Opción 1: Docker Compose


#### Pasos

1. **Clonar y configurar:**
```bash
cd proyecto_3
cp .env.example .env
# Editar .env si es necesario
```

2. **Construir y levantar servicios:**
```bash
docker-compose up --build -d
```

3. **Verificar servicios:**
```bash
docker-compose ps
```

4. **Acceder a interfaces:**
- Airflow: http://localhost:8080 (user: `airflow`, pass: `airflow`)
- MLflow: http://localhost:5000
- API: http://localhost:8000
- Streamlit: http://localhost:8501
- Grafana: http://localhost:3000 (user: `admin`, pass: `admin`)
- Prometheus: http://localhost:9090
- MinIO Console: http://localhost:9011 (user: `minioadmin`, pass: `minioadmin`)
- Locust: http://localhost:8089

### Opción 2: Kubernetes (Producción)

#### Prerrequisitos
- Cluster de Kubernetes (minikube, k3s, o cloud provider)
- kubectl configurado
- Imágenes Docker construidas y pusheadas a registry

#### Pasos

1. **Construir imágenes:**
```bash
# API
cd services/api
docker build -t diabetes-api:latest .

# Streamlit
cd ../streamlit
docker build -t diabetes-streamlit:latest .

# MLflow
cd ../mlflow
docker build -t mlflow-diabetes:latest .
```

2. **Pushear a registry**
```bash
docker tag diabetes-api:latest <your-registry>/diabetes-api:latest
docker push <your-registry>/diabetes-api:latest
# Repetir para las demás imágenes
```

3. **Desplegar en Kubernetes:**
```bash
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/pvc.yaml
kubectl apply -f kubernetes/databases.yaml
kubectl apply -f kubernetes/mlflow.yaml
kubectl apply -f kubernetes/api.yaml
kubectl apply -f kubernetes/streamlit.yaml
kubectl apply -f kubernetes/observability.yaml
```

4. **Verificar pods:**
```bash
kubectl get pods -n mlops-diabetes
```

5. **Obtener IPs externas:**
```bash
kubectl get svc -n mlops-diabetes
```

## Flujo de Trabajo

### 1. Ingesta de Datos
El DAG `diabetes_data_ingestion` descarga el dataset de diabetes y lo carga en lotes de 15,000 registros:
- Descarga automática desde URL de Google Drive
- División en train (70%), validation (15%), test (15%)
- Carga en **batches** del conjunto de entrenamiento (requisito del proyecto)
- Almacenamiento en tabla `diabetes_raw`

**Ejecutar manualmente:**
```bash
# En Airflow UI: DAGs > diabetes_data_ingestion > Trigger DAG
```

### 2. Preprocesamiento
El DAG `diabetes_preprocessing` limpia y transforma los datos:
- Conversión de rangos de edad a valores numéricos
- Encoding de variables categóricas
- Feature engineering (conteo de medicamentos, etc.)
- Almacenamiento en tabla `diabetes_clean`

**Ejecutar:**
```bash
# En Airflow UI: DAGs > diabetes_preprocessing > Trigger DAG
```

### 3. Entrenamiento
El DAG `diabetes_training` entrena múltiples modelos:
- Logistic Regression
- Random Forest
- Gradient Boosting
- Registro de experimentos en MLflow
- **Promoción automática del mejor modelo a Production**

**Ejecutar:**
```bash
# En Airflow UI: DAGs > diabetes_training > Trigger DAG
```

### 4. Inferencia
La API consume automáticamente el modelo en stage `Production`:
- No requiere cambios de código para actualizar modelo
- Expone endpoint `/predict` para predicciones
- Métricas de Prometheus en `/metrics`

### 5. Monitoreo
Grafana muestra dashboards con:
- Total de requests
- Predicciones por versión de modelo
- Latencia de requests
- Errores

### 6. Pruebas de Carga
Locust permite determinar capacidad máxima:
1. Acceder a http://localhost:8089
2. Configurar usuarios (ej: 100 users, 10 spawn rate)
3. Ejecutar pruebas y analizar resultados

## Dataset

**Diabetes 130-US Hospitals (1999-2008)**
- 101,766 registros de pacientes diabéticos
- 50+ features clínicas
- Target: readmitted (NO, <30, >30 días)



## Testing

### Probar API manualmente:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "age_numeric": 55,
    "time_in_hospital": 3,
    "num_lab_procedures": 45,
    "num_procedures": 1,
    "num_medications": 15,
    "number_outpatient": 0,
    "number_emergency": 0,
    "number_inpatient": 0,
    "number_diagnoses": 9,
    "max_glu_serum_encoded": 0,
    "a1cresult_encoded": 0,
    "change_encoded": 1,
    "diabetesmed_encoded": 1,
    "num_diabetes_meds": 2
  }'
```

### Verificar modelo en MLflow:
```bash
curl http://localhost:5000/api/2.0/mlflow/registered-models/search
```

## Troubleshooting

### Problema: Contenedores no inician
```bash
# Ver logs
docker-compose logs -f <servicio>

# Reiniciar servicio específico
docker-compose restart <servicio>
```

### Problema: MLflow no encuentra modelo
```bash
# Verificar modelos registrados
docker-compose exec mlflow mlflow models list

# Recargar modelo en API
curl -X POST http://localhost:8000/reload-model
```

### Problema: DAGs no aparecen en Airflow
```bash
# Verificar montaje de volumen
docker-compose exec airflow-webserver ls /opt/airflow/dags

# Refrescar DAGs
docker-compose restart airflow-scheduler
```

## Notas de Implementación

### Decisiones Técnicas

1. **LocalExecutor en Airflow**: Para simplicidad, en producción usar CeleryExecutor
2. **MinIO en lugar de S3**: Compatible con S3, más fácil para desarrollo local
3. **2 bases PostgreSQL**: Separación conceptual de RAW y CLEAN data
4. **LabelEncoder para target**: Simplifica clasificación multiclase
5. **StandardScaler**: Mejora convergencia de modelos



## Autores

Proyecto 3 de MLOps - Operaciones de Aprendizaje de Máquina

Daniel Rios
Miguel Granados
Sebastian Fanchi


