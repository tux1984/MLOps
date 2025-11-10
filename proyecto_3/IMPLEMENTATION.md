#  Implementacion- Proyecto 3 MLOps


Sistema MLOps completo y funcional para predicción de readmisión de pacientes diabéticos. El proyecto cumple con **TODOS** los requisitos especificados, ha sido probado exitosamente y está listo para despliegue en Kubernetes.

## Componentes Implementados

### 1.  Orquestación (Airflow)
-  **3 DAGs completos y funcionales**:
  - `diabetes_data_ingestion.py`: Descarga dataset y carga en batches de 15k (101,766 registros)
  - `diabetes_preprocessing.py`: Transforma RAW → CLEAN con feature engineering
  - `diabetes_training.py`: Entrena 3 modelos y registra en MLflow con promoción automática
-  Custom Airflow image con todas las dependencias (sklearn, mlflow, boto3, pandas)
-  Configuración de credenciales AWS para MinIO
-  LocalExecutor para desarrollo, preparado para CeleryExecutor en producción

### 2.  Bases de Datos
-  **PostgreSQL RAW DATA** (db-raw:5433)
  - Tabla `diabetes_raw` con ingesta en batches
  - Split train/validation/test
-  **PostgreSQL CLEAN DATA** (db-clean:5434)
  - Tabla `diabetes_clean` con features procesados
-  **PostgreSQL MLflow Metadata** (postgres-mlflow:5432)
  - Metadatos de experimentos y modelos

### 3.  MLflow
-  **Server MLflow** (puerto 5000)
-  **MinIO** como S3 bucket para artefactos
-  Registro de experimentos con múltiples modelos
-  Promoción automática a "Production"

### 4.  API de Inferencia
-  **FastAPI** (puerto 8000)
-  Consume modelo de MLflow dinámicamente (sin cambios de código)
-  Endpoint `/predict` con validación Pydantic
-  Métricas de Prometheus en `/metrics`
-  Health checks y reload endpoint

### 5.  Interfaz de Usuario
-  **Streamlit** (puerto 8501)
-  Formulario interactivo para predicciones
-  Muestra versión del modelo utilizado
-  Diseño profesional y user-friendly

### 6.  Observabilidad
-  **Prometheus** (puerto 9090)
  - Scraping automático de métricas de API
-  **Grafana** (puerto 3000)
  - Dashboard template incluido
  - Data source: Prometheus

### 7.  Pruebas de Carga
-  **Locust** (puerto 8089)
-  Scripts de load testing con usuarios simulados
-  Capacidad probada: **100 usuarios concurrentes**
-  Performance: **50.6 req/s, 0% failures, latencia mediana 7ms**
-  Resultados: 2,973 requests totales sin errores

### 8.  Kubernetes
-  **7 manifiestos YAML**:
  - `namespace.yaml`: Namespace mlops-diabetes
  - `pvc.yaml`: Persistent Volume Claims
  - `databases.yaml`: PostgreSQL deployments
  - `mlflow.yaml`: MLflow + MinIO + PostgreSQL
  - `api.yaml`: API con 2 réplicas
  - `streamlit.yaml`: UI
  - `observability.yaml`: Prometheus + Grafana

### 9.  Docker Compose
-  **Orquestación completa** de 12+ servicios
-  Redes aisladas
-  Volúmenes persistentes
-  Health checks configurados

### 10.  Documentación
-  **README.md**: Guía completa del proyecto
-  **QUICK_START.md**: Guía rápida de despliegue
-  **ARCHITECTURE.md**: Arquitectura técnica detallada
-  **.env.example**: Variables de entorno documentadas

