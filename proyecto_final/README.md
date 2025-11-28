# Proyecto Final MLOps - Sistema de Predicción de Precios Inmobiliarios

Sistema MLOps completo end-to-end para la predicción de precios de propiedades inmobiliarias utilizando el dataset de Realtor. El proyecto implementa un pipeline automatizado desde la ingesta de datos hasta el despliegue de modelos en producción, con integración continua y despliegue continuo (CI/CD).

## Descripción

Este proyecto implementa un sistema de Machine Learning Ops que cubre el ciclo de vida completo de un modelo de Machine Learning, desde la recolección de datos hasta el servicio de inferencia en producción. El sistema está diseñado para operar de manera automatizada, escalable y observable, siguiendo las mejores prácticas de MLOps.

### Objetivo del Modelo

Predecir el precio de propiedades inmobiliarias (regresión) basándose en características como número de habitaciones, baños, tamaño del terreno, ubicación, entre otras variables del dataset de Realtor.

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Kubernetes/Docker Compose                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐      ┌─────────────┐      ┌──────────────┐          │
│  │   API    │─────▶│  RAW DATA   │─────▶│  CLEAN DATA  │          │
│  │ Externa  │      │ (PostgreSQL)│      │ (PostgreSQL) │          │
│  │ Profesor │      └─────────────┘      └──────────────┘          │
│  └──────────┘             │                      │                 │
│       │                   │                      │                 │
│       ▼                   ▼                      ▼                 │
│  ┌─────────────────────────────────────────────────┐              │
│  │              Airflow Orchestrator               │              │
│  │  ┌──────────────────────────────────────────┐  │              │
│  │  │ DAG 1: Ingesta desde API Externa        │  │              │
│  │  │ DAG 2: Preprocesamiento y Limpieza      │  │              │
│  │  │ DAG 3: Entrenamiento y Registro          │  │              │
│  │  └──────────────────────────────────────────┘  │              │
│  └─────────────────────────────────────────────────┘              │
│                           │                                        │
│                           ▼                                        │
│                    ┌─────────────┐                                │
│                    │   MLflow    │                                │
│                    │  Tracking   │                                │
│                    │   Server    │                                │
│                    └─────────────┘                                │
│                           │                                        │
│                           ▼                                        │
│                    ┌─────────────┐                                │
│                    │   Model     │                                │
│                    │  Registry   │                                │
│                    │ (Production)│                                │
│                    └─────────────┘                                │
│                           │                                        │
│          ┌────────────────┴────────────────┐                      │
│          ▼                                  ▼                      │
│    ┌──────────┐                      ┌──────────┐                │
│    │ FastAPI  │                      │Streamlit │                │
│    │   API    │◄────────────────────▶│    UI    │                │
│    └──────────┘                      └──────────┘                │
│          │                                                         │
│          ▼                                                         │
│    ┌──────────┐         ┌──────────┐         ┌──────────┐       │
│    │Prometheus│────────▶│ Grafana  │         │  Locust  │       │
│    │ Metrics  │         │Dashboard │         │Load Test │       │
│    └──────────┘         └──────────┘         └──────────┘       │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Componentes del Sistema

### 1. Orquestación con Apache Airflow

Airflow gestiona la ejecución automatizada de tres DAGs secuenciales:

#### DAG 1: Ingesta de Datos desde API Externa
**Archivo**: `dags/1_ingest_from_external_api.py`

Consume la API del profesor ubicada en `http://10.43.100.103:8000` para obtener datos de propiedades inmobiliarias. Cada ejecución realiza un request incremental y almacena los datos en la base de datos RAW.

**Funcionalidades**:
- Obtención del próximo número de request desde la base de datos
- Llamada a la API con parámetros de grupo y request count
- Cálculo de hash MD5 por registro para deduplicación
- Inserción paralela en tablas raw_train, raw_validation y raw_test
- Logging detallado de requests en tabla api_request_log
- Manejo de errores y timeouts (300 segundos)
- Detección automática de finalización de datos (código 404)

**Decisiones técnicas**:
- Se utiliza hash MD5 para garantizar que no se inserten registros duplicados
- Los requests se loguean completamente para trazabilidad y debugging
- El DAG está configurado para ejecutarse diariamente o bajo demanda manual

