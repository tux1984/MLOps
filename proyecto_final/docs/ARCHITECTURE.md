# Arquitectura del Sistema MLOps

## Visión General

Este documento describe la arquitectura completa del sistema MLOps para predicción de readmisión hospitalaria de pacientes diabéticos.

## Componentes Principales

### 1. Capa de Datos

#### PostgreSQL Databases
- **raw-db**: Almacena datos crudos ingresados desde fuentes externas
  - Tablas: `raw_train`, `raw_validation`, `raw_test`, `batch_metadata`
  - Incluye `row_hash` para detección de duplicados
  
- **clean-db**: Almacena datos preprocesados listos para entrenamiento
  - Tablas: `clean_train`, `clean_validation`, `clean_test`
  - Incluye metadata de transformaciones aplicadas
  
- **airflow-db**: Backend para Airflow
- **mlflow-db**: Backend store para MLflow Tracking

#### MinIO S3
- Almacenamiento de artifacts de MLflow
- Bucket: `mlflow-artifacts`
- S3-compatible para portabilidad

### 2. Capa de Orquestación

#### Apache Airflow
- **Executor**: LocalExecutor (desarrollo), KubernetesExecutor (producción)
- **DAGs**:
  1. `1_raw_batch_ingest_15k.py`: Ingesta en batches de 15,000 registros
  2. `2_clean_build.py`: Preprocesamiento y limpieza
  3. `3_train_and_register.py`: Entrenamiento y registro de modelos

### 3. Capa de ML Tracking

#### MLflow
- **Tracking Server**: Registra experimentos, métricas y parámetros
- **Model Registry**: Gestiona versiones de modelos
- **Stages**: Ninguno → Staging → Production → Archived
- **Artifacts**: Almacenados en MinIO S3

### 4. Capa de Inferencia

#### FastAPI
- **Endpoints**:
  - `POST /predict`: Predicción individual
  - `POST /predict-batch`: Predicción en lote
  - `POST /explain`: Explicación SHAP
  - `GET /health`: Health check
  - `GET /metrics`: Métricas Prometheus
  - `GET /model-info`: Información del modelo

- **Características**:
  - Carga dinámica de modelo desde MLflow Production
  - Sin cambios de código al actualizar modelo
  - Auto-scaling con HPA en Kubernetes
  - Métricas exportadas para Prometheus

#### Streamlit Frontend
- Interfaz de usuario interactiva
- Predicciones individuales y batch
- Visualización de explicabilidad SHAP
- Dashboard de métricas

### 5. Capa de Observabilidad

#### Prometheus
- Recolección de métricas de todos los componentes
- Scraping cada 15 segundos
- Métricas personalizadas:
  - Latencia de predicciones
  - Throughput de API
  - Estado de DAGs
  - Performance de modelos

#### Grafana
- Dashboards interactivos
- Visualización de métricas
- Alertas configurables

### 6. Capa de Testing

#### Locust
- Pruebas de carga
- Simulación de usuarios concurrentes
- Métricas de performance:
  - Response time
  - Throughput (req/s)
  - Error rate

## Flujo de Datos

### Pipeline de Entrenamiento

```
1. Ingesta de Datos
   ↓
2. [DAG 1] Descarga dataset → Split 70/15/15 → Carga en batches → raw-db
   ↓
3. [DAG 2] Lee raw-db → Limpieza → Encoding → Scaling → clean-db
   ↓
4. [DAG 3] Lee clean-db → Entrenamiento → Evaluación → MLflow
   ↓
5. MLflow: Compara modelos → Selecciona mejor → Promociona a Production
```

### Pipeline de Inferencia

```
1. Request llega a FastAPI
   ↓
2. API carga modelo desde MLflow Production (si no está en memoria)
   ↓
3. Preprocesamiento de datos de entrada
   ↓
4. Predicción con modelo
   ↓
5. (Opcional) Cálculo de SHAP values para explicación
   ↓
6. Response con predicción y probabilidad
   ↓
7. Registro de métricas en Prometheus
```

## Patrones de Diseño

### 1. Dynamic Model Loading
- API carga modelo dinámicamente desde MLflow
- No requiere rebuild al actualizar modelo
- Endpoint `/reload-model` para forzar recarga

### 2. Microservices Architecture
- Servicios independientes y desacoplados
- Comunicación via HTTP/REST
- Escalado independiente por servicio

### 3. GitOps (Kubernetes)
- Infraestructura como código
- Versionado en Git
- Despliegue declarativo

### 4. Observability First
- Métricas en todos los componentes
- Logging estructurado
- Trazabilidad end-to-end

## Consideraciones de Producción

### Escalabilidad
- API: Horizontal scaling con HPA
- Airflow: KubernetesExecutor para paralelización
- Bases de datos: Connection pooling
- Cache: Redis para modelo en memoria (futuro)

### Alta Disponibilidad
- Múltiples réplicas de API
- Health checks y readiness probes
- Graceful shutdown
- Circuit breakers

### Seguridad
- Secrets management con Kubernetes Secrets
- Network policies
- RBAC en Kubernetes
- API authentication (futuro)

### Monitoreo
- SLIs: Latency, Error rate, Throughput
- SLOs: 95th percentile < 500ms, Error rate < 1%
- Alertas automáticas
- Logs centralizados

## Tecnologías Utilizadas

- **Orchestration**: Kubernetes, Docker, Docker Compose
- **ML Pipeline**: Apache Airflow
- **ML Tracking**: MLflow
- **API**: FastAPI, Uvicorn
- **Frontend**: Streamlit
- **Databases**: PostgreSQL
- **Storage**: MinIO (S3)
- **Monitoring**: Prometheus, Grafana
- **Load Testing**: Locust
- **ML**: scikit-learn, XGBoost, SHAP
- **Languages**: Python 3.11

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Kubernetes Cluster / Docker Compose               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        Data Layer                                 │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────┐  │  │
│  │  │ raw-db  │  │clean-db │  │airflow  │  │mlflow   │  │MinIO │  │  │
│  │  │(PostgreSQL)│(PostgreSQL)│ -db     │  │-db      │  │ (S3) │  │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └──────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    ▲                                     │
│                                    │                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   Orchestration Layer                             │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │                    Apache Airflow                            │ │  │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │ │  │
│  │  │  │  DAG 1   │  │  DAG 2   │  │  DAG 3   │                  │ │  │
│  │  │  │ Ingest   │→ │  Clean   │→ │  Train   │                  │ │  │
│  │  │  └──────────┘  └──────────┘  └──────────┘                  │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     ML Tracking Layer                             │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │                        MLflow                                │ │  │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐           │ │  │
│  │  │  │Experiments │  │   Models   │  │  Registry  │           │ │  │
│  │  │  └────────────┘  └────────────┘  └────────────┘           │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Inference Layer                                │  │
│  │  ┌──────────────┐                      ┌──────────────┐          │  │
│  │  │   FastAPI    │◄─────────────────────│  Streamlit   │          │  │
│  │  │     API      │                      │   Frontend   │          │  │
│  │  └──────────────┘                      └──────────────┘          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                  Observability Layer                              │  │
│  │  ┌──────────────┐              ┌──────────────┐                  │  │
│  │  │  Prometheus  │─────────────▶│   Grafana    │                  │  │
│  │  │   Metrics    │              │  Dashboards  │                  │  │
│  │  └──────────────┘              └──────────────┘                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Próximos Pasos

1. Implementación de CI/CD pipeline
2. Drift detection automático
3. A/B testing de modelos
4. Feature store
5. Model serving con Seldon/KServe
