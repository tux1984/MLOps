# MLOps - Predicción de Precios Inmobiliarios

Sistema end-to-end de MLOps para predicción de precios de propiedades inmobiliarias usando datos de Realtor.

---

## 🎯 Descripción

Plataforma completa que implementa el ciclo de vida de Machine Learning:
- **Ingesta automática** desde API externa
- **Preprocesamiento** y transformación de datos
- **Entrenamiento** de modelos con tracking en MLflow
- **API REST** para inferencia con guardado de logs
- **Interfaz web** con explicabilidad SHAP
- **Monitoreo** con Prometheus y Grafana
- **CI/CD** con GitHub Actions
- **Despliegue Kubernetes** con HELM (opcional)

**Dataset**: Realtor - Predicción de precios de propiedades  
**Tipo**: Regresión  
**Target**: `price` (precio de la propiedad)  
**Features**: ubicación, tamaño, habitaciones, baños, estado, etc.

---

## 📦 Arquitectura

```
API Externa (Profesor) → Airflow DAG 1 → PostgreSQL RAW
                              ↓
                  Airflow DAG 2 → PostgreSQL CLEAN
                              ↓
                  Airflow DAG 3 → MLflow (modelo en Production)
                              ↓
                  FastAPI (inferencia) ← MLflow Model Registry
                              ↓
                  Streamlit (UI) + Prometheus/Grafana (monitoreo)
```

**Componentes**:
- 4 PostgreSQL (RAW, CLEAN, Airflow metadata, MLflow metadata)
- MinIO (S3 storage para artifacts)
- Airflow (orquestación con git-sync en K8s)
- MLflow (tracking y model registry)
- FastAPI (API de predicción con métricas)
- Streamlit (UI con SHAP y historial)
- Prometheus + Grafana (observabilidad con dashboards precargados)

---

## 🚀 Inicio Rápido

### Prerequisitos
```bash
# Docker y Docker Compose instalados
docker --version
docker compose version
```

### Instalación

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd proyecto_final

# 2. Iniciar servicios
docker compose up -d

# 3. Verificar estado
docker compose ps
```

### Acceso a Servicios

| Servicio | URL | Credenciales | Descripción |
|----------|-----|--------------|-------------|
| **Airflow** | http://localhost:8080 | admin/admin | Orquestador de pipelines |
| **MLflow** | http://localhost:5001 | - | Tracking y model registry |
| **API** | http://localhost:8000 | - | Inferencia REST |
| **Frontend** | http://localhost:8501 | - | Interfaz web |
| **Grafana** | http://localhost:3000 | admin/admin | Dashboards de monitoreo |
| **Prometheus** | http://localhost:9090 | - | Métricas del sistema |

---

## 📊 Ejemplo de Uso Completo

### 1. Ingestar Datos

Accede a **Airflow** (http://localhost:8080) y ejecuta:

```
DAG: 1_ingest_from_external_api
```
- Activa el toggle
- Click en ▶️ → "Trigger DAG"
- Espera ~2-3 min

**Resultado**: ~4,000 registros en PostgreSQL RAW (train/validation/test)

### 2. Preprocesar Datos

En Airflow, ejecuta:
```
DAG: 2_clean_build
```

**Resultado**: Datos limpios y transformados en PostgreSQL CLEAN

### 3. Entrenar Modelos

En Airflow, ejecuta:
```
DAG: 3_train_and_register
```

**Resultado**: 3 modelos entrenados (Random Forest, Gradient Boosting, Logistic Regression) registrados en MLflow, el mejor en stage "Production"

### 4. Verificar Modelo en MLflow

Accede a **MLflow** (http://localhost:5001):
- **Experiments** → Ver runs y métricas
- **Models** → Verificar modelo en stage "Production"

### 5. Realizar Predicciones

**Opción A - API REST**:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "property": {
      "brokered_by": "Century 21",
      "status": "for_sale",
      "bed": 3,
      "bath": 2.0,
      "acre_lot": 0.25,
      "street": "123 Main St",
      "city": "Miami",
      "state": "Florida",
      "zip_code": "33101",
      "house_size": 1500,
      "prev_sold_date": null
    }
  }'
```

**Respuesta**:
```json
{
  "predicted_price": 350000.0,
  "model_name": "realtor_price_model",
  "model_version": "1",
  "model_stage": "Production",
  "timestamp": "2025-11-28T..."
}
```

**Opción B - Interfaz Web**:

Accede a **Streamlit** (http://localhost:8501):
- **🎯 Predicción**: Formulario interactivo
- **📊 Historial**: Modelos entrenados con métricas
- **🔍 SHAP**: Explicabilidad del modelo
- **📈 Estadísticas**: Uso del sistema

### 6. Monitorear Sistema

**Grafana** (http://localhost:3000):
- Dashboards precargados automáticamente
- Métricas de API, latencia, errores
- Visualización en tiempo real

---

## 🛠️ Desarrollo

### Estructura del Proyecto

```
proyecto_final/
├── dags/                      # Airflow DAGs
│   ├── 1_ingest_from_external_api.py
│   ├── 2_clean_build.py
│   ├── 3_train_and_register.py
│   └── utils/                 # Utilidades
├── services/
│   ├── api/                   # FastAPI
│   ├── frontend/              # Streamlit
│   ├── mlflow/                # MLflow server
│   └── locust/                # Load testing
├── helm/mlops-realtor/        # HELM chart para Kubernetes
├── kubernetes/                # Manifiestos K8s
├── initdb/                    # Scripts SQL inicialización
├── .github/workflows/         # CI/CD pipelines
├── docker-compose.yml         # Orquestación local
└── README.md                  # Este archivo
```

### Construir Imágenes Docker

```bash
# Airflow
docker build -f dags/Dockerfile.airflow -t <user>/mlops-airflow:latest .

# API
docker build -t <user>/mlops-api:latest services/api

# Frontend
docker build -t <user>/mlops-frontend:latest services/frontend

# Publicar
docker push <user>/mlops-*:latest
```

### Variables de Entorno

Configuradas en `.env`:

```bash
# PostgreSQL
POSTGRES_USER=mlops
POSTGRES_PASSWORD=mlops123

# API Externa
GROUP_NUMBER=3                          # Tu número de grupo
API_BASE_URL=http://10.43.100.103:8000

# MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000
```

---

## 🎨 Características Avanzadas

### ✨ SHAP Explicabilidad
El frontend incluye interpretación de modelos con SHAP values, mostrando el impacto de cada característica en la predicción.

### 📊 Historial de Modelos
Tracking completo de versiones de modelos con métricas, comparaciones y evolución temporal.

### 💾 Logs de Inferencia
Todas las predicciones se guardan en RAW DB para análisis y reentrenamiento futuro.

### 🔄 Reentrenamiento Continuo
El sistema detecta nuevos datos y permite reentrenar modelos manualmente o programado.

### 📈 Dashboards Precargados
Grafana incluye dashboards automáticos con métricas de sistema y performance de modelos.

---

## 🎯 Despliegue en Kubernetes (Opcional)

### Con HELM

```bash
# Instalar chart completo
cd helm/mlops-realtor
helm install mlops-realtor . -n mlops --create-namespace

# Acceder via NodePort
# Airflow:   http://<node-ip>:30080
# MLflow:    http://<node-ip>:30500
# Frontend:  http://<node-ip>:30501
```

**Incluye**:
- ✅ Git-sync para Airflow (sincronización automática de DAGs)
- ✅ MinIO con auto-create bucket
- ✅ Grafana con ConfigMaps de dashboards
- ✅ Todos los servicios con health checks y resource limits

Ver [helm/mlops-realtor/README.md](helm/mlops-realtor/README.md) para detalles.

---

## 📊 Métricas de Evaluación

**Modelos de regresión evaluados con**:
- **RMSE** (Root Mean Squared Error)
- **MAE** (Mean Absolute Error)
- **R²** (Coefficient of Determination)
- **MAPE** (Mean Absolute Percentage Error)

El modelo con mejor R² se promociona automáticamente a "Production" en MLflow.

---

## 🔧 Comandos Útiles

```bash
# Ver logs de un servicio
docker compose logs -f <servicio>

# Reiniciar servicios
docker compose restart <servicio>

# Verificar datos en BD
docker compose exec db-raw psql -U mlops -d mlops_raw -c "SELECT COUNT(*) FROM raw_train;"

# Detener todo
docker compose down

# Limpiar volúmenes (¡CUIDADO! Elimina datos)
docker compose down -v
```

---

## 🐛 Troubleshooting

**Problema**: API no carga modelo
- **Solución**: Verifica que hay un modelo en "Production" en MLflow → Ejecuta DAG 3

**Problema**: DAG falla
- **Solución**: Revisa logs en Airflow UI → DAG → Run → Task → Logs

**Problema**: Sin datos en tablas
- **Solución**: Verifica que DAG 1 se ejecutó exitosamente (círculo verde en Airflow)

---

## 📚 Documentación

- **README.md** (este archivo) - Visión general y arquitectura
- **QUICKSTART.md** - Guía de inicio rápido
- **helm/mlops-realtor/README.md** - Despliegue en Kubernetes

---

## 📄 Requisitos del Proyecto

Implementación completa del proyecto final del curso **Operaciones de Machine Learning**:
- ✅ Ingesta automatizada con Airflow
- ✅ Preprocesamiento y feature engineering
- ✅ Tracking de experimentos con MLflow
- ✅ Model registry y versionado
- ✅ API de inferencia con FastAPI
- ✅ Interfaz web con Streamlit
- ✅ SHAP explicabilidad
- ✅ Observabilidad con Prometheus/Grafana
- ✅ CI/CD con GitHub Actions
- ✅ Despliegue Kubernetes con HELM (opcional)
- ✅ GitOps con ArgoCD (opcional)