#### DAG 2: Preprocesamiento y Limpieza
**Archivo**: `dags/2_clean_build.py`

Transforma los datos crudos en features listas para entrenamiento, aplicando técnicas de feature engineering y normalización.

**Funcionalidades**:
- Carga paralela de datos RAW (train, validation, test)
- Conversión de variables categóricas a encodings numéricos
- Creación de features derivados:
  - price_per_sqft (precio por pie cuadrado)
  - bed_bath_ratio (ratio habitaciones/baños)
  - sqft_per_acre (pies cuadrados por acre)
  - days_since_prev_sale (días desde última venta)
  - Features temporales (año, mes, trimestre de venta previa)
  - Agregaciones por ciudad, estado y código postal
- Normalización con Z-score para features numéricos
- Guardado en tablas clean_train, clean_validation, clean_test
- Almacenamiento de encodings en tabla encoding_mappings para consistencia
- Registro de estadísticas de preprocesamiento

**Decisiones técnicas**:
- Se mantienen mappings de encodings en base de datos para aplicar consistentemente en inferencia
- Las estadísticas de normalización se guardan para reutilización
- El procesamiento es paralelo para optimizar tiempos de ejecución

#### DAG 3: Entrenamiento y Registro de Modelos
**Archivo**: `dags/3_train_and_register.py`

Entrena múltiples modelos de regresión y selecciona el mejor basándose en métricas de evaluación.

**Funcionalidades**:
- Entrenamiento de tres modelos:
  - Random Forest Regressor (n_estimators=200, max_depth=20)
  - Gradient Boosting Regressor (n_estimators=200, max_depth=5)
  - Linear Regression (solver=lbfgs)
- Registro de experimentos en MLflow con:
  - Hiperparámetros
  - Métricas (RMSE, MAE, R², MAPE)
  - Feature importance
  - Gráficos de residuos y predicciones
- Selección automática del mejor modelo por RMSE
- Evaluación final en conjunto de test
- Promoción automática a stage Production en MLflow
- Archivado de modelo anterior en Production
- Logging consolidado de resumen de entrenamiento

**Decisiones técnicas**:
- RMSE se usa como métrica principal por su sensibilidad a outliers
- Se registra el modelo completo (pipeline + scaler + modelo)
- La promoción a Production es automática sin intervención manual
- Solo un modelo puede estar en Production simultáneamente

### 2. MLflow: Tracking y Registry

MLflow proporciona el seguimiento de experimentos y el registro centralizado de modelos.

**Configuración**:
- Backend store: PostgreSQL para metadatos
- Artifact store: MinIO (S3-compatible) para modelos y artefactos
- Tracking URI: `http://mlflow:5000`
- S3 Endpoint: `http://minio:9000`

**Funcionalidades**:
- Registro de hiperparámetros y métricas por experimento
- Almacenamiento de artefactos (modelos serializados, gráficos, logs)
- Model Registry con stages: None, Staging, Production, Archived
- Versionado automático de modelos
- API REST para consulta de modelos y experimentos

**Decisiones técnicas**:
- PostgreSQL como backend garantiza persistencia y consultas eficientes
- MinIO simula S3 para desarrollo local con compatibilidad cloud
- El Model Registry separa experimentación de producción

### 3. API de Inferencia con FastAPI

API REST que consume el modelo en stage Production desde MLflow.

**Archivo**: `services/api/main.py`

**Endpoints implementados**:
- `GET /`: Endpoint raíz con información del servicio
- `GET /health`: Health check con validación de modelo cargado
- `GET /model-info`: Información del modelo actual (nombre, versión, stage)
- `POST /predict`: Predicción individual de precio de propiedad
- `POST /predict-batch`: Predicción en lote (múltiples propiedades)
- `POST /explain`: Explicación SHAP de predicción individual
- `GET /metrics`: Métricas de Prometheus para observabilidad
- `POST /reload-model`: Recarga manual del modelo desde MLflow

**Características**:
- Carga dinámica del modelo en Production sin cambios de código
- Validación de entrada con Pydantic schemas
- Manejo de errores con mensajes descriptivos
- Exportación de métricas: contador de requests, histograma de latencia
- CORS habilitado para consumo desde frontend

