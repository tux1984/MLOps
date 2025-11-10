# Arquitectura Técnica Detallada - Proyecto 3

## 🏛️ Visión General

Este documento describe la arquitectura técnica completa del sistema MLOps para predicción de readmisión de pacientes diabéticos.

## 📐 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CAPA DE PRESENTACIÓN                        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐          ┌──────────────┐         ┌─────────────┐│
│  │  Streamlit   │◄─────────┤   Grafana    │◄────────┤   Locust    ││
│  │      UI      │  HTTP    │  Dashboard   │  HTTP   │  Load Test  ││
│  │  (Port 8501) │          │ (Port 3000)  │         │ (Port 8089) ││
│  └──────┬───────┘          └──────┬───────┘         └─────────────┘│
└─────────┼──────────────────────────┼───────────────────────────────┘
          │                          │
          │ HTTP                     │ Metrics
          │                          │
┌─────────▼──────────────────────────▼───────────────────────────────┐
│                        CAPA DE SERVICIOS                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐              ┌───────────────────┐           │
│  │   FastAPI API    │◄─────────────┤   Prometheus      │           │
│  │  Inference API   │   Scraping   │  Metrics Store    │           │
│  │   (Port 8000)    │   /metrics   │   (Port 9090)     │           │
│  └────────┬─────────┘              └───────────────────┘           │
│           │                                                          │
│           │ Load Model                                              │
│           │                                                          │
│  ┌────────▼─────────┐                                               │
│  │     MLflow       │                                               │
│  │  Tracking Server │                                               │
│  │   (Port 5000)    │                                               │
│  └────────┬─────────┘                                               │
│           │                                                          │
│           ├──────────┬──────────────┐                               │
│           │          │              │                               │
└───────────┼──────────┼──────────────┼───────────────────────────────┘
            │          │              │
            │          │              │
┌───────────▼──────────▼──────────────▼───────────────────────────────┐
│                    CAPA DE ALMACENAMIENTO                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐  │
│  │  PostgreSQL  │  │    MinIO     │  │   PostgreSQL (RAW)      │  │
│  │   MLflow     │  │   S3 Bucket  │  │   - diabetes_raw        │  │
│  │  Metadata    │  │  Artifacts   │  │   - Split: train/val/test│ │
│  │ (Port 5432)  │  │(Port 9000/1) │  │   (Port 5433)           │  │
│  └──────────────┘  └──────────────┘  └─────────────────────────┘  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐                                │
│  │ PostgreSQL   │  │  PostgreSQL  │                                │
│  │   (CLEAN)    │  │   Airflow    │                                │
│  │ - diabetes_  │  │   Metadata   │                                │
│  │   clean      │  │ (Internal)   │                                │
│  │ (Port 5434)  │  └──────────────┘                                │
│  └──────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
            ▲
            │
┌───────────┴─────────────────────────────────────────────────────────┐
│                    CAPA DE ORQUESTACIÓN                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Apache Airflow                            │  │
│  │                     (Port 8080)                              │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐ │  │
│  │ │ Data Ingestion │→ │Preprocessing │→ │    Training      │ │  │
│  │ │      DAG       │  │     DAG      │  │       DAG        │ │  │
│  │ └────────────────┘  └──────────────┘  └──────────────────┘ │  │
│  │   • Download CSV     • RAW → CLEAN    • Train Models      │  │
│  │   • Split data       • Feature Eng    • Log to MLflow     │  │
│  │   • Batch loading    • Encoding       • Auto-promote      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 Flujo de Datos Detallado

### 1. Ingesta de Datos (DAG: diabetes_data_ingestion)

```
┌─────────────┐
│ Google Drive│
│  Dataset    │
└──────┬──────┘
       │ Download (requests)
       ▼
┌─────────────┐
│  Airflow    │
│ Worker Pod  │
└──────┬──────┘
       │ sklearn.train_test_split
       │ 70% train, 15% val, 15% test
       ▼
┌─────────────┐
│ Batch Split │
│ 15k records │
└──────┬──────┘
       │ 7 batches (train)
       │ 1 batch (validation)
       │ 1 batch (test)
       ▼
┌─────────────────┐
│  PostgreSQL     │
│  diabetes_raw   │
│  - batch_number │
│  - split_type   │
│  - row_hash     │
└─────────────────┘
```

