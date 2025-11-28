# Guía de Despliegue

## Prerequisitos

### Software Requerido

#### Para Despliegue Local (Docker Compose)
- Docker Desktop 4.x o superior
- Docker Compose 2.x o superior
- 8GB RAM mínimo, 16GB recomendado
- 20GB espacio en disco

#### Para Despliegue en Kubernetes
- kubectl 1.25+
- k3d 5.x o minikube 1.30+ (para desarrollo local)
- Helm 3.x (opcional, para charts)

### Configuración Inicial

1. **Clonar el repositorio**
```bash
git clone <repo-url>
cd proyecto_final
```

2. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env según necesidades
```

## Despliegue con Docker Compose

### 1. Despliegue Completo

```bash
# Iniciar todos los servicios
docker-compose up -d --build

# Verificar que servicios están corriendo
docker-compose ps

# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f api
```

### 2. Inicialización de Airflow

```bash
# Ejecutar inicialización de Airflow (primera vez)
docker-compose run --rm airflow-init

# Crear usuario admin de Airflow (si no existe)
docker-compose exec airflow-webserver airflow users create \
    --username admin \
    --password admin123 \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

### 3. Verificar Servicios

Acceder a las interfaces web:

- **Airflow**: http://localhost:8080
  - Usuario: `admin`
  - Contraseña: `admin123`

- **MLflow**: http://localhost:5001

- **API Docs**: http://localhost:8000/docs

- **Streamlit**: http://localhost:8501

- **Grafana**: http://localhost:3000
  - Usuario: `admin`
  - Contraseña: `admin`

- **Prometheus**: http://localhost:9090

- **MinIO Console**: http://localhost:9001
  - Usuario: `minioadmin`
  - Contraseña: `minioadmin`

### 4. Ejecutar Pipeline de Datos

1. Ir a Airflow UI: http://localhost:8080
2. Activar y ejecutar DAGs en orden:
   - `1_raw_batch_ingest_15k`
   - `2_clean_build`
   - `3_train_and_register`

3. Verificar en MLflow que el modelo fue registrado

### 5. Probar API

```bash
# Health check
curl http://localhost:8000/health

# Model info
curl http://localhost:8000/model-info

# Predicción (ajustar JSON según schema)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "patient": {
      "age": 65,
      "gender": "Male"
    }
  }'
```

## Despliegue en Kubernetes

### 1. Crear Cluster K3d (Local)

```bash
# Crear cluster
./scripts/create_cluster.sh

# O manualmente:
k3d cluster create mlops-cluster \
  --agents 2 \
  --port "8080:30808@loadbalancer" \
  --port "8000:30800@loadbalancer" \
  --port "8501:30851@loadbalancer"

# Verificar cluster
kubectl cluster-info
kubectl get nodes
```

### 2. Desplegar Aplicaciones

```bash
# Opción 1: Usar script automatizado
./scripts/deploy.sh kubernetes

# Opción 2: Manual
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/pvc.yaml
kubectl apply -f kubernetes/databases.yaml
kubectl apply -f kubernetes/mlflow.yaml
kubectl apply -f kubernetes/airflow.yaml
kubectl apply -f kubernetes/api.yaml
kubectl apply -f kubernetes/frontend.yaml
kubectl apply -f kubernetes/observability.yaml
```

### 3. Verificar Despliegue

```bash
# Ver todos los pods
kubectl get pods -n mlops

# Ver servicios
kubectl get svc -n mlops

# Ver estado de pods
kubectl describe pod <pod-name> -n mlops

# Ver logs
kubectl logs <pod-name> -n mlops -f
```

### 4. Acceder a Servicios

```bash
# Obtener URLs de servicios
kubectl get svc -n mlops

# Port-forward si es necesario
kubectl port-forward svc/api 8000:8000 -n mlops
kubectl port-forward svc/frontend 8501:8501 -n mlops
kubectl port-forward svc/airflow-webserver 8080:8080 -n mlops
```

## Configuración Adicional

### Configurar Prometheus Data Sources en Grafana

1. Ir a Grafana: http://localhost:3000
2. Login (admin/admin)
3. Configuration → Data Sources → Add data source
4. Seleccionar Prometheus
5. URL: `http://prometheus:9090`
6. Save & Test

### Importar Dashboard de Grafana

1. En Grafana: Dashboards → Import
2. Upload JSON file: `config/grafana/dashboard.json`
3. Seleccionar Prometheus data source
4. Import

### Configurar Alertas (Opcional)

```bash
# Editar prometheus.yml para agregar alertmanager
vim config/prometheus/prometheus.yml

# Reiniciar Prometheus
docker-compose restart prometheus
# O en K8s:
kubectl rollout restart deployment/prometheus -n mlops
```

## Troubleshooting

### Servicios no inician

```bash
# Ver logs detallados
docker-compose logs <service-name>

# Verificar conectividad entre servicios
docker-compose exec <service> ping <other-service>

# Verificar variables de entorno
docker-compose exec <service> env
```

### Problemas de base de datos

```bash
# Reiniciar bases de datos
docker-compose restart db-raw db-clean postgres-mlflow postgres-airflow

# Verificar logs de PostgreSQL
docker-compose logs postgres-raw
```

### API no carga modelo

```bash
# Verificar que modelo está en Production en MLflow
# Recargar modelo manualmente
curl -X POST http://localhost:8000/reload-model

# Ver logs de API
docker-compose logs -f api
```

### Problemas de permisos en Airflow

```bash
# Corregir permisos
sudo chown -R 50000:0 ./logs ./dags ./plugins

# O en el contenedor:
docker-compose exec airflow-webserver chown -R airflow:root /opt/airflow
```

## Actualización de Servicios

### Actualizar API

```bash
# Rebuild imagen
docker-compose build api

# Reiniciar servicio
docker-compose up -d api

# En K8s:
kubectl rollout restart deployment/api -n mlops
```

### Actualizar DAGs

Los DAGs se actualizan automáticamente desde el volumen montado:

```bash
# Editar archivos en dags/
# Airflow detectará cambios automáticamente

# O reiniciar scheduler:
docker-compose restart airflow-scheduler
```

## Limpieza

```bash
# Detener servicios
docker-compose down

# Eliminar volúmenes (CUIDADO: elimina datos)
docker-compose down -v

# Eliminar imágenes
docker-compose down --rmi all

# Limpiar todo en K8s
kubectl delete namespace mlops
```

## Monitoreo Post-Despliegue

### Verificar Health de Servicios

```bash
./scripts/test_services.sh
```

### Monitorear Logs

```bash
# Docker Compose
docker-compose logs -f --tail=100

# Kubernetes
kubectl logs -f deployment/api -n mlops
```

### Verificar Métricas

- Prometheus: http://localhost:9090/targets
- Grafana: http://localhost:3000/dashboards
