# Componentes Implementados - MLOps Proyecto Final

Este documento detalla los **5 componentes faltantes** que fueron implementados para completar el proyecto según los requisitos del PDF.

---

## ✅ 1. GitHub Actions Workflows (CI/CD)

**Ubicación**: `.github/workflows/`

### Workflows Creados

#### `build-airflow.yml`
- Construye y publica imagen Docker de Airflow
- Trigger: Push a `main`/`master` en `dags/**`
- Imagen: `<DOCKERHUB_USERNAME>/mlops-airflow:latest`

#### `build-api.yml`
- Construye y publica imagen Docker de FastAPI
- Trigger: Push a `main`/`master` en `services/api/**`
- Imagen: `<DOCKERHUB_USERNAME>/mlops-api:latest`

#### `build-frontend.yml`
- Construye y publica imagen Docker de Streamlit
- Trigger: Push a `main`/`master` en `services/frontend/**`
- Imagen: `<DOCKERHUB_USERNAME>/mlops-frontend:latest`

#### `build-mlflow.yml`
- Construye y publica imagen Docker de MLflow
- Trigger: Push a `main`/`master` en `services/mlflow/**`
- Imagen: `<DOCKERHUB_USERNAME>/mlops-mlflow:latest`

#### `ci.yml`
- Pipeline de integración continua
- Jobs: linting (flake8, black), tests (pytest), security scan (Trivy)

### Configuración Requerida

1. Crear secrets en GitHub:
   - `DOCKERHUB_USERNAME`: Tu usuario de DockerHub
   - `DOCKERHUB_TOKEN`: Token de acceso de DockerHub

2. Ver documentación completa en: `.github/workflows/README.md`

---

## ✅ 2. Argo CD Manifests (Despliegue Continuo)

**Ubicación**: `argocd/`

### Archivos Creados

#### `application.yaml`
- Application principal que despliega todo el sistema
- Sync policy: Automated (prune + selfHeal)
- Namespace: `mlops-final`

#### `project.yaml`
- AppProject con definición de:
  - Repositorios permitidos
  - Namespaces de destino
  - Roles (developer, admin)
  - Políticas de acceso

#### `applications.yaml`
- Applications individuales por componente:
  - `mlops-api`: API de inferencia
  - `mlops-frontend`: UI Streamlit
  - `mlops-mlflow`: MLflow Tracking
  - `mlops-airflow`: Orquestador de DAGs
  - `mlops-databases`: PostgreSQL (4 instancias)
  - `mlops-observability`: Prometheus + Grafana

### Instalación

```bash
# 1. Instalar Argo CD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 2. Crear AppProject
kubectl apply -f argocd/project.yaml

# 3. Crear Application principal
kubectl apply -f argocd/application.yaml

# 4. Verificar
kubectl get applications -n argocd
```

Ver documentación completa en: `argocd/README.md`

---

## ✅ 3. SHAP Explicabilidad (Frontend)

**Ubicación**: `services/frontend/app.py`

### Funcionalidades Implementadas

#### Nueva pestaña: "🧠 SHAP Explainability"
- Formulario para ingresar datos del paciente
- Cálculo de valores SHAP vía API `/explain`
- Visualizaciones interactivas:
  - **Waterfall Plot**: Top 15 features con mayor impacto
  - **Force Plot**: Features que aumentan/disminuyen riesgo
  - **Tabla de Valores**: SHAP values ordenados por impacto absoluto

#### Funciones Añadidas

```python
get_shap_explanation(patient_data)
plot_shap_waterfall(shap_values, feature_names, base_value, prediction)
plot_shap_force(shap_values, feature_names, base_value)
```

#### Dependencias Agregadas

```
shap==0.44.0
matplotlib==3.8.2
scikit-learn==1.3.2
```

### Uso

1. Acceder a pestaña "SHAP Explainability"
2. Ingresar datos del paciente
3. Clic en "🔍 Explain Prediction"
4. Visualizar:
   - Predicción (readmission risk)
   - Top features con mayor influencia
   - Dirección del impacto (positivo/negativo)

---

