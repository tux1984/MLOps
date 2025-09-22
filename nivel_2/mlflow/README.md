
# 🚀 MLflow Full Lifecycle Project

Este proyecto implementa un entorno completo y profesional de Machine Learning utilizando [MLflow](https://mlflow.org/) para rastrear experimentos, registrar modelos y exponer inferencias vía API. El sistema simula un entorno de producción en contenedores Docker, conectando:

- 🔗 **MLflow Tracking y Model Registry**
- 🗃️ **PostgreSQL** como backend de metadatos y dataset
- ☁️ **MinIO (S3)** como backend de artefactos
- 🧪 **JupyterLab** para entrenamiento y experimentación
- 🔮 **FastAPI** como servidor de inferencias

## 🧱 Arquitectura del sistema

```
+-------------+       +-------------+       +---------------+
|  JupyterLab | <---> | PostgreSQL  | <---> |   MLflow DB   |
|  Experiments|       | (Dataset +  |       | (params, runs)|
+-------------+       |  metadata)  |       +---------------+
       |                      ↑
       ↓                      |
+-------------+         +-----------+        +---------------+
|   MLflow    | <-----> |   MinIO   | <----> |  Model Artifacts
| Tracking UI |         |  (S3 API) |        +---------------+
+-------------+

           |
           ↓
+------------------+
|   FastAPI        |
|  /predict (REST) |
+------------------+
```

## 📦 Requisitos

- Docker & Docker Compose
- Make (opcional, para automatizar)
- Navegador (para acceder a UIs)
- Python ≥ 3.10 (para desarrollo local)

## 🚀 Instalación y uso rápido

```bash
# Clona el repositorio
git clone https://github.com/tu_usuario/mlflow_project.git
cd mlflow_project

# Construye contenedores
make build

# Inicia todos los servicios
make up

# Carga el dataset inicial a PostgreSQL
make load-data

# Abre JupyterLab para entrenar modelos
make notebook

# Abre documentación interactiva de la API
make api
```

## 📁 Estructura de carpetas

```bash
mlflow_project/
├── .env                      # Variables para MinIO, PostgreSQL, MLflow
├── Makefile                  # Comandos automáticos
├── docker-compose.yml        # Orquestación de todos los servicios
├── init.sql                  # Crea tabla inicial en PostgreSQL
├── data/
│   └── sample_data.csv       # Dataset inicial para entrenamiento
├── scripts/
│   └── load_data.py          # Carga CSV a PostgreSQL
├── jupyterlab/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── notebook.ipynb        # Entrenamiento con MLflow
├── api/
│   ├── Dockerfile
│   ├── main.py               # API de inferencia con FastAPI
│   └── requirements.txt
└── README.md
```

## 🧪 Entrenamiento en JupyterLab

Accede a [http://localhost:8888](http://localhost:8888) y abre el notebook `notebook.ipynb`.  
El notebook realiza:

- Preprocesamiento de datos
- División `train/val/test`
- Entrenamiento de 20 modelos Random Forest con distintos hiperparámetros
- Registro automático en MLflow Tracking
- Comparación de resultados
- Registro del mejor modelo en `Model Registry`

## 🧠 Seguimiento de Experimentos con MLflow

Accede a MLflow UI en: [http://localhost:5000](http://localhost:5000)

Allí podrás ver:
- Todos los experimentos, runs, métricas y parámetros
- Artefactos de los modelos
- Model Registry con historial de versiones

## ☁️ MinIO – Almacenamiento de artefactos (S3 compatible)

Accede a la consola MinIO en: [http://localhost:9001](http://localhost:9001)

Credenciales por defecto:

- Usuario: `admin`
- Contraseña: `supersecret`

Debes crear el bucket `mlflow-artifacts` (una sola vez) antes de entrenar.

## 🔮 API de Inferencia

La API de FastAPI permite consultar predicciones del modelo registrado en MLflow.

### Documentación Swagger:

📎 [http://localhost:8000/docs](http://localhost:8000/docs)

### Endpoint:

```http
POST /predict
```

### Body de ejemplo:

```json
{
  "age": 34,
  "income": 48000,
  "education_level": "Master"
}
```

### Respuesta:

```json
{
  "credit_score": 712.45
}
```

## 🔄 Comandos útiles (`Makefile`)

```bash
make up             # Levanta todos los servicios
make build          # Construye los contenedores
make load-data      # Carga el CSV a PostgreSQL
make notebook       # Abre JupyterLab en navegador
make api            # Abre Swagger UI
make logs           # Muestra logs
make down           # Detiene todos los servicios
make reset-db       # Elimina volumen de PostgreSQL
make reset-minio    # Elimina volumen de MinIO
```

## 🧼 Buenas prácticas aplicadas

- ✔️ Estructura modular y reproducible
- ✔️ Model Registry gestionado desde código
- ✔️ Entrenamiento reproducible y trazable
- ✔️ API desacoplada del entrenamiento
- ✔️ Contenedores independientes y escalables
- ✔️ Logging y versionado automático
- ✔️ Dataset realista y conexión a base de datos

## ✅ Estado del proyecto

| Módulo       | Estado    |
|--------------|-----------|
| PostgreSQL   | ✅ OK     |
| MinIO        | ✅ OK     |
| MLflow       | ✅ OK     |
| JupyterLab   | ✅ OK     |
| Experimentos | ✅ OK     |
| API FastAPI  | ✅ OK     |

## 📬 Contacto

Desarrollado por [Tu Nombre]  
✉️ contacto@correo.com  
🔗 [LinkedIn](https://www.linkedin.com/in/...)
