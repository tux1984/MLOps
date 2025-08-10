# Penguins ML API

## 🔍 Descripción general

**Penguins ML API** es una aplicación construida con **FastAPI** que entrena un modelo de Machine Learning para predecir la especie de un pingüino usando el dataset [Palmer Penguins](https://allisonhorst.github.io/palmerpenguins/).

El flujo de la app es:

1. **Entrenamiento** de un modelo de clasificación en `scripts/train.py`.
2. **Serialización** del modelo entrenado en `artifacts/model.joblib`.
3. **Exposición** del modelo vía API REST con **FastAPI** (`app/main.py`).
4. **Despliegue** en contenedor Docker.

---

## 🗂️ Estructura del proyecto

```
NIVEL_0/
├── app/
│   ├── core/
│   │   ├── config.py          # Configuraciones generales
│   │   └── utils.py           # Utilidades para cargar el modelo
│   ├── models/
│   │   └── schemas.py         # Modelos Pydantic para validación de datos
│   └── main.py                # Definición de la API FastAPI
├── artifacts/
│   └── model.joblib           # Modelo entrenado (se genera al entrenar)
├── scripts/
│   └── train.py               # Script de entrenamiento (Data Prep + Model Creation)
├── requirements.txt           # Dependencias de Python
├── Dockerfile                 # Definición de la imagen Docker
└── README.md                  # Este archivo
```

---

## 🎓 Flujo de entrenamiento (`scripts/train.py`)

### **1. Data preparation**

- **Carga**: se carga el dataset con `palmerpenguins.load_penguins()`.
- **Limpieza**: se eliminan columnas irrelevantes (como `year`) y nulos.
- **Transformación**: normaliza columnas categóricas (`sex`, `island`).
- **Validación**: checks de valores positivos y categorías válidas.
- **Ingeniería de Características**: agrega `bill_ratio` = bill\_length / bill\_depth.
- **División**: train/test estratificado.

### **2. Model creation**

- **Construcción**: `Pipeline` con `ColumnTransformer` para preprocessing.
- **Entrenamiento**: Logistic Regression multinomial.
- **Validación**: `accuracy_score` y `classification_report`.

### **3. Salida**

- Guarda `artifacts/model.joblib` con:
  - `pipeline`: el pipeline completo.
  - `target_names`: clases.
  - `metrics`: métricas de validación.

---

## 📊 API con FastAPI (`app/main.py`)

### Endpoints

#### **GET** `/health`

Verifica el estado de la API y la versión.

**Respuesta ejemplo:**

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

#### **POST** `/predict`

Predice la especie de uno o más pingüinos.

**Request Body:**

```json
{
  "items": [
    {
      "island": "Biscoe",
      "bill_length_mm": 39.1,
      "bill_depth_mm": 18.7,
      "flipper_length_mm": 181,
      "body_mass_g": 3750,
      "sex": "male",
      "bill_ratio": 2.1
    }
  ]
}
```

**Respuesta ejemplo:**

```json
{
  "predictions": [
    {
      "species": "Adelie",
      "probabilities": {
        "Adelie": 0.85,
        "Chinstrap": 0.10,
        "Gentoo": 0.05
      }
    }
  ]
}
```

---

## 🛠️ Ejecución local

### 1) Crear entorno y dependencias

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Entrenar el modelo

```bash
python scripts/train.py
```

### 3) Levantar la API

```bash
uvicorn app.main:app --reload --port 8989
```

Documentación interactiva en:

```
http://localhost:8989/docs
```

---

## 📦 Construir y correr con Docker

### 1) Entrenar localmente

```bash
python scripts/train.py
```

Esto genera `artifacts/model.joblib`.

### 2) Construir imagen

```bash
docker build -t penguins-api .
```

### 3) Ejecutar contenedor

```bash
docker run -p 8989:8989 penguins-api
```

La API estará disponible en:

```
http://localhost:8989/docs
```

---

## 🔗 Referencias

- Dataset: [palmerpenguins](https://allisonhorst.github.io/palmerpenguins/)
- Framework: [FastAPI](https://fastapi.tiangolo.com/)
- ML: [scikit-learn](https://scikit-learn.org/stable/)

---

## 💡 Notas finales

- La ingeniería de features (`bill_ratio`) se realiza dentro del pipeline para evitar **train/serve skew**.
- El pipeline está diseñado para recibir datos crudos y procesarlos de forma consistente tanto en entrenamiento como en inferencia.
- El contenedor usa un usuario no-root y una imagen `python:3.12-slim` para ser más seguro y liviano.

