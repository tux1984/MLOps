# Guía de Inicio Rápido - Proyecto Final MLOps

Esta guía proporciona instrucciones paso a paso para desplegar y probar el sistema completo de predicción de precios inmobiliarios end-to-end.

## Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

- Docker 20.10+ y Docker Compose 2.0+
- 8 GB de RAM disponibles
- 20 GB de espacio en disco
- Conexión a internet para descargar imágenes y datos

Para verificar las versiones:

```bash
docker --version
docker-compose --version
```

## Preparación del Entorno

### 1. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```bash
# Configuración de PostgreSQL
POSTGRES_USER=mlops
POSTGRES_PASSWORD=mlops123
POSTGRES_DB_RAW=mlops_raw
POSTGRES_DB_CLEAN=mlops_clean
POSTGRES_DB_AIRFLOW=airflow_metadata
POSTGRES_DB_MLFLOW=mlflow_metadata

# Puertos de bases de datos
POSTGRES_PORT_RAW=5432
POSTGRES_PORT_CLEAN=5433
POSTGRES_PORT_AIRFLOW=5434
POSTGRES_PORT_MLFLOW=5435

# Configuración de Airflow
AIRFLOW_EXECUTOR=LocalExecutor
AIRFLOW_LOAD_EXAMPLES=False
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=admin
AIRFLOW_ADMIN_EMAIL=admin@mlops.com

# Configuración de MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin

# Configuración de MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_BUCKET=mlflow

# Configuración de API Externa
API_BASE_URL=http://10.43.100.103:8000
GROUP_NUMBER=3

# Puertos de servicios
AIRFLOW_PORT=8080
MLFLOW_PORT=5000
API_PORT=8000
FRONTEND_PORT=8501
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
LOCUST_PORT=8089
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
```

### 2. Verificar la API Externa

Antes de iniciar, verifica que la API del profesor esté disponible:

```bash
curl http://10.43.100.103:8000/health
```

Si la API no está disponible, el DAG de ingesta fallará. Contacta al profesor o actualiza la URL en `.env`.

## Flujo de Ejecución Completo

### Paso 1: Levantar Infraestructura Base

Inicia las bases de datos y servicios de almacenamiento:

```bash
docker-compose up -d postgres-raw postgres-clean postgres-airflow postgres-mlflow minio
```

Espera aproximadamente 30 segundos para que las bases de datos estén listas. Verifica el estado:

```bash
docker-compose ps
```

Deberías ver 5 servicios con estado "Up".

### Paso 2: Iniciar MLflow y Airflow

Levanta los servicios de orquestación y tracking:

```bash
docker-compose up -d mlflow airflow-webserver
```

Espera 1-2 minutos para que Airflow complete su inicialización. Verifica acceso:

- Airflow: http://localhost:8080 (usuario: admin, contraseña: admin)
- MLflow: http://localhost:5000

### Paso 3: Ejecutar DAG de Ingesta

Desde la interfaz de Airflow (http://localhost:8080):

1. Ve a la sección "DAGs"
2. Busca el DAG `1_ingest_from_external_api`
3. Activa el toggle (ON) en la columna izquierda
4. Haz clic en el botón "Trigger DAG" (play button)
5. Monitorea el progreso en la vista "Graph"

El DAG tomará aproximadamente 5-10 minutos dependiendo del volumen de datos.

**Validación**:

```bash
# Conectarse a la base RAW
docker exec -it postgres-raw psql -U mlops -d mlops_raw -c "SELECT COUNT(*) FROM raw_train;"
```

Deberías ver registros insertados (ej. 1000+ registros).

### Paso 4: Ejecutar DAG de Preprocesamiento

Una vez completado el DAG de ingesta:

1. En Airflow, busca el DAG `2_clean_build`
2. Actívalo y ejecútalo manualmente (Trigger DAG)
3. Este DAG tomará 3-5 minutos

El DAG aplicará feature engineering y normalizará los datos.

**Validación**:

```bash
# Conectarse a la base CLEAN
docker exec -it postgres-clean psql -U mlops -d mlops_clean -c "SELECT COUNT(*) FROM clean_train;"
```

Deberías ver el mismo número de registros con 30+ columnas.

### Paso 5: Ejecutar DAG de Entrenamiento

Con los datos limpios disponibles:

1. En Airflow, busca el DAG `3_train_and_register`
2. Actívalo y ejecútalo manualmente
3. Este DAG tomará 10-15 minutos (entrena 3 modelos)

El mejor modelo será promovido automáticamente a stage "Production" en MLflow.

**Validación**:

Ve a MLflow (http://localhost:5000):

1. Haz clic en "Models" en la barra superior
2. Deberías ver el modelo registrado (ej. "realtor_model")
3. Haz clic en el modelo y verifica que hay una versión en stage "Production"

### Paso 6: Levantar API y Frontend

Ahora que hay un modelo en producción, levanta los servicios de inferencia:

```bash
docker-compose up -d api frontend
```

Espera 30-60 segundos para que carguen. Verifica acceso:

- API: http://localhost:8000
- Frontend: http://localhost:8501

**Validación de API**:

```bash
# Health check
curl http://localhost:8000/health