**Decisiones técnicas**:
- MlflowClient se inicializa al arrancar el servicio
- El modelo se carga en memoria una sola vez (lazy loading)
- Las predicciones retornan también la versión del modelo usado
- SHAP values se calculan on-demand para explicabilidad

### 4. Frontend con Streamlit

Interfaz gráfica interactiva para consumo del modelo.

**Archivo**: `services/frontend/app.py`

**Funcionalidades**:
- Tab 1: Predicción Individual
  - Formulario con 22 campos de entrada
  - Validación de rangos
  - Visualización del precio predicho
  - Información del modelo usado
- Tab 2: Predicción en Batch
  - Upload de archivo CSV
  - Preview de datos cargados
  - Descarga de resultados con predicciones
- Tab 3: Explicabilidad SHAP
  - Formulario de entrada
  - Cálculo de valores SHAP
  - Gráfico Waterfall (top 15 features)
  - Gráfico Force (impacto positivo/negativo)
  - Tabla de valores SHAP ordenados
- Tab 4: Analytics
  - Placeholder para dashboards futuros

**Sidebar**:
- Estado de conexión con API
- Información del modelo en producción
- Descripción del proyecto

**Decisiones técnicas**:
- Streamlit permite desarrollo rápido de UI sin JavaScript
- La UI se comunica con API vía requests HTTP
- SHAP values se obtienen desde API para centralizar lógica
- Layout responsive con columnas y tabs

### 5. Bases de Datos PostgreSQL

El sistema utiliza cuatro bases de datos PostgreSQL separadas:

#### Base de Datos RAW (Puerto 5432)
**Archivo**: `initdb/01_create_raw_db_realtor.sql`

Almacena datos sin procesar desde la API externa.

**Tablas principales**:
- `raw_train`: Datos de entrenamiento con 12 columnas del dataset realtor
- `raw_validation`: Datos de validación
- `raw_test`: Datos de prueba
- `api_request_log`: Registro de llamadas a la API
- `ingestion_summary`: Resumen de cada ingesta

**Decisión técnica**: Separación de RAW permite rollback y reprocessing completo si es necesario.

#### Base de Datos CLEAN (Puerto 5433)
**Archivo**: `initdb/02_create_clean_db_realtor.sql`

Almacena datos preprocesados listos para ML.

**Tablas principales**:
- `clean_train`: Features procesados (30+ columnas)
- `clean_validation`: Features de validación
- `clean_test`: Features de prueba
- `encoding_mappings`: Mappings categóricos consistentes
- `preprocessing_statistics`: Stats para normalización

**Decisión técnica**: CLEAN DB facilita re-entrenamiento sin reprocesar RAW cada vez.

#### Base de Datos Airflow (Puerto 5434)
Base de datos para metadatos de Airflow (DAG runs, task instances, logs).

#### Base de Datos MLflow (Puerto 5435)
**Archivo**: `initdb/03_create_mlflow_db.sql`

Backend store para metadatos de MLflow (experimentos, runs, modelos registrados).

### 6. MinIO: Almacenamiento de Artefactos

MinIO proporciona almacenamiento S3-compatible para artefactos de MLflow.

**Configuración**:
- API Port: 9000
- Console Port: 9001
- Bucket: `mlflow`
- Credenciales: minioadmin/minioadmin

**Contenido almacenado**:
- Modelos serializados (.pkl)
- Logs de entrenamiento
- Gráficos y visualizaciones
- Feature importance plots

**Decisión técnica**: MinIO es compatible con boto3 y permite migración fácil a S3 real en producción.

### 7. Observabilidad: Prometheus y Grafana

#### Prometheus
**Archivo**: `config/prometheus/prometheus.yml`

Recolecta métricas de la API cada 15 segundos.

**Métricas disponibles**:
- `api_requests_total`: Contador de requests totales
- `api_request_duration_seconds`: Histograma de latencia
- `predictions_total`: Total de predicciones realizadas
- `model_version`: Versión del modelo actualmente en uso

#### Grafana
**Configuración**:
- Puerto: 3000
- Datasource: Prometheus
- Credenciales: admin/admin

**Dashboards sugeridos**:
- Request rate por minuto
- Latencia P50, P95, P99
- Predicciones por hora
- Tasa de errores

