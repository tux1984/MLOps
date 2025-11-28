# Quick Start

Guía práctica para ejecutar el proyecto MLOps Realtor localmente.

---

## ⚡ Inicio Rápido (5 minutos)

```bash
# 1. Iniciar servicios
docker compose up -d

# 2. Verificar que estén activos (~30 segundos)
docker compose ps

# 3. Acceder a Airflow
open http://localhost:8080  # Usuario: admin, Password: admin
```

---

## 🔄 Flujo de Ejecución

### Paso 1: Ingestar Datos (2-3 min)

**En Airflow (http://localhost:8080)**:
1. Buscar DAG: `1_ingest_from_external_api`
2. Activar toggle (debe quedar azul)
3. Click ▶️ → "Trigger DAG"
4. Esperar hasta que esté verde ✅

**Qué hace**: Obtiene ~4,000 registros de la API del profesor y los guarda en PostgreSQL RAW.

**Verificar**:
```bash
docker compose exec db-raw psql -U mlops -d mlops_raw -c \
  "SELECT COUNT(*) FROM raw_train;"
# Debería mostrar ~2,838 registros
```

### Paso 2: Limpiar Datos (3-5 min)

**En Airflow**:
1. DAG: `2_clean_build`
2. Click ▶️ → "Trigger DAG"
3. Esperar hasta verde ✅

**Qué hace**: Preprocesa datos RAW (limpieza, encoding, feature engineering) y los guarda en PostgreSQL CLEAN.

### Paso 3: Entrenar Modelos (5-10 min)

**En Airflow**:
1. DAG: `3_train_and_register`
2. Click ▶️ → "Trigger DAG"
3. Esperar hasta verde ✅

**Qué hace**: Entrena 3 modelos (Random Forest, Gradient Boosting, Logistic Regression), los registra en MLflow y promociona el mejor a "Production".

**Verificar en MLflow (http://localhost:5001)**:
- **Models** → Debe haber un modelo en stage "Production"

---

## 🧪 Probar la API

### Health Check
```bash
curl http://localhost:8000/health
```

### Predicción Individual
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

**Respuesta esperada**:
```json
{
  "predicted_price": 350000.0,
  "model_name": "realtor_price_model",
  "model_version": "1",
  "model_stage": "Production"
}
```

### Documentación Interactiva
```
http://localhost:8000/docs
```

---

## 🎨 Interfaz Web

**Streamlit** (http://localhost:8501):

1. **🎯 Predicción**
   - Formulario interactivo para ingresar datos
   - Predicción en tiempo real
   - Información del modelo usado

2. **📊 Historial de Modelos**
   - Tabla con todas las versiones entrenadas
   - Métricas (RMSE, MAE, R², MAPE)
   - Gráficos de evolución
   - Comparador de modelos

3. **🔍 Explicabilidad (SHAP)**
   - Análisis de características más influyentes
   - Visualización de impacto
   - Valores SHAP por feature

4. **📈 Estadísticas**
   - Total de inferencias
   - Uso por modelo
   - Estado del sistema

---

## 📊 Monitoreo

**Grafana** (http://localhost:3000):
- Login: admin/admin
- **Dashboards** → Browse → Ver dashboards precargados:
  - MLOps - System Overview
  - MLOps - Model Performance

**Prometheus** (http://localhost:9090):
- Métricas en tiempo real
- Query: `predictions_total`, `prediction_latency_seconds`

---

## 🔄 Ciclo de Reentrenamiento

Para obtener más datos y reentrenar:

```bash
# 1. Ejecutar DAG 1 nuevamente (obtiene siguiente batch)
# 2. Ejecutar DAG 2 (procesa nuevos datos)
# 3. Ejecutar DAG 3 (entrena con datos actualizados)
# 4. Nuevo modelo automáticamente en Production (si es mejor)
# 5. API usa nuevo modelo sin cambios de código
```

**Nota**: La API guarda todas las inferencias en RAW DB para futuros entrenamientos.

---

## 🐳 Comandos Docker

```bash
# Ver logs en tiempo real
docker compose logs -f airflow-scheduler
docker compose logs -f api

# Reiniciar un servicio
docker compose restart <servicio>

# Ver estado de salud
docker compose ps

# Detener todo
docker compose down

# Limpiar completamente (¡elimina datos!)
docker compose down -v
```

---

## ☸️ Despliegue en Kubernetes

Para despliegue en producción con todas las características del BONO:

```bash
# Instalar con HELM
cd helm/mlops-realtor
helm install mlops-realtor . -n mlops --create-namespace

# Verificar pods
kubectl get pods -n mlops

# Acceder via NodePort
# Airflow:   http://<node-ip>:30080
# Frontend:  http://<node-ip>:30501
```

**Características del BONO incluidas**:
- ✅ HELM charts completos
- ✅ Airflow con git-sync (sincronización automática de DAGs)
- ✅ MinIO con auto-create bucket
- ✅ Grafana con ConfigMaps de dashboards precargados
- ✅ SHAP en interfaz gráfica
- ✅ Todos los servicios con health checks

Ver [helm/mlops-realtor/README.md](helm/mlops-realtor/README.md) para detalles.

---

## 🔍 Verificación Rápida

```bash
# 1. Servicios activos
docker compose ps
# Todos deben estar "Up" y "healthy"

# 2. Datos ingresados
docker compose exec db-raw psql -U mlops -d mlops_raw -c \
  "SELECT COUNT(*) FROM raw_train;"

# 3. API funcionando
curl http://localhost:8000/health

# 4. Modelo cargado
curl http://localhost:8000/model-info
```

---

## 💡 Notas Importantes

### API Externa
- **URL**: http://10.43.100.103:8000/data
- **Parámetros**: `group_number=<tu-grupo>`, `day=Tuesday|Wednesday`
- Cada request devuelve un batch diferente de datos
- Grupo 3 → `day=Tuesday`
- Grupo asignable en `.env` → `GROUP_NUMBER=3`

### Configuración
Las variables de entorno están en `.env`. Principales:

```bash
GROUP_NUMBER=3                          # Tu número de grupo
API_BASE_URL=http://10.43.100.103:8000 # API del profesor
MLFLOW_TRACKING_URI=http://mlflow:5000
```

### Primer Uso
- **Primera vez**: Ejecuta DAG 1 → DAG 2 → DAG 3 en orden
- **Reentrenamiento**: Ejecuta DAG 1 múltiples veces para más datos
- **Sin modelo**: Si la API no carga modelo, ejecuta DAG 3

---

## 📚 Más Información

**Documentación**:
- [README.md](README.md) - Este archivo
- [helm/mlops-realtor/README.md](helm/mlops-realtor/README.md) - Kubernetes y HELM

**Soporte**:
- Logs: `docker compose logs -f <servicio>`
- Airflow UI: http://localhost:8080 → DAG → Logs
- MLflow UI: http://localhost:5001 → Experiments

---

**Tiempo total estimado**: ~15 minutos para tener todo funcionando
