
# Quick Start

## Índice
1. [Quick Start](#quick-start)
2. [Arquitectura y Flujo](#arquitectura-y-flujo)
3. [Modelos y Entrenamiento](#modelos-y-entrenamiento)
4. [Documentación de la API](#documentación-de-la-api)
5. [Solución de problemas](#solución-de-problemas)

Sigue estos pasos para desplegar y probar la API de clasificación de pingüinos localmente usando Docker:

1. **Clona el repositorio:**
   ```bash
   git clone <URL_DEL_REPO>
   cd MLOps/nivel_0
   ```

2. **(Opcional) Crea un ambiente virtual e instala dependencias:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # En Windows
   pip install -r requirements.txt
   ```

3. **Entrena los modelos:**
   
   - Random Forest:
     ```bash
     python train_penguins.py --model rf --cv 5 --test-size 0.2 --outdir artifacts_rf
     ```
   - Regresión Logística:
     ```bash
     python train_penguins.py --model logreg --cv 5 --test-size 0.2 --outdir artifacts_logreg
     ```

4. **Despliega la API con Docker Compose:**
   ```bash
   docker-compose up --build
   ```
   Esto levantará la API en http://localhost:8000

5. **Explora la documentación interactiva:**
   - Abre [http://localhost:8000/docs](http://localhost:8000/docs) para probar los endpoints y ver los modelos cargados.

---

# Arquitectura y Flujo

1. **Ingesta de datos** → `palmerpenguins.load_penguins()` devuelve un DataFrame listo.
2. **Procesamiento** → imputación de nulos, escalado de numéricas y one‑hot en categóricas con `ColumnTransformer` dentro de un `Pipeline`.
3. **Split estratificado** → separa Train/Test manteniendo proporción de clases.
4. **Entrenamiento** → `GridSearchCV` selecciona la mejor configuración (CV estratificada).
5. **Evaluación** → accuracy, reporte por clase y matriz de confusión en Test.
6. **Artefactos** → `penguins_model.joblib`, `metrics.json`, `schema.json`.
7. **Serving** → FastAPI carga uno o varios modelos y expone `/predict` y `/predict/compare`.

---


# Modelos y Entrenamiento

- **RandomForestClassifier (`rf`)**:  
  `n_estimators` ∈ {200, 400, 800}, `max_depth` ∈ {None, 6, 10, 14}, `min_samples_split` ∈ {2, 4, 8}.

- **LogisticRegression (`logreg`)**:  
  `C` ∈ {0.1, 1, 3, 10}, `solver` ∈ {lbfgs, saga}, `penalty` = L2.

**GridSearchCV** selecciona la mejor combinación de hiperparámetros usando validación cruzada.

Cada carpeta de artefactos (`artifacts_rf/`, `artifacts_logreg/`) contiene:
- `penguins_model.joblib` → Pipeline completo (preprocesamiento + mejor modelo).
- `metrics.json` → métricas de CV/Test y mejores hiperparámetros.
- `schema.json` → columnas esperadas, target y ejemplo.

---

# Métricas y Evaluación

- **Accuracy** global, **reporte de clasificación** (precision/recall/F1 por clase) y **matriz de confusión**.
- Ejemplo real (puede variar):
  - Mejor configuración RF: `{'clf__max_depth': None, 'clf__min_samples_split': 2, 'clf__n_estimators': 800}`
  - Mejor CV accuracy RF: `0.9855`
  - Test accuracy RF: `1.0000`

Matriz de confusión (Test):
```
[[30  0  0]
 [ 0 14  0]
 [ 0  0 25]]
```

---

# Documentación de la API

La API (FastAPI) permite cargar y comparar varios modelos. Accede a la documentación interactiva en `/docs`.

## Endpoints principales

- `GET /healthz`  
  Verifica el estado de la API y los modelos cargados.

- `GET /models`  
  Lista los modelos disponibles y sus métricas principales.

- `GET /model/schema?model=rf|logreg`  
  Devuelve el esquema de entrada esperado para el modelo indicado.

- `POST /predict?model=rf|logreg`  
  Realiza una predicción con el modelo seleccionado. Puedes elegir el modelo por query param o en el body.
  
  **Ejemplo de body:**
  ```json
  {
    "model": "logreg",
    "records": [
      {
        "bill_length_mm": 45.1,
        "bill_depth_mm": 17.0,
        "flipper_length_mm": 200,
        "body_mass_g": 4200,
        "island": "Biscoe",
        "sex": "male"
      }
    ]
  }
  ```

- `POST /predict/compare`  
  Ejecuta todos los modelos cargados con los mismos registros y devuelve los resultados por modelo.

## Cómo probar en `/docs`

1. Ve a [http://localhost:8000/docs](http://localhost:8000/docs).
2. Selecciona el endpoint que deseas probar.
3. Haz clic en "Try it out".
4. Completa el body de ejemplo (ver arriba) y ejecuta la petición.
5. Revisa la respuesta y las probabilidades por clase.

---

# Solución de problemas

- **“No se cargó ningún modelo” al iniciar la API**  
  Verifica que existan `penguins_model.joblib` en las carpetas configuradas y que las rutas sean correctas.

- **Error de validación en `/predict`**  
  Revisa tipos y nombres en `/model/schema?model=...`. Envía números como `number`, no strings.

- **Categoría desconocida en `island`/`sex`**  
  No falla: `OneHotEncoder(handle_unknown="ignore")` convierte a ceros para esa categoría.

- **Resultados distintos a los del README**  
  La aleatoriedad del split/semillas y la versión de librerías pueden cambiar levemente las métricas. Usa `random_state=42` para reproducibilidad.