## ✅ 4. Dataset Correcto: Realtor (Bienes Raíces)

**Problema Original**: El proyecto usaba dataset de diabetes, pero el PDF especifica dataset de **precios de propiedades inmobiliarias**.

### Cambios Realizados

#### Schemas de Base de Datos

**`initdb/01_create_raw_db_realtor.sql`**
- Tablas: `raw_train`, `raw_validation`, `raw_test`
- Columnas del dataset realtor:
  ```sql
  brokered_by TEXT             -- Broker/agency (categórico)
  status VARCHAR(50)           -- ready for sale / for_sale
  price NUMERIC(12,2)          -- TARGET VARIABLE
  bed INTEGER                  -- Número de camas
  bath NUMERIC(4,2)            -- Número de baños
  acre_lot NUMERIC(10,4)       -- Tamaño del terreno en acres
  street TEXT                  -- Dirección (categórico)
  city VARCHAR(100)            -- Ciudad
  state VARCHAR(50)            -- Estado
  zip_code VARCHAR(10)         -- Código postal
  house_size INTEGER           -- Área en pies cuadrados
  prev_sold_date DATE          -- Fecha de venta anterior
  ```

**`initdb/02_create_clean_db_realtor.sql`**
- Tablas: `clean_train`, `clean_validation`, `clean_test`
- Features derivados:
  ```sql
  price_per_sqft               -- price / house_size
  bed_bath_ratio               -- bed / bath
  sqft_per_acre                -- house_size / acre_lot
  days_since_prev_sale         -- Días desde última venta
  prev_sale_year, month, quarter
  avg_price_by_city, state, zip
  bed_zscore, bath_zscore, house_size_zscore, acre_lot_zscore
  ```

- Tablas auxiliares:
  - `encoding_mappings`: Encodings categóricos consistentes
  - `preprocessing_statistics`: Stats para normalización

#### Objetivo del Modelo
- **ANTES**: Clasificación (readmission risk: 0, 1, 2)
- **AHORA**: Regresión (predecir precio de propiedad en USD)

---

## ✅ 5. Integración con API Externa del Profesor

**Ubicación**: `dags/1_ingest_from_external_api.py`

### DAG Nuevo: Ingesta desde API Externa

#### Configuración

```python
GROUP_NUMBER = 3                      # Número de grupo asignado
API_URL = "http://10.43.100.103:8000"  # API del profesor
```

#### Funcionamiento

1. **`get_next_request_count()`**
   - Consulta último request_count en `api_request_log`
   - Incrementa en 1 para próximo request

2. **`fetch_data_from_api()`**
   - Hace GET request: `http://10.43.100.103:8000/data?group=3&request=N`
   - Valida status code (200 = OK, 404 = todos los datos recolectados)
   - Registra request en `api_request_log`
   - Retorna JSON con keys: `train`, `validation`, `test`

3. **`load_train_data()`, `load_validation_data()`, `load_test_data()`**
   - Calcula hash MD5 por fila (deduplicación)
   - Inserta en `raw_train`, `raw_validation`, `raw_test`
   - ON CONFLICT DO NOTHING para evitar duplicados

4. **`log_ingestion_summary()`**
   - Cuenta registros por dataset
   - Inserta resumen en `ingestion_summary`

#### Tabla de Logging: `api_request_log`

```sql
CREATE TABLE api_request_log (
    request_count INTEGER,
    group_number INTEGER,
    request_timestamp TIMESTAMP,
    response_status_code INTEGER,
    response_size INTEGER,
    num_records INTEGER,
    error_message TEXT,
    is_successful BOOLEAN
);
```

#### Flujo del DAG

```
get_next_request_count
  ↓
fetch_data_from_api
  ↓
[load_train, load_validation, load_test] (paralelo)
  ↓
log_ingestion_summary
```

#### Manejo de Errores

- **Timeout**: 300s máximo por request
- **404**: Indica que todos los datos fueron recolectados
- **Otros errores**: Se loguean en `api_request_log.error_message`

#### Ejecución