# Información del modelo
curl http://localhost:8000/model-info
```

Deberías ver respuestas JSON con status 200.

**Validación de Frontend**:

1. Abre http://localhost:8501 en tu navegador
2. Debería aparecer la interfaz con 4 tabs
3. En el sidebar, verifica que muestre "API Status: Connected"
4. Verifica que muestre información del modelo en producción

### Paso 7: Realizar Predicción

#### Opción A: Desde el Frontend (Recomendado)

1. Ve a http://localhost:8501
2. En el Tab 1 "Predicción Individual", completa el formulario:
   - Brokered By: Century 21
   - Status: for_sale
   - Bed: 3
   - Bath: 2
   - Acre Lot: 0.25
   - Street: 123 Main St
   - City: Miami
   - State: Florida
   - Zip Code: 33101
   - House Size: 1500
   - Previous Sold Date: 2020-01-15
3. Haz clic en "Predecir Precio"
4. Verifica que muestre un precio estimado

#### Opción B: Desde la API (curl)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "brokered_by": "Century 21",
    "status": "for_sale",
    "bed": 3,
    "bath": 2,
    "acre_lot": 0.25,
    "street": "123 Main St",
    "city": "Miami",
    "state": "Florida",
    "zip_code": "33101",
    "house_size": 1500,
    "prev_sold_date": "2020-01-15"
  }'
```

Respuesta esperada:

```json
{
  "predicted_price": 345678.90,
  "model_name": "realtor_model",
  "model_version": "1",
  "model_stage": "Production"
}
```

### Paso 8: Explorar Explicabilidad SHAP

1. En el Frontend, ve al Tab 3 "Explicabilidad SHAP"
2. Completa el formulario con los mismos datos del paso 7
3. Haz clic en "Generar Explicación"
4. Verifica que aparezcan:
   - Gráfico Waterfall (top 15 features más importantes)
   - Gráfico Force (impacto positivo/negativo)
   - Tabla con valores SHAP ordenados

Esto te permite entender qué features contribuyeron más a la predicción.

### Paso 9: Monitorear con Grafana

Levanta los servicios de observabilidad:

```bash
docker-compose up -d prometheus grafana
```

Accede a Grafana:

1. Ve a http://localhost:3000
2. Usuario: admin, Contraseña: admin
3. Si pide cambiar contraseña, puedes saltarlo
4. Ve a "Configuration" → "Data Sources"
5. Verifica que Prometheus esté configurado (http://prometheus:9090)
6. Ve a "Dashboards" → "Browse" y explora los dashboards predefinidos

**Métricas disponibles**:

- Total de requests a la API
- Latencia de predicciones (P50, P95, P99)
- Predicciones por minuto
- Errores HTTP

### Paso 10: Pruebas de Carga con Locust

Levanta Locust para simular tráfico:

```bash
docker-compose up -d locust
```

Accede a Locust:

1. Ve a http://localhost:8089
2. Configura:
   - Number of users: 10
   - Spawn rate: 2
   - Host: http://api:8000
3. Haz clic en "Start swarming"
4. Monitorea las métricas en tiempo real:
   - RPS (Requests Per Second)
   - Response Time (ms)
   - Failure Rate

**Duración recomendada**: 5 minutos

**Validación**:

Mientras Locust está ejecutándose, ve a Grafana y observa cómo aumentan las métricas de la API.

## Comandos Útiles

### Ver logs de un servicio

```bash
# Logs de Airflow
docker-compose logs -f airflow-webserver

# Logs de API
docker-compose logs -f api

# Logs de MLflow
docker-compose logs -f mlflow

# Logs de un DAG específico (desde dentro del contenedor de Airflow)
docker exec -it airflow-webserver cat /opt/airflow/logs/dag_id=1_ingest_from_external_api/run_id=manual__2024-11-20T10:00:00/task_id=fetch_data_from_api/attempt=1.log
```

### Reiniciar un servicio

```bash
docker-compose restart <servicio>
```

### Detener todos los servicios

```bash
docker-compose down
```

### Detener y eliminar volúmenes (reinicio completo)

```bash
docker-compose down -v
```

**Advertencia**: Esto eliminará todas las bases de datos y modelos entrenados.

### Conectarse a una base de datos

```bash
# Base RAW
docker exec -it postgres-raw psql -U mlops -d mlops_raw

# Base CLEAN
docker exec -it postgres-clean psql -U mlops -d mlops_clean

# Base MLflow
docker exec -it postgres-mlflow psql -U mlops -d mlflow_metadata
```

### Verificar estado de todos los servicios

```bash
docker-compose ps
```

### Ver uso de recursos

```bash
docker stats
```

### Ejecutar tests automatizados

```bash
# Tests de la API
docker-compose run --rm api pytest /app/tests/

# Tests del pipeline completo
docker-compose run --rm airflow-webserver pytest /opt/airflow/tests/
```

## Troubleshooting

### Problema: Airflow no arranca

**Síntoma**: El contenedor `airflow-webserver` se reinicia constantemente.

**Solución**:

```bash
# Ver logs
docker-compose logs airflow-webserver

# Verificar que la base de datos de Airflow esté lista
docker exec -it postgres-airflow psql -U mlops -d airflow_metadata -c "\dt"

# Si la base está vacía, reinicializar
docker-compose down
docker-compose up -d postgres-airflow
docker-compose up -d airflow-webserver
```

### Problema: DAG de ingesta falla

**Síntoma**: DAG `1_ingest_from_external_api` falla en la tarea `fetch_data_from_api`.

**Solución**:

```bash
# Verificar conectividad con la API externa
docker exec -it airflow-webserver curl http://10.43.100.103:8000/health

# Si no hay conectividad, revisar la variable GROUP_NUMBER en .env
# Verificar logs del DAG
docker-compose logs airflow-webserver | grep "ingest_from_external_api"
```

### Problema: API no carga el modelo

**Síntoma**: `curl http://localhost:8000/health` retorna `model_loaded: false`.

**Solución**:

```bash
# Verificar que hay un modelo en Production en MLflow
curl http://localhost:5000/api/2.0/mlflow/registered-models/search

# Si no hay modelo, ejecutar DAG 3 primero
# Si hay modelo, reiniciar API
docker-compose restart api
docker-compose logs -f api
```

### Problema: Frontend no se conecta a la API

**Síntoma**: En el frontend, el sidebar muestra "API Status: Disconnected".

**Solución**:

```bash
# Verificar que la API esté levantada
curl http://localhost:8000/health

# Verificar que el frontend pueda alcanzar la API (desde dentro del contenedor)
docker exec -it frontend curl http://api:8000/health

# Si falla, revisar la red de Docker
docker network inspect proyecto_final_default
```

### Problema: MinIO no accesible

**Síntoma**: MLflow falla al guardar artefactos con error "Unable to connect to endpoint".

**Solución**:

```bash
# Verificar que MinIO esté levantado
docker-compose ps minio

# Crear bucket manualmente si no existe
docker exec -it minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker exec -it minio mc mb local/mlflow

# Reiniciar MLflow
docker-compose restart mlflow
```

### Problema: Locust no puede alcanzar la API

**Síntoma**: Locust muestra 100% de errores de conexión.

**Solución**:

```bash
# Verificar que Locust y API estén en la misma red
docker network inspect proyecto_final_default | grep -E "locust|api"

# En la UI de Locust, asegúrate de usar http://api:8000 (nombre del servicio, no localhost)
```

### Problema: Prometheus no recolecta métricas

**Síntoma**: En Grafana, las gráficas están vacías.

**Solución**:

```bash
# Verificar que Prometheus pueda alcanzar la API
docker exec -it prometheus wget -O- http://api:8000/metrics

# Revisar configuración de Prometheus
docker exec -it prometheus cat /etc/prometheus/prometheus.yml

# Verificar targets en Prometheus UI
# Ve a http://localhost:9090/targets
```

### Problema: Memoria insuficiente

**Síntoma**: Los servicios se matan con código 137 (OOM Killed).

**Solución**:

```bash
# Ver uso de memoria
docker stats

# Aumentar memoria disponible para Docker Desktop
# Settings → Resources → Memory → 8 GB mínimo

# Alternativamente, levantar servicios por partes
docker-compose up -d postgres-raw postgres-clean
docker-compose up -d airflow-webserver mlflow
# ... esperar entre grupos
```

## Checklist de Validación End-to-End

Usa este checklist para verificar que todo funciona correctamente:

- [ ] **Infraestructura Base**
  - [ ] 4 bases de datos PostgreSQL levantadas y accesibles
  - [ ] MinIO levantado y bucket `mlflow` creado

- [ ] **Airflow**
  - [ ] Airflow UI accesible en http://localhost:8080
  - [ ] 3 DAGs visibles: ingesta, preprocesamiento, entrenamiento

- [ ] **Pipeline de Datos**
  - [ ] DAG 1 ejecutado con éxito (datos en raw_train)
  - [ ] DAG 2 ejecutado con éxito (datos en clean_train con 30+ columnas)
  - [ ] DAG 3 ejecutado con éxito (modelo registrado en MLflow)

- [ ] **MLflow**
  - [ ] MLflow UI accesible en http://localhost:5000
  - [ ] Al menos 1 experimento con 3 runs (3 modelos entrenados)
  - [ ] Modelo en stage "Production" visible en Model Registry

- [ ] **API de Inferencia**
  - [ ] API responde en http://localhost:8000
  - [ ] `/health` retorna `model_loaded: true`
  - [ ] `/model-info` retorna versión del modelo en Production
  - [ ] `/predict` retorna predicción válida (número positivo)

- [ ] **Frontend**
  - [ ] Frontend accesible en http://localhost:8501
  - [ ] Sidebar muestra "API Status: Connected"
  - [ ] Tab 1 permite hacer predicción individual
  - [ ] Tab 2 permite cargar CSV y descargar resultados
  - [ ] Tab 3 muestra gráficos SHAP correctamente

- [ ] **Observabilidad**
  - [ ] Prometheus accesible en http://localhost:9090
  - [ ] Grafana accesible en http://localhost:3000
  - [ ] Grafana muestra métricas de la API

- [ ] **Pruebas de Carga**
  - [ ] Locust accesible en http://localhost:8089
  - [ ] Locust puede ejecutar pruebas contra la API
  - [ ] Métricas en Grafana reflejan tráfico de Locust

## Notas sobre Kubernetes

Si deseas desplegar en Kubernetes en lugar de Docker Compose:

1. **Crear el namespace**:

```bash
kubectl apply -f kubernetes/namespace.yaml
```

2. **Crear PersistentVolumeClaims**:

```bash
kubectl apply -f kubernetes/pvc.yaml
```

3. **Desplegar bases de datos**:

```bash
kubectl apply -f kubernetes/databases.yaml
```

4. **Desplegar MLflow**:

```bash
kubectl apply -f kubernetes/mlflow.yaml
```

5. **Desplegar Airflow, API y Frontend**:

```bash
kubectl apply -f kubernetes/api.yaml
kubectl apply -f kubernetes/frontend.yaml
```

6. **Configurar Argo CD para GitOps**:

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Esperar a que Argo CD esté listo
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

# Aplicar Project y Applications
kubectl apply -f argocd/project.yaml
kubectl apply -f argocd/applications.yaml
```

7. **Acceder a servicios**:

```bash
# Port-forward de Airflow
kubectl port-forward -n mlops svc/airflow 8080:8080

# Port-forward de MLflow
kubectl port-forward -n mlops svc/mlflow 5000:5000

# Port-forward de API
kubectl port-forward -n mlops svc/api 8000:8000

# Port-forward de Frontend
kubectl port-forward -n mlops svc/frontend 8501:8501
```

**Nota**: Los manifiestos de Kubernetes asumen que tienes un cluster funcional. Para desarrollo local, considera usar Minikube o Kind.

## Próximos Pasos

Una vez que hayas completado esta guía, puedes:

1. **Explorar MLflow**: Revisar experimentos, comparar modelos, analizar métricas
2. **Personalizar dashboards de Grafana**: Crear alertas y visualizaciones custom
3. **Optimizar modelos**: Modificar hiperparámetros en el DAG de entrenamiento
4. **Agregar features**: Implementar nuevas transformaciones en el DAG de preprocesamiento
5. **Implementar A/B testing**: Tener dos versiones de modelo en Staging y Production
6. **Configurar CI/CD**: Conectar GitHub Actions con tu repositorio para deployments automáticos
7. **Explorar Argo CD**: Desplegar en Kubernetes con GitOps

## Soporte

Si encuentras problemas no cubiertos en esta guía:

1. Revisa los logs detallados de cada servicio
2. Consulta la documentación adicional en `docs/`
3. Revisa el archivo `COMPONENTES_IMPLEMENTADOS.md` para detalles técnicos
4. Contacta al equipo del proyecto

---

**Última actualización**: Noviembre 2024  
**Versión**: 1.0
