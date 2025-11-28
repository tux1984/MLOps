# Guía de Inicio Rápido - Proyecto Final MLOps

Esta guía proporciona instrucciones paso a paso para desplegar y probar el sistema completo de predicción de precios inmobiliarios end-to-end.

## Requisitos Previos

Antes de comenzar, el usuario debe asegurarse de tener instalado:

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

El usuario debe crear un archivo `.env` en la raíz del proyecto con las siguientes variables:

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

Antes de iniciar, el usuario debe verificar que la API de datos esté disponible:

```bash
curl http://10.43.100.103:8000/health
```

Si la API no está disponible, el DAG de ingesta fallará.

## Flujo de Ejecución Completo

### Paso 1: Levantar Infraestructura Base

El usuario debe iniciar las bases de datos y servicios de almacenamiento:

```bash
docker-compose up -d postgres-raw postgres-clean postgres-airflow postgres-mlflow minio
```

Se debe esperar aproximadamente 30 segundos para que las bases de datos estén listas. Para verificar el estado:

```bash
docker-compose ps
```

Se deberían observar 5 servicios con estado "Up".

### Paso 2: Iniciar MLflow y Airflow

Se deben levantar los servicios de orquestación y tracking:

```bash
docker-compose up -d mlflow airflow-webserver
```

Se debe esperar 1-2 minutos para que Airflow complete su inicialización. Para verificar el acceso:

- Airflow: http://localhost:8080 (usuario: admin, contraseña: admin)
- MLflow: http://localhost:5000

### Paso 3: Ejecutar DAG de Ingesta