**Detalles técnicos:**
- **Paralelización**: Batches se cargan concurrentemente (Airflow tasks)
- **Idempotencia**: `row_hash` previene duplicados
- **Atomicidad**: Cada batch es una transacción separada

### 2. Preprocesamiento (DAG: diabetes_preprocessing)

```
┌─────────────────┐
│  diabetes_raw   │
└────────┬────────┘
         │ Read all splits
         ▼
┌────────────────────┐
│  Transformation    │
│  Engine (pandas)   │
├────────────────────┤
│ • Age encoding     │
│ • Categorical enc  │
│ • Feature eng      │
│ • Null handling    │
└────────┬───────────┘
         │ Cleaned features
         ▼
┌─────────────────┐
│ diabetes_clean  │
│ Ready for ML    │
└─────────────────┘
```

**Features generados:**
- `age_numeric`: Conversión de rangos a valores
- `num_diabetes_meds`: Conteo de medicamentos específicos
- `*_encoded`: One-hot encoding de categóricas

### 3. Entrenamiento (DAG: diabetes_training)

```
┌─────────────────┐
│ diabetes_clean  │
│ (train split)   │
└────────┬────────┘
         │ Load & Scale
         ▼
┌─────────────────────┐
│ StandardScaler      │
│ LabelEncoder        │
└────────┬────────────┘
         │
         ├──────────┬──────────┬──────────┐
         ▼          ▼          ▼          ▼
    ┌───────┐  ┌───────┐  ┌───────┐
    │LogReg │  │RandomF│  │GradBst│
    └───┬───┘  └───┬───┘  └───┬───┘
        │          │          │
        └──────────┴──────────┘
                   │ Log experiments
                   ▼
            ┌──────────────┐
            │   MLflow     │
            │  Tracking    │
            └──────┬───────┘
                   │ Save artifacts
                   ▼
            ┌──────────────┐
            │    MinIO     │
            │ s3://mlflow/ │
            └──────────────┘
                   │
                   │ Best F1-score
                   ▼
            ┌──────────────┐
            │  Production  │
            │   Staging    │
            └──────────────┘
```

**Criterio de selección:**
- Métrica principal: **F1-Score weighted**
- Promoción automática a "Production"
- Archivado de versiones anteriores

### 4. Inferencia (API + Streamlit)

```
┌─────────────┐
│ Streamlit   │
│   User      │
└──────┬──────┘
       │ HTTP POST /predict
       ▼
┌─────────────────┐
│  FastAPI        │
│  Endpoint       │
└──────┬──────────┘
       │ Load model (lazy)
       ▼
┌─────────────────┐
│  MLflow Client  │
│  get_latest_    │
│  versions()     │
└──────┬──────────┘
       │ Stage="Production"
       ▼
┌─────────────────┐
│  Model Loader   │
│  mlflow.pyfunc  │
└──────┬──────────┘
       │ Load from MinIO
       ▼
┌─────────────────┐
│  Model Cache    │
│  (memory)       │
└──────┬──────────┘
       │ predict()
       ▼
┌─────────────────┐
│  Response       │
│  + metadata     │
└─────────────────┘
```

**Optimizaciones:**
- Modelo en cache (no recarga en cada request)
- Lazy loading (solo cuando es necesario)
- Endpoint `/reload-model` para forzar actualización

### 5. Observabilidad (Prometheus + Grafana)

```
┌─────────────┐
│  API        │
│  /metrics   │
└──────┬──────┘
       │ Expose Prometheus metrics
       │ • api_requests_total
       │ • api_request_duration_seconds
       │ • predictions_total
       │ • prediction_errors_total
       ▼
┌─────────────────┐
│  Prometheus     │
│  Scraper        │
└──────┬──────────┘
       │ Store time-series
       ▼
┌─────────────────┐
│  Prometheus DB  │
│  (TSDB)         │
└──────┬──────────┘
       │ Query via PromQL
       ▼
┌─────────────────┐
│  Grafana        │
│  Dashboard      │
└─────────────────┘
```