**Decisión técnica**: Prometheus + Grafana es el estándar de facto para observabilidad de microservicios.

### 8. Locust: Pruebas de Carga

**Archivo**: `services/locust/locustfile.py`

Simula carga concurrente sobre la API para determinar capacidad máxima.

**Escenarios de prueba**:
- `predict_single`: 80% del tráfico, predicción individual
- `predict_batch`: 10% del tráfico, predicción en batch
- `explain_prediction`: 5% del tráfico, explicación SHAP
- `health_check`: 3% del tráfico, health check
- `model_info`: 2% del tráfico, info del modelo

**Métricas medidas**:
- RPS (requests per second)
- Latencia mediana, P95, P99
- Tasa de errores
- Usuarios concurrentes soportados

**Decisión técnica**: Locust permite scripts Python para pruebas complejas y customizables.

### 9. GitHub Actions: CI/CD

**Directorio**: `.github/workflows/`

Automatización de construcción y despliegue de imágenes Docker.

**Workflows implementados**:
- `build-airflow.yml`: Build de imagen de Airflow
- `build-api.yml`: Build de imagen de API
- `build-frontend.yml`: Build de imagen de Frontend
- `build-mlflow.yml`: Build de imagen de MLflow
- `ci.yml`: Tests, linting y security scan

**Flujo CI/CD**:
1. Desarrollador hace push a main/master
2. GitHub Actions ejecuta tests y linting
3. Si pasa, construye imagen Docker
4. Pushea imagen a DockerHub con tags (latest, sha)
5. Argo CD detecta nueva imagen
6. Argo CD sincroniza y actualiza deployment en Kubernetes

**Decisión técnica**: Separación de workflows por servicio permite deployments independientes.

### 10. Argo CD: Despliegue Continuo

**Directorio**: `argocd/`

GitOps para despliegue automático en Kubernetes.

**Componentes**:
- `project.yaml`: AppProject con permisos y políticas
- `application.yaml`: Application principal
- `applications.yaml`: Applications por microservicio

**Política de sincronización**:
- Automated sync habilitado
- Prune: elimina recursos no definidos en Git
- SelfHeal: corrige desviaciones del estado deseado
- Excepciones: Airflow y Databases con sync manual

**Decisión técnica**: Argo CD garantiza que el cluster siempre refleje el estado definido en Git (GitOps).

## Integración Continua y Despliegue Continuo (CI/CD)

### Diferencia entre GitHub Actions y Docker Compose

Es importante entender que GitHub Actions y Docker Compose cumplen roles complementarios pero diferentes en el ciclo de vida del proyecto:

#### GitHub Actions (Construcción y Publicación)

**Propósito**: Automatizar la construcción, pruebas y publicación de imágenes Docker cuando hay cambios en el código.

**Responsabilidades**:
- Se activa automáticamente con `git push` a las ramas main/master
- Ejecuta tests unitarios y de integración
- Realiza análisis estático de código (linting)
- Ejecuta escaneo de seguridad de dependencias
- **Construye** las imágenes Docker desde los Dockerfiles
- **Publica** las imágenes construidas a DockerHub con etiquetas (latest, sha, versión)
- Genera artefactos de build y reportes de tests

**Lo que NO hace**:
- No levanta servicios en ejecución
- No expone puertos para acceso de usuarios
- No ejecuta los DAGs de Airflow
- No mantiene bases de datos persistentes
- No proporciona acceso a interfaces web (Airflow UI, MLflow UI, etc.)

**Ubicación de ejecución**: Servidores de GitHub (GitHub-hosted runners) o runners auto-hospedados

#### Docker Compose (Orquestación y Ejecución)

**Propósito**: Levantar, orquestar y mantener en ejecución todos los servicios del sistema en un entorno específico.

**Responsabilidades**:
- Descarga imágenes Docker desde DockerHub o las construye localmente
- **Levanta** todos los contenedores definidos en `docker-compose.yml`
- Crea y gestiona redes internas para comunicación entre servicios
- Crea y monta volúmenes para persistencia de datos
- **Expone puertos** en la máquina host (8080, 5000, 8501, etc.)
- Conecta servicios entre sí (ej. API con PostgreSQL, MLflow con MinIO)
- Mantiene los servicios corriendo y puede reiniciarlos automáticamente
- Permite acceso a logs, shells de contenedores, y comandos de gestión