Desde la interfaz de Airflow (http://localhost:8080), el usuario debe:

1. Ir a la sección "DAGs"
2. Buscar el DAG `1_ingest_from_external_api`
3. Activar el toggle (ON) en la columna izquierda
4. Hacer clic en el botón "Trigger DAG" (play button)
5. Monitorear el progreso en la vista "Graph"

El DAG tomará aproximadamente 5-10 minutos dependiendo del volumen de datos.

**Validación**:

```bash
# Conectarse a la base RAW
docker exec -it postgres-raw psql -U mlops -d mlops_raw -c "SELECT COUNT(*) FROM raw_train;"
```

Se deberían observar registros insertados (ej. 1000+ registros).

### Paso 4: Ejecutar DAG de Preprocesamiento

Una vez completado el DAG de ingesta, el usuario debe:

1. En Airflow, buscar el DAG `2_clean_build`
2. Activarlo y ejecutarlo manualmente (Trigger DAG)
3. Este DAG tomará 3-5 minutos

El DAG aplicará feature engineering y normalizará los datos.

**Validación**:

```bash
# Conectarse a la base CLEAN
docker exec -it postgres-clean psql -U mlops -d mlops_clean -c "SELECT COUNT(*) FROM clean_train;"
```

Se debería observar el mismo número de registros con 30+ columnas.

### Paso 5: Ejecutar DAG de Entrenamiento

Con los datos limpios disponibles, el usuario debe:

1. En Airflow, buscar el DAG `3_train_and_register`
2. Activarlo y ejecutarlo manualmente
3. Este DAG tomará 10-15 minutos (entrena 3 modelos)

El mejor modelo será promovido automáticamente a stage "Production" en MLflow.

**Validación**:

El usuario debe acceder a MLflow (http://localhost:5000) y:

1. Hacer clic en "Models" en la barra superior
2. Se debería observar el modelo registrado (ej. "realtor_model")
3. Hacer clic en el modelo y verificar que hay una versión en stage "Production"

### Paso 6: Levantar API y Frontend

Ahora que hay un modelo en producción, se deben levantar los servicios de inferencia:

```bash
docker-compose up -d api frontend
```

Se debe esperar 30-60 segundos para que carguen. Para verificar el acceso:

- API: http://localhost:8000
- Frontend: http://localhost:8501

**Validación de API**:

```bash
# Health check
curl http://localhost:8000/health

# Información del modelo
curl http://localhost:8000/model-info
```

Se deberían observar respuestas JSON con status 200.

**Validación de Frontend**:

1. Abrir http://localhost:8501 en el navegador
2. Debería aparecer la interfaz con 4 tabs
3. En el sidebar, verificar que muestre "API Status: Connected"
4. Verificar que muestre información del modelo en producción

### Paso 7: Realizar Predicción

#### Opción A: Desde el Frontend (Recomendado)

1. Acceder a http://localhost:8501
2. En el Tab 1 "Predicción Individual", completar el formulario:
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
3. Hacer clic en "Predecir Precio"
4. Verificar que muestre un precio estimado

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

1. En el Frontend, acceder al Tab 3 "Explicabilidad SHAP"
2. Completar el formulario con los mismos datos del paso 7
3. Hacer clic en "Generar Explicación"
4. Verificar que aparezcan:
   - Gráfico Waterfall (top 15 features más importantes)
   - Gráfico Force (impacto positivo/negativo)
   - Tabla con valores SHAP ordenados

Esto permite comprender qué features contribuyeron más a la predicción.

### Paso 9: Monitorear con Grafana

Se deben levantar los servicios de observabilidad:

```bash
docker-compose up -d prometheus grafana
```

Para acceder a Grafana, el usuario debe:

1. Ir a http://localhost:3000
2. Usuario: admin, Contraseña: admin
3. Si solicita cambiar contraseña, se puede omitir
4. Ir a "Configuration" → "Data Sources"
5. Verificar que Prometheus esté configurado (http://prometheus:9090)
6. Ir a "Dashboards" → "Browse" y explorar los dashboards predefinidos

**Métricas disponibles**:

- Total de requests a la API
- Latencia de predicciones (P50, P95, P99)
- Predicciones por minuto
- Errores HTTP

### Paso 10: Pruebas de Carga con Locust

Se debe levantar Locust para simular tráfico:

```bash
docker-compose up -d locust
```

Para acceder a Locust, el usuario debe:

1. Ir a http://localhost:8089
2. Configurar:
   - Number of users: 10
   - Spawn rate: 2
   - Host: http://api:8000
3. Hacer clic en "Start swarming"
4. Monitorear las métricas en tiempo real:
   - RPS (Requests Per Second)
   - Response Time (ms)
   - Failure Rate

**Duración recomendada**: 5 minutos

**Validación**:

Mientras Locust está ejecutándose, el usuario debe ir a Grafana y observar cómo aumentan las métricas de la API.

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

El usuario puede utilizar este checklist para verificar que todo funciona correctamente:

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

Si se desea desplegar en Kubernetes en lugar de Docker Compose:

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

**Nota**: Los manifiestos de Kubernetes asumen que el usuario tiene un cluster funcional. Para desarrollo local, se recomienda usar Minikube o Kind.

## Monitoreo de GitHub Actions (CI/CD)

### ¿Qué son los GitHub Actions y para qué sirven?

GitHub Actions **NO reemplazan** Docker Compose. Son herramientas complementarias:

- **GitHub Actions**: Construye y publica imágenes Docker automáticamente cuando se hace `git push`
- **Docker Compose**: Levanta y ejecuta los servicios en la máquina local o servidor

**Analogía**: GitHub Actions es una fábrica que construye productos (imágenes Docker), mientras que Docker Compose es el lugar donde se usan esos productos (ejecuta los contenedores).

### ¿Cuándo se ejecutan los workflows?

Los workflows de GitHub Actions se activan automáticamente cuando:

1. Se hace `git push` a las ramas `main` o `master`
2. Se crea o actualiza un Pull Request
3. Se modifican archivos específicos (ej. `dags/**`, `services/api/**`)

### Cómo Ver las Ejecuciones de GitHub Actions

Si el proyecto está en GitHub, se puede monitorear las ejecuciones de los workflows:

#### Paso 1: Acceder a la Pestaña Actions

1. Acceder al repositorio en GitHub: `https://github.com/usuario/proyecto-final-mlops`
2. Hacer clic en la pestaña **"Actions"** en la parte superior
3. Se observará una lista de todas las ejecuciones recientes

#### Paso 2: Explorar una Ejecución Específica

1. Hacer clic en cualquier ejecución de la lista (ej. "Build Airflow Image")
2. Se observará el estado:
   - ✅ **Verde (Success)**: La imagen se construyó y publicó correctamente
   - ❌ **Rojo (Failure)**: Hubo errores en build, tests o linting
   - 🟡 **Amarillo (In Progress)**: Aún está ejecutándose
   - ⚪ **Gris (Cancelled)**: Se canceló manualmente

3. Hacer clic en el nombre del job (ej. "build")
4. Se desplegará cada paso del workflow:
   - Checkout code
   - Set up Docker Buildx
   - Login to DockerHub
   - Build and push
   - etc.

5. Hacer clic en cualquier paso para ver los logs detallados

#### Paso 3: Verificar Imágenes Publicadas en DockerHub

Después de una ejecución exitosa:

1. Acceder a DockerHub: `https://hub.docker.com/r/usuario/`
2. Se deberían observar los repositorios:
   - `usuario/proyecto-final-airflow`
   - `usuario/proyecto-final-api`
   - `usuario/proyecto-final-frontend`
   - `usuario/proyecto-final-mlflow`

3. Hacer clic en uno de los repositorios
4. En la pestaña "Tags", se observarán las etiquetas:
   - `latest`: Última versión construida
   - `sha-abc123`: Versión específica del commit

#### Paso 4: Usar las Imágenes Publicadas

Para usar las imágenes construidas por GitHub Actions en el `docker-compose.yml`:

```yaml
# Antes (build local)
services:
  airflow-webserver:
    build:
      context: ./dags
      dockerfile: Dockerfile.airflow

# Después (usar imagen de DockerHub)
services:
  airflow-webserver:
    image: usuario/proyecto-final-airflow:latest
```

Luego se debe ejecutar:

```bash
# Descargar última imagen desde DockerHub
docker-compose pull airflow-webserver

# Reiniciar con la nueva imagen
docker-compose up -d airflow-webserver
```

### Qué Validan los Workflows

Cada workflow ejecuta diferentes validaciones:

#### Workflow CI (`ci.yml`)
**Se ejecuta en**: Todos los pushes y PRs

**Validaciones**:
```bash
# 1. Tests unitarios
pytest tests/ --cov --cov-report=xml

# 2. Linting de código (estilo)
flake8 dags/ services/ --max-line-length=120

# 3. Escaneo de seguridad
bandit -r dags/ services/ -f json -o bandit-report.json

# 4. Verificación de tipos (opcional)
mypy dags/ --ignore-missing-imports
```

**Si falla**: No se construyen las imágenes Docker

#### Workflows de Build (Airflow, API, Frontend, MLflow)
**Se ejecuta en**: Pushes a main/master que modifican archivos relevantes

**Acciones**:
```bash
# 1. Construir imagen Docker
docker build -t usuario/proyecto-final-airflow:latest -f dags/Dockerfile.airflow .

# 2. Etiquetar con SHA del commit
docker tag usuario/proyecto-final-airflow:latest usuario/proyecto-final-airflow:sha-abc123

# 3. Publicar a DockerHub
docker push usuario/proyecto-final-airflow:latest
docker push usuario/proyecto-final-airflow:sha-abc123
```

**Si falla**: La imagen no se publica, el equipo no podrá usar la nueva versión

### Configurar Secrets en GitHub

Para que los workflows funcionen, el usuario debe configurar secrets:

1. Acceder al repositorio en GitHub
2. Settings → Secrets and variables → Actions
3. Hacer clic en "New repository secret"
4. Agregar estos secrets:

   - **DOCKERHUB_USERNAME**: Usuario de DockerHub
   - **DOCKERHUB_TOKEN**: Token de acceso de DockerHub
     - Para crear el token: DockerHub → Account Settings → Security → New Access Token

### Troubleshooting de GitHub Actions

#### Problema: Workflow falla en "Login to DockerHub"

**Causa**: Secrets no configurados o incorrectos

**Solución**:
```bash
# Verificar que los secrets existan
# Settings → Secrets and variables → Actions

# Crear nuevo token en DockerHub si es necesario
# DockerHub → Account Settings → Security → New Access Token
```

#### Problema: Workflow falla en tests

**Causa**: Código con errores de sintaxis o tests que no pasan

**Solución**:
```bash
# Ejecutar tests localmente antes de push
cd proyecto_final
pip install -r tests/requirements.txt
pytest tests/ -v

# Corregir errores y volver a hacer commit
```

#### Problema: Workflow falla en build de imagen

**Causa**: Dockerfile con errores o dependencias no disponibles

**Solución**:
```bash
# Probar build localmente
docker build -t test-airflow -f dags/Dockerfile.airflow .

# Ver logs detallados
docker build --progress=plain -t test-airflow -f dags/Dockerfile.airflow .
```

#### Problema: Workflow queda "stuck" en ejecución

**Causa**: Comando bloqueante o timeout largo

**Solución**:
```bash
# Cancelar la ejecución desde GitHub UI
# Actions → Click en la ejecución → Cancel workflow

# Revisar el último paso donde se quedó
# Ajustar timeouts en el workflow si es necesario
```

### Comandos Útiles para CI/CD

```bash
# Ver historial de imágenes locales
docker images | grep proyecto-final

# Limpiar imágenes antiguas
docker image prune -a

# Descargar última versión de todas las imágenes
docker-compose pull

# Reconstruir y reiniciar todos los servicios
docker-compose up -d --build

# Ver qué imagen está usando cada contenedor
docker-compose ps --format "table {{.Name}}\t{{.Image}}\t{{.Status}}"

# Forzar recreación de contenedores con nueva imagen
docker-compose up -d --force-recreate
```

### Flujo Recomendado de Trabajo

1. **Desarrollo local**: Realizar cambios en el código
2. **Prueba local**: `docker-compose restart <servicio>` para probar
3. **Commit y push**: `git add . && git commit -m "mensaje" && git push`
4. **Monitorear Actions**: Acceder a GitHub Actions y verificar que pase
5. **Esperar publicación**: Esperar a que la imagen se publique en DockerHub (2-5 min)
6. **Actualizar localmente**: `docker-compose pull <servicio> && docker-compose up -d <servicio>`
7. **Validar cambios**: Verificar que los cambios funcionen correctamente

### Diferencia Clave: Build vs Run

```
╔═══════════════════════════════════════════════════════════════╗
║                      GitHub Actions                           ║
║  ┌────────────────────────────────────────────────────┐      ║
║  │  FASE: BUILD (Construcción)                        │      ║
║  │  - Toma código fuente                              │      ║
║  │  - Ejecuta tests                                   │      ║
║  │  - Construye imagen Docker                         │      ║
║  │  - Publica a DockerHub                             │      ║
║  │  OUTPUT: Imagen lista para usar                    │      ║
║  └────────────────────────────────────────────────────┘      ║
╚═══════════════════════════════════════════════════════════════╝
                           │
                           │ docker pull
                           ▼
╔═══════════════════════════════════════════════════════════════╗
║                      Docker Compose                           ║
║  ┌────────────────────────────────────────────────────┐      ║
║  │  FASE: RUN (Ejecución)                             │      ║
║  │  - Descarga imagen de DockerHub                    │      ║
║  │  - Crea contenedor                                 │      ║
║  │  - Expone puertos                                  │      ║
║  │  - Monta volúmenes                                 │      ║
║  │  - Conecta a redes                                 │      ║
║  │  - MANTIENE SERVICIO CORRIENDO                     │      ║
║  │  OUTPUT: Servicio accesible en http://localhost    │      ║
║  └────────────────────────────────────────────────────┘      ║
╚═══════════════════════════════════════════════════════════════╝
```

**Analogía Final**:
- **GitHub Actions**: Fábrica de coches (construye el producto)
- **DockerHub**: Concesionario (almacena los productos)
- **Docker Compose**: Conductor (usa el coche para ir a lugares)

No se puede conducir un coche que solo está en la fábrica, y no se puede construir un coche nuevo cada vez que se desee ir a algún lugar. Ambos son necesarios pero en diferentes momentos.

## Próximos Pasos

Una vez completada esta guía, el usuario puede:

1. **Explorar MLflow**: Revisar experimentos, comparar modelos, analizar métricas
2. **Personalizar dashboards de Grafana**: Crear alertas y visualizaciones custom
3. **Optimizar modelos**: Modificar hiperparámetros en el DAG de entrenamiento
4. **Agregar features**: Implementar nuevas transformaciones en el DAG de preprocesamiento
5. **Implementar A/B testing**: Tener dos versiones de modelo en Staging y Production
6. **Configurar CI/CD**: Conectar GitHub Actions con el repositorio para deployments automáticos
7. **Explorar Argo CD**: Desplegar en Kubernetes con GitOps
8. **Monitorear GitHub Actions**: Configurar notificaciones de Slack/Email cuando los builds fallen
9. **Implementar workflow de release**: Crear tags y releases automáticas cuando se actualice la versión

## Soporte

Si se encuentran problemas no cubiertos en esta guía:

1. Revisar los logs detallados de cada servicio
2. Consultar la documentación adicional en `docs/`
3. Revisar el archivo `COMPONENTES_IMPLEMENTADOS.md` para detalles técnicos
4. Contactar al equipo del proyecto

---

**Última actualización**: Noviembre 2024  
**Versión**: 1.0