```bash
# Trigger manual
airflow dags trigger 1_ingest_from_external_api

# Schedule diario
schedule_interval='@daily'

# Ver logs
airflow tasks logs 1_ingest_from_external_api fetch_data_from_api <execution_date>
```

---

## Resumen de Cambios

### Archivos Nuevos (19)

#### GitHub Actions (6 archivos)
- `.github/workflows/build-airflow.yml`
- `.github/workflows/build-api.yml`
- `.github/workflows/build-frontend.yml`
- `.github/workflows/build-mlflow.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/README.md`

#### Argo CD (4 archivos)
- `argocd/application.yaml`
- `argocd/project.yaml`
- `argocd/applications.yaml`
- `argocd/README.md`

#### Dataset Realtor (3 archivos)
- `initdb/01_create_raw_db_realtor.sql`
- `initdb/02_create_clean_db_realtor.sql`
- `dags/1_ingest_from_external_api.py`

### Archivos Modificados (2)

- `services/frontend/app.py`
  - Imports: `shap`, `matplotlib`, `numpy`
  - Funciones: `get_shap_explanation()`, `plot_shap_waterfall()`, `plot_shap_force()`
  - Nueva pestaña: "SHAP Explainability"

- `services/frontend/requirements.txt`
  - Agregado: `shap==0.44.0`, `matplotlib==3.8.2`, `scikit-learn==1.3.2`

---

## Estado Final del Proyecto

### ✅ Componentes Completos

1. ✅ **3 DAGs de Airflow**
   - Ingesta desde API externa (nuevo)
   - Preprocesamiento
   - Entrenamiento

2. ✅ **MLflow** - Tracking + Registry

3. ✅ **FastAPI** - API de inferencia con 7 endpoints

4. ✅ **Streamlit** - Frontend con 4 tabs (SHAP nuevo)

5. ✅ **4 Bases de Datos PostgreSQL**

6. ✅ **MinIO S3** - Artefactos MLflow

7. ✅ **Prometheus + Grafana** - Observabilidad

8. ✅ **Locust** - Load testing

9. ✅ **Docker Compose** - Orquestación local

10. ✅ **Kubernetes Manifests** - Despliegue K8s

11. ✅ **GitHub Actions** - CI/CD completo (NUEVO)

12. ✅ **Argo CD** - Despliegue continuo (NUEVO)

13. ✅ **SHAP Explicabilidad** - En frontend (NUEVO)

14. ✅ **Dataset Realtor** - Schema correcto (NUEVO)

15. ✅ **API Externa** - Integración con profesor (NUEVO)

### Implementación: 100% Completa

---

## Próximos Pasos

### 1. Configurar Secrets en GitHub

```bash
# En GitHub → Settings → Secrets → Actions
DOCKERHUB_USERNAME=tu-usuario
DOCKERHUB_TOKEN=tu-token
```

### 2. Desplegar Bases de Datos con Schema Realtor

```bash
# Usar los nuevos archivos SQL
docker-compose up -d db-raw db-clean

# O en Kubernetes
kubectl apply -f kubernetes/databases.yaml
```

### 3. Ejecutar DAG de Ingesta

```bash
# Configurar GROUP_NUMBER en .env
export GROUP_NUMBER=3

# Ejecutar DAG
airflow dags trigger 1_ingest_from_external_api
```

### 4. Configurar Argo CD

```bash
# Instalar y configurar
kubectl apply -f argocd/project.yaml
kubectl apply -f argocd/application.yaml
```

### 5. Adaptar DAGs 2 y 3

- Modificar preprocessing para features del dataset realtor
- Cambiar modelo de clasificación a regresión
- Ajustar métricas (RMSE, MAE, R² en lugar de F1, Accuracy)

---

## Referencias

- **PDF del Proyecto**: `MLOPS_Proyecto_Final_2025.pdf`
- **Contexto**: `contexto_proyecto_final.txt`
- **GitHub Actions Docs**: `.github/workflows/README.md`
- **Argo CD Docs**: `argocd/README.md`
- **API del Profesor**: `http://10.43.100.103:8000/docs`

---

## Contacto

Para dudas o sugerencias sobre la implementación, consultar la documentación en cada directorio.