**Lo que SÍ hace**:
- Proporciona el entorno completo para desarrollo y testing
- Permite ejecutar los DAGs de Airflow manualmente o programados
- Mantiene bases de datos activas y accesibles
- Expone interfaces web para interacción
- Facilita debugging y desarrollo local

**Ubicación de ejecución**: Tu máquina local, servidor de desarrollo, o servidor de producción

### Flujo Completo de Desarrollo y Despliegue

```
┌──────────────────────────────────────────────────────────────────┐
│                    FASE 1: DESARROLLO                            │
├──────────────────────────────────────────────────────────────────┤
│  1. Desarrollador modifica código en dags/1_ingest_*.py         │
│  2. Prueba localmente: docker-compose restart airflow-webserver  │
│  3. Verifica funcionamiento en http://localhost:8080             │
│  4. git commit -m "Mejorar DAG de ingesta"                       │
│  5. git push origin main                                         │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              FASE 2: INTEGRACIÓN CONTINUA (CI)                   │
├──────────────────────────────────────────────────────────────────┤
│  GitHub Actions se activa automáticamente:                       │
│                                                                   │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Workflow: ci.yml                                  │         │
│  │  - Checkout código                                 │         │
│  │  - Instalar dependencias                           │         │
│  │  - Ejecutar pytest (tests unitarios)               │         │
│  │  - Ejecutar flake8 (linting)                       │         │
│  │  - Ejecutar bandit (security scan)                 │         │
│  │  ✓ PASS: Continuar a build                         │         │
│  │  ✗ FAIL: Detener pipeline, notificar               │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                   │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Workflow: build-airflow.yml                       │         │
│  │  - Construir imagen desde dags/Dockerfile.airflow  │         │
│  │  - Etiquetar: usuario/airflow:latest               │         │
│  │  - Etiquetar: usuario/airflow:sha-abc123           │         │
│  │  - Push a DockerHub                                │         │
│  │  ✓ Imagen disponible en DockerHub                  │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                   │
│  (Se repite para api, frontend, mlflow)                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                       DockerHub Registry
                  (Imágenes publicadas y versionadas)
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│         FASE 3: DESPLIEGUE CONTINUO (CD) - Opción A              │
│                    Argo CD + Kubernetes                          │
├──────────────────────────────────────────────────────────────────┤
│  1. Argo CD monitorea el repositorio Git cada 3 minutos         │
│  2. Detecta cambio en argocd/applications.yaml                  │
│  3. Detecta nueva imagen en DockerHub (usuario/airflow:latest)  │
│  4. Ejecuta: kubectl apply -f kubernetes/airflow.yaml           │
│  5. Kubernetes pull la nueva imagen y actualiza pods            │
│  6. Rollout automático sin downtime                             │
│  ✓ Airflow actualizado en cluster Kubernetes                    │
└──────────────────────────────────────────────────────────────────┘

                              O

┌──────────────────────────────────────────────────────────────────┐
│         FASE 3: DESPLIEGUE CONTINUO (CD) - Opción B              │
│                  Docker Compose Manual/Scripted                  │
├──────────────────────────────────────────────────────────────────┤
│  En tu máquina local o servidor:                                 │
│                                                                   │
│  1. docker-compose pull airflow-webserver                        │
│     (Descarga última imagen desde DockerHub)                     │
│  2. docker-compose up -d airflow-webserver                       │
│     (Reinicia servicio con nueva imagen)                         │
│  ✓ Airflow actualizado localmente                                │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              FASE 4: EJECUCIÓN Y OPERACIÓN                       │
├──────────────────────────────────────────────────────────────────┤
│  Docker Compose mantiene servicios corriendo:                    │
│                                                                   │
│  - Airflow UI accesible en http://localhost:8080                │
│  - MLflow UI accesible en http://localhost:5000                 │
│  - API REST accesible en http://localhost:8000                  │
│  - Frontend Streamlit en http://localhost:8501                  │
│  - Bases de datos PostgreSQL activas                            │
│  - Prometheus/Grafana monitoreando                              │
│                                                                   │
│  El equipo puede:                                                │
│  - Ejecutar DAGs manualmente desde Airflow UI                   │
│  - Consultar métricas en MLflow                                 │
│  - Hacer predicciones desde API o Frontend                      │
│  - Monitorear performance en Grafana                            │
└──────────────────────────────────────────────────────────────────┘
```

