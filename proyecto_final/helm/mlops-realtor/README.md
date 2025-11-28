# MLOps Realtor - HELM Chart

Chart completo para despliegue en Kubernetes del sistema MLOps de predicción de precios inmobiliarios.

---

## 🎯 Características

**Despliegue completo en Kubernetes con todas las características del BONO**:
- ✅ HELM charts para todos los servicios
- ✅ Airflow con git-sync (sincronización automática de DAGs desde Git)
- ✅ MinIO con creación automática de bucket
- ✅ Grafana con dashboards precargados mediante ConfigMaps
- ✅ SHAP en interfaz gráfica para explicabilidad

---

## 📦 Componentes Incluidos

- **4 PostgreSQL**: RAW, CLEAN, Airflow metadata, MLflow metadata
- **MinIO**: Storage S3-compatible con auto-create bucket
- **MLflow**: Tracking server y model registry
- **Airflow**: Orquestador con git-sync sidecar
- **FastAPI**: API de inferencia con métricas
- **Streamlit**: Frontend con SHAP y historial
- **Prometheus**: Recolección de métricas
- **Grafana**: Visualización con dashboards precargados

---

## 📋 Prerequisitos

```bash
# Kubernetes cluster
kubectl cluster-info

# HELM 3+
helm version

# (Opcional) ArgoCD para GitOps
kubectl create namespace argocd
kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

---

## 🚀 Instalación

### 1. Personalizar Configuración

Edita `values.yaml` con tus valores:

```yaml
# Imágenes Docker Hub
images:
  mlflow:
    repository: <tu-usuario>/mlops-mlflow
  airflow:
    repository: <tu-usuario>/mlops-airflow
  api:
    repository: <tu-usuario>/mlops-api
  frontend:
    repository: <tu-usuario>/mlops-frontend

# Git-sync para Airflow (BONO)
airflow:
  gitSync:
    enabled: true
    repo: "https://github.com/<tu-usuario>/mlops-realtor.git"
    branch: "master"
    subPath: "dags"

# Configuración de grupo
airflow:
  env:
    GROUP_NUMBER: "3"  # Tu número de grupo
```

### 2. Instalar Chart

```bash
# Crear namespace
kubectl create namespace mlops

# Instalar
helm install mlops-realtor . -n mlops

# Verificar instalación
kubectl get pods -n mlops
```

### 3. Acceder a Servicios

```bash
# Obtener IP del nodo
export NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')

# Servicios disponibles (NodePort):
# - Airflow:    http://$NODE_IP:30080  (admin/admin)
# - MLflow:     http://$NODE_IP:30500
# - API:        http://$NODE_IP:30800
# - Frontend:   http://$NODE_IP:30501
# - Grafana:    http://$NODE_IP:30300  (admin/admin)
# - Prometheus: http://$NODE_IP:30909
# - MinIO:      http://$NODE_IP:30901  (minioadmin/minioadmin)
```

---

## 🔧 Post-Instalación

### Inicializar Bases de Datos

```bash
# Copiar scripts SQL a pods
kubectl cp ../../initdb/01_create_raw_db_realtor.sql \
  mlops/postgres-raw-<pod-id>:/tmp/

# Ejecutar scripts
kubectl exec -it deployment/postgres-raw -n mlops -- \
  psql -U mlops -d mlops_raw -f /tmp/01_create_raw_db_realtor.sql

# Repetir para CLEAN y MLflow
```

### Verificar git-sync (BONO)

```bash
# Ver logs de git-sync
kubectl logs -f deployment/airflow -c git-sync -n mlops

# Debe mostrar:
# INFO: synced repository to /dags/repo
```

### Verificar Dashboards de Grafana (BONO)

1. Accede a Grafana: http://$NODE_IP:30300
2. Login: admin/admin
3. **Dashboards** → **Browse**
4. Verás automáticamente:
   - MLOps - System Overview
   - MLOps - Model Performance

---

## 🔄 Actualizar Sistema

```bash
# Actualizar valores
helm upgrade mlops-realtor . -n mlops \
  --set images.api.tag=v2.0

# Ver historial
helm history mlops-realtor -n mlops

# Rollback
helm rollback mlops-realtor -n mlops
```

---

## 🗑️ Desinstalación

```bash
# Desinstalar (mantiene PVCs)
helm uninstall mlops-realtor -n mlops

# Eliminar PVCs (¡elimina datos!)
kubectl delete pvc --all -n mlops

# Eliminar namespace
kubectl delete namespace mlops
```

---

## 📊 Características del BONO

| Requisito | Implementado | Archivo |
|-----------|--------------|---------|
| HELM charts completos | ✅ | `Chart.yaml`, `templates/*.yaml` |
| Airflow git-sync | ✅ | `templates/airflow.yaml` (sidecar) |
| MinIO auto-create bucket | ✅ | `templates/minio.yaml` (initContainer) |
| Grafana dashboards ConfigMaps | ✅ | `templates/grafana-dashboards.yaml` |
| SHAP en interfaz | ✅ | `../../services/frontend/app.py` |

---

## 🐛 Troubleshooting

```bash
# Ver logs de un pod
kubectl logs -f deployment/<nombre> -n mlops

# Ver eventos del namespace
kubectl get events -n mlops --sort-by='.lastTimestamp'

# Describir recurso
kubectl describe pod/<nombre> -n mlops

# Estado de recursos
kubectl get all -n mlops
```

---

## 📚 Documentación

- [README.md](../../README.md) - Documentación principal
- [QUICKSTART.md](../../QUICKSTART.md) - Guía rápida

**Última actualización**: 28 de Noviembre de 2025