**Métricas clave:**
- **Throughput**: requests/second
- **Latency**: P50, P95, P99
- **Errors**: rate & count
- **Model usage**: predictions by version

## 🔐 Seguridad y Resiliencia

### Manejo de Secretos
- Variables de entorno en `.env`
- Kubernetes Secrets (producción)
- No hardcoded passwords

### Health Checks
- **API**: `GET /` → Status 200
- **MLflow**: `GET /health` → Status 200
- **Streamlit**: HTTP probe on 8501
- **Prometheus**: `GET /-/healthy`

### Reintentos y Tolerancia a Fallos
- **Airflow**: `retries=1`, `retry_delay=5min`
- **API**: Model reload automático on error
- **Kubernetes**: livenessProbe + readinessProbe

## 📊 Escalabilidad

### Horizontal Scaling
- **API**: 2+ replicas en K8s
- **Airflow Workers**: CeleryExecutor (producción)
- **PostgreSQL**: Read replicas (futuro)

### Vertical Scaling
- Resource requests/limits en K8s
- Tuning de connection pools

## 🚀 Despliegue en Kubernetes

### Namespaces
- `mlops-diabetes`: Todos los componentes

### Persistent Volumes
- `postgres-raw-pvc`: 5Gi
- `postgres-clean-pvc`: 5Gi
- `postgres-mlflow-pvc`: 5Gi
- `minio-pvc`: 10Gi
- `airflow-logs-pvc`: 2Gi

### Services
- **ClusterIP**: Comunicación interna (DBs, MLflow)
- **LoadBalancer**: Acceso externo (API, Streamlit, Grafana)

### ConfigMaps
- Prometheus config
- Airflow variables
- DB init scripts

## 🔍 Debugging y Troubleshooting

### Logs Centralizados
```bash
# Docker Compose
docker-compose logs -f <service>

# Kubernetes
kubectl logs -n mlops-diabetes -l app=<label> -f
```

### Métricas en Tiempo Real
```bash
# Prometheus
curl http://localhost:9090/api/v1/query?query=api_requests_total

# API health
curl http://localhost:8000/
```

### Verificación de Datos
```bash
# PostgreSQL raw
docker exec -it db-raw psql -U postgres -d rawdb -c "SELECT COUNT(*) FROM diabetes_raw;"

# PostgreSQL clean
docker exec -it db-clean psql -U postgres -d cleandb -c "SELECT COUNT(*) FROM diabetes_clean;"
```

## 📈 Optimizaciones Futuras

1. **Caching**: Redis para predictions frecuentes
2. **Batch Prediction**: Endpoint para múltiples predicciones
3. **Model Versioning**: Canary deployments
4. **Feature Store**: Feast o similar
5. **CI/CD**: GitHub Actions + ArgoCD
6. **Monitoring Avanzado**: Distributed tracing (Jaeger)
7. **Data Versioning**: DVC
8. **Model Serving**: Triton Inference Server

## 🎯 Métricas de Éxito

### SLOs (Service Level Objectives)
- **Availability**: 99.5% uptime
- **Latency**: P95 < 500ms
- **Error Rate**: < 1%
- **Throughput**: > 100 req/s

### KPIs de ML
- **Model Accuracy**: > 75%
- **F1-Score**: > 0.70
- **Drift Detection**: Alertas automáticas
- **Retraining**: Semanal o on-demand

## 📚 Referencias Técnicas

- **Airflow**: https://airflow.apache.org/docs/
- **MLflow**: https://mlflow.org/docs/latest/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Streamlit**: https://docs.streamlit.io/
- **Prometheus**: https://prometheus.io/docs/
- **Kubernetes**: https://kubernetes.io/docs/

---

**Versión**: 1.0  
**Última actualización**: 2024  
**Mantenedor**: Proyecto MLOps