### Casos de Uso Específicos

#### Desarrollo Local
**Herramienta**: Docker Compose únicamente
- Se levantan todos los servicios con `docker-compose up -d`
- Se desarrollan y prueban cambios localmente
- No se necesita GitHub Actions aún
- Los builds de imágenes son locales y rápidos

#### Trabajo en Equipo
**Herramientas**: GitHub Actions + Docker Compose
- Cada desarrollador usa Docker Compose localmente
- Al hacer push, GitHub Actions valida el código automáticamente
- Construye imágenes centralizadas en DockerHub
- Todo el equipo puede ejecutar `docker-compose pull` para obtener la última versión
- Se garantiza que todos usan imágenes consistentes

#### Producción con Kubernetes
**Herramientas**: GitHub Actions + Argo CD + Kubernetes
- GitHub Actions construye y publica imágenes
- Argo CD detecta cambios automáticamente
- Kubernetes ejecuta los pods con las nuevas imágenes
- Docker Compose solo se usa para desarrollo local
- Escalado automático y alta disponibilidad

### Cuándo Usar Cada Herramienta

| Escenario | GitHub Actions | Docker Compose | Argo CD |
|-----------|----------------|----------------|---------|
| Desarrollo individual local | No | **Sí** | No |
| Pruebas antes de commit | No | **Sí** | No |
| Validar código en PR | **Sí** | No | No |
| Construir imágenes para equipo | **Sí** | No | No |
| Desplegar en servidor de desarrollo | No | **Sí** | Opcional |
| Desplegar en staging/producción | **Sí** | No | **Sí** |
| Rollback a versión anterior | No | Manual | **Sí** |
| Escalado horizontal | No | No | **Sí** |

### Resumen

**GitHub Actions** es la **fábrica automatizada**: construye, prueba y empaqueta el software, pero no lo ejecuta para uso final.

**Docker Compose** es el **entorno de ejecución**: toma las imágenes (de DockerHub o locales) y las pone a correr para que puedan ser utilizadas.

**Argo CD** es el **operador de despliegue**: toma las imágenes de DockerHub y las despliega automáticamente en Kubernetes siguiendo las definiciones en Git.

Todos son necesarios para un pipeline MLOps completo, pero cada uno tiene su rol específico en diferentes etapas del ciclo de vida del software.

## Decisiones de Diseño

### Arquitectura de Microservicios
Se optó por separar cada componente en su propio servicio para:
- Escalado independiente por demanda
- Despliegue sin downtime de componentes no afectados
- Facilidad de reemplazo o actualización de servicios individuales

### Separación de Bases de Datos
Cuatro bases de datos PostgreSQL separadas por:
- Aislamiento de concerns (RAW, CLEAN, Airflow, MLflow)
- Prevención de conflictos de esquema
- Backup y restore granular
- Seguridad: permisos específicos por base

### LocalExecutor en Airflow
Se utiliza LocalExecutor en lugar de CeleryExecutor por:
- Simplicidad de configuración
- Suficiente para volúmenes moderados de datos
- Menor overhead de infraestructura
- Nota: En producción de alta escala se recomendaría CeleryExecutor o KubernetesExecutor

### Dynamic Model Loading en API
La API carga dinámicamente el modelo en Production sin código hardcodeado:
- Permite actualización de modelos sin redeploy de código
- Facilita A/B testing cambiando stage en MLflow
- Reduce tiempo de deployment (no rebuild de imagen)

### Feature Engineering en DAG
El feature engineering se ejecuta en Airflow y no en API porque:
- Las transformaciones son costosas computacionalmente
- Se garantiza consistencia entre training e inference
- Los encodings y estadísticas se almacenan para reutilización
- La API se mantiene liviana y rápida

### SHAP para Explicabilidad
SHAP (SHapley Additive exPlanations) se utiliza para:
- Interpretabilidad a nivel de instancia
- Explicar por qué el modelo predijo cierto precio
- Confianza del usuario en predicciones
- Cumplimiento de regulaciones de transparencia

