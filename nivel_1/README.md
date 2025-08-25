
# Taller MLOps Nivel 1 - Comparticion de volumenes

## Tabla de Contenidos

- [Introducción](#introducción)
- [Quickstart](#quickstart)
- [Definición y levantamiento de servicios](#definición-y-levantamiento-de-servicios)
	- [docker-compose](#1-docker-compose)
	- [Dockerfiles](#2-dockerfiles)
	- [Manejo de paquetes con uv](#3-manejo-de-paquetes-con-uv)
- [Entrenamiento de Modelos](#entrenamiento-de-modelos)
- [Definición de API](#definición-de-api)
	- [Endpoints disponibles](#endpoints-disponibles)
	- [Notas adicionales](#notas-adicionales)

## Introducción

Este proyecto levanta dos servicios principales usando Docker Compose:
- **JupyterLab**: entorno interactivo para desarrollo, experimentación y entrenamiento de modelos de clasificación (regresión logística, random forest y SVC) sobre el dataset de pingüinos.
- **API (FastAPI)**: expone los modelos entrenados para inferencia.

Ambos servicios comparten volúmenes para acceder a los modelos y los datos, permitiendo que los modelos entrenados en JupyterLab estén disponibles para la API y que ambos servicios accedan a los mismos datos.

---

## Quickstart

Para iniciar ambos servicios, ejecute el siguiente comando en la carpeta `nivel_1` donde se encuentra el archivo `docker-compose.yml`:

```
docker compose up
```

Luego, acceda a los servicios desde su navegador web:
- **JupyterLab**: [http://localhost:8888](http://localhost:8888)
- **API (FastAPI)**: [http://localhost:8000/docs](http://localhost:8000/docs) (documentación interactiva)

---

## Definición y levantamiento de servicios

### 1. docker-compose
El archivo `docker-compose.yml` define dos servicios:
- **jupyterlab**: construye desde `docker/jupyter`, expone el puerto 8888 y comparte los volúmenes `notebooks`, `models` y `data`.
- **fastapi**: construye desde `api`, expone el puerto 8000 y comparte el volumen `models`.

**Compartición de volúmenes:**
- `./models:/shared/models`: ambos servicios acceden a los modelos entrenados.
- `./data:/data`: JupyterLab accede a los datos para entrenamiento.
- `./notebooks:/home/jovyan/work`: JupyterLab guarda los notebooks en la máquina local.

Esto permite que los modelos entrenados en JupyterLab estén disponibles para la API sin necesidad de copiar archivos manualmente.

### 2. Dockerfiles

- **JupyterLab:**
	- Basado en `python:3.11-slim`.
	- Instala dependencias del sistema y Python.
	- Instala `uv` y los paquetes listados en `requirements.uv.txt` usando `uv`.
	- Configura el usuario `jovyan` (no-root) y expone el puerto 8888.
	- Comando de arranque: JupyterLab.

- **API (FastAPI):**
	- Basado en `python:3.11-slim`.
	- Instala dependencias del sistema y Python.
	- Instala `uv` y los paquetes listados en `requirements.uv.txt` usando `uv`.
	- Copia el código fuente de la API y expone el puerto 8000.
	- Comando de arranque: Uvicorn para servir FastAPI.

### 3. Manejo de paquetes con uv

Cada servicio gestiona sus dependencias de Python utilizando **uv**, una herramienta moderna y rápida para instalar paquetes. Los paquetes requeridos se listan en `requirements.uv.txt` dentro de cada contexto de build, y se instalan con:
```
uv pip install --system -r requirements.uv.txt
```
Esto garantiza entornos reproducibles y eficientes para ambos servicios.

---

## Entrenamiento de Modelos

El entrenamiento de modelos se realiza en JupyterLab utilizando el dataset de pingüinos de seaborn. El flujo básico es:

1. **Carga y preprocesamiento:** Se carga el dataset, se eliminan valores nulos y se codifica la variable objetivo (`species`) con `LabelEncoder`. Las variables categóricas se convierten a variables dummy.
2. **División de datos:** Los datos se dividen en conjuntos de entrenamiento y prueba.
3. **Definición y entrenamiento de modelos:** Se definen tres modelos principales (regresión logística, random forest y SVC) y se realiza búsqueda de hiperparámetros con `GridSearchCV`.
4. **Evaluación:** Se imprime el reporte de clasificación para cada modelo.
5. **Guardado de modelos:** Cada modelo entrenado se guarda como un archivo `.pkl` en el directorio `/shared/models`, junto con el `LabelEncoder` utilizado. Esto permite que la API acceda directamente a los modelos entrenados para realizar inferencias.

---

## Definición de API

La API está implementada con FastAPI y expone los siguientes endpoints para interactuar con los modelos entrenados:

### Endpoints disponibles

- **GET /**
	- Descripción: Endpoint raíz. Devuelve un mensaje de bienvenida y la lista de endpoints principales.
	- Ejemplo de respuesta:
		```json
		{
			"message": "Bienvenido a la API de inferencia de modelos ML",
			"endpoints": ["/models", "/predict/{model_name}"]
		}
		```

- **GET /models**
	- Descripción: Devuelve la lista de modelos `.pkl` disponibles en el volumen compartido.
	- Ejemplo de respuesta:
		```json
		{
			"path": "/shared/models",
			"modelos_disponibles_total": 3,
			"modelos_disponibles": ["random_forest.pkl", "logistic_regression.pkl", "svc.pkl"]
		}
		```

- **POST /predict**
	- Descripción: Realiza una predicción usando el modelo especificado (por query param o en el body). Si no se indica, usa el modelo por defecto.
	- Parámetros:
		- `model` (opcional, query): nombre del modelo a usar (con o sin `.pkl`).
		- Body: JSON con los datos de entrada y, opcionalmente, el modelo.
	- Ejemplo de body:
		```json
		{
			"records": [
				{
					"island": "Biscoe",
					"bill_length_mm": 39.1,
					"bill_depth_mm": 18.7,
					"flipper_length_mm": 181,
					"body_mass_g": 3750,
					"sex": "Male"
				}
			]
		}
		```
	- Ejemplo de respuesta:
		```json
		{
			"model": "random_forest.pkl",
			"predictions": ["Adelie"],
			"probabilities": [
				{"Adelie": 0.95, "Chinstrap": 0.03, "Gentoo": 0.02}
			],
			"classes": ["Adelie", "Chinstrap", "Gentoo"]
		}
		```

- **POST /predict/compare**
	- Descripción: Realiza predicciones con varios modelos y compara los resultados.
	- Parámetros:
		- `models` (opcional, query): lista de modelos a comparar (con o sin `.pkl`).
		- Body: JSON con los datos de entrada.
	- Ejemplo de body:
		```json
		{
			"records": [
				{
					"island": "Biscoe",
					"bill_length_mm": 39.1,
					"bill_depth_mm": 18.7,
					"flipper_length_mm": 181,
					"body_mass_g": 3750,
					"sex": "Male"
				}
			]
		}
		```
	- Ejemplo de respuesta:
		```json
		{
			"results": {
				"random_forest.pkl": {
					"model": "random_forest.pkl",
					"predictions": ["Adelie"],
					"probabilities": [
						{"Adelie": 0.95, "Chinstrap": 0.03, "Gentoo": 0.02}
					],
					"classes": ["Adelie", "Chinstrap", "Gentoo"]
				},
				"logistic_regression.pkl": {
					"model": "logistic_regression.pkl",
					"predictions": ["Adelie"],
					"probabilities": [
						{"Adelie": 0.90, "Chinstrap": 0.05, "Gentoo": 0.05}
					],
					"classes": ["Adelie", "Chinstrap", "Gentoo"]
				},
				"svc.pkl": {
					"model": "svc.pkl",
					"predictions": ["Gentoo"],
					"probabilities": null,
					"classes": ["Adelie", "Chinstrap", "Gentoo"]
				}
			}
		}
		```

### Notas adicionales

- Todos los endpoints devuelven errores claros en caso de problemas con el modelo o los datos de entrada.
- El esquema exacto de los datos de entrada y salida puede consultarse en la documentación interactiva de FastAPI:
	- [http://localhost:8000/docs](http://localhost:8000/docs)