## Dataset: Realtor (Bienes Raíces)

**Fuente**: API del profesor en `http://10.43.100.103:8000`

**Características del dataset**:
- Variables: 12 columnas (brokered_by, status, price, bed, bath, acre_lot, street, city, state, zip_code, house_size, prev_sold_date)
- Target: price (regresión)
- Tipo de datos: numéricos, categóricos, fechas
- Distribución: proporcionada en batches incrementales por la API

**Preprocesamiento aplicado**:
- Encoding de categóricas (Label Encoding con persistencia)
- Imputación de valores faltantes (mediana para numéricos, moda para categóricos)
- Normalización Z-score para features numéricos
- Feature engineering: ratios, agregaciones, features temporales

## Requisitos

### Hardware Mínimo
- CPU: 4 cores
- RAM: 8 GB
- Disco: 20 GB libres

### Software
- Docker 20.10+
- Docker Compose 2.0+
- (Opcional) Kubernetes 1.24+
- (Opcional) kubectl configurado

## Estructura de Directorios

```
proyecto_final/
├── .github/
│   └── workflows/              # GitHub Actions CI/CD
│       ├── build-airflow.yml
│       ├── build-api.yml
│       ├── build-frontend.yml
│       ├── build-mlflow.yml
│       └── ci.yml
├── argocd/                     # Argo CD manifiestos
│   ├── application.yaml
│   ├── project.yaml
│   ├── applications.yaml
│   └── README.md
├── config/                     # Configuraciones
│   ├── grafana/
│   │   └── dashboard.json
│   └── prometheus/
│       └── prometheus.yml
├── dags/                       # Airflow DAGs
│   ├── 1_ingest_from_external_api.py
│   ├── 2_clean_build.py
│   ├── 3_train_and_register.py
│   ├── Dockerfile.airflow
│   ├── requirements.txt
│   └── utils/
│       ├── data_loader.py
│       ├── preprocessing.py
│       └── mlflow_utils.py
├── docs/                       # Documentación
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── TESTING.md
├── initdb/                     # Scripts SQL iniciales
│   ├── 01_create_raw_db_realtor.sql
│   ├── 02_create_clean_db_realtor.sql
│   └── 03_create_mlflow_db.sql
├── kubernetes/                 # Manifiestos Kubernetes
│   ├── namespace.yaml
│   ├── pvc.yaml
│   ├── databases.yaml
│   ├── mlflow.yaml
│   ├── api.yaml
│   ├── frontend.yaml
│   └── observability.yaml
├── scripts/                    # Scripts de utilidad
│   ├── deploy.sh
│   ├── test_services.sh
│   └── cleanup.sh
├── services/                   # Microservicios
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── requirements.txt
│   ├── locust/
│   │   ├── Dockerfile
│   │   ├── locustfile.py
│   │   └── requirements.txt
│   └── mlflow/
│       ├── Dockerfile
│       └── requirements.txt
├── tests/                      # Tests automatizados
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_pipeline.py
│   └── requirements.txt
├── .env.example                # Variables de entorno template
├── .gitignore                  # Git ignore
├── docker-compose.yml          # Orquestación Docker
├── README.md                   # Este archivo
├── QUICKSTART.md               # Guía de inicio rápido
└── COMPONENTES_IMPLEMENTADOS.md # Documentación de componentes
```

## Documentación Adicional

- `QUICKSTART.md`: Guía de inicio rápido para despliegue
- `COMPONENTES_IMPLEMENTADOS.md`: Detalles de implementación de los 5 componentes nuevos
- `.github/workflows/README.md`: Documentación de CI/CD con GitHub Actions
- `argocd/README.md`: Documentación de despliegue continuo con Argo CD
- `docs/ARCHITECTURE.md`: Arquitectura detallada del sistema
- `docs/DEPLOYMENT.md`: Guía de despliegue en diferentes entornos
- `docs/TESTING.md`: Estrategia de testing y pruebas

## Autores

Proyecto Final - Curso de Operaciones de Machine Learning  
Pontificia Universidad Javeriana  
Cristian Javier Diaz Alvarez

Daniel Rios  
Miguel Granados  
Sebastian Fanchi

Noviembre 2025
