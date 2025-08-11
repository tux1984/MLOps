# Clasificación de pingüinos con palmerpenguins (Entrenamiento + API)

Proyecto end-to-end: **descarga de datos**, **procesamiento**, **entrenamiento con validación** y **serving** mediante **FastAPI**. Ahora con **modo multi‑modelo** para cargar varios clasificadores (p.ej., Random Forest y Regresión Logística) y elegir/compare en tiempo de ejecución.

---

## Índice
1. [Arquitectura y flujo](#arquitectura-y-flujo)
2. [Dataset](#dataset)
3. [Requisitos e instalación](#requisitos-e-instalación)
4. [Entrenamiento (`train_penguins.py`)](#entrenamiento-train_penguinspy)
5. [Preprocesamiento](#preprocesamiento)
6. [Modelos y búsqueda de hiperparámetros](#modelos-y-búsqueda-de-hiperparámetros)
7. [Métricas y evaluación](#métricas-y-evaluación)
8. [Artefactos generados](#artefactos-generados)
9. [API (FastAPI) — Modo multi‑modelo](#api-fastapi--modo-multi-modelo)
10. [Ejemplos de uso](#ejemplos-de-uso)
11. [Variables de entorno](#variables-de-entorno)
12. [Estructura sugerida del repositorio](#estructura-sugerida-del-repositorio)
13. [Solución de problemas](#solución-de-problemas)

---

## Arquitectura y flujo

1) **Ingesta de datos** → `palmerpenguins.load_penguins()` devuelve un DataFrame listo.  
2) **Procesamiento** → imputación de nulos, escalado de numéricas y one‑hot en categóricas con `ColumnTransformer` dentro de un `Pipeline`.  
3) **Split estratificado** → separa Train/Test manteniendo proporción de clases.  
4) **Entrenamiento** → `GridSearchCV` selecciona la mejor configuración (CV estratificada).  
5) **Evaluación** → accuracy, reporte por clase y matriz de confusión en **Test**.  
6) **Artefactos** → `penguins_model.joblib`, `metrics.json`, `schema.json`.  
7) **Serving** → **FastAPI** carga uno o **varios** modelos y expone `/predict` (y `/predict/compare`).

> Decisión clave: el **Pipeline** guarda *preprocesamiento + modelo* juntos.

---

## Dataset

- **palmerpenguins**: medidas anatómicas de pingüinos de Palmer Station (Antártida).  
- Columnas relevantes:
  - Target: `species` (Adelie, Chinstrap, Gentoo)
  - Numéricas: `bill_length_mm`, `bill_depth_mm`, `flipper_length_mm`, `body_mass_g`
  - Categóricas: `island`, `sex`

---

## Entrenamiento (`train_penguins.py`)

### Entrenar un Random Forest
```bash
python train_penguins.py --model rf --cv 5 --test-size 0.2 --outdir artifacts_rf
```

### Entrenar una Regresión Logística
```bash
python train_penguins.py --model logreg --cv 5 --test-size 0.2 --outdir artifacts_logreg
```

> Puedes entrenar tantos modelos como quieras, usando `--outdir` distintos (p. ej., `artifacts_svc`, `artifacts_xgb`, etc.).

### Qué sucede internamente
1. Carga datos y elimina filas con `species` nulo.  
2. Separa **X** (features) e **y** (target), distinguiendo numéricas y categóricas.  
3. Construye un **ColumnTransformer**:
   - Numéricas → `SimpleImputer(median)` + `StandardScaler()`
   - Categóricas → `SimpleImputer(most_frequent)` + `OneHotEncoder(handle_unknown="ignore")`
4. Une **preprocesamiento + modelo** en un **Pipeline**.  
5. Ejecuta **GridSearchCV** con `cv` folds para elegir hiperparámetros.  
6. Evalúa en **Test** y guarda artefactos.

---

## Preprocesamiento

- **Imputación de nulos**: numéricas con **mediana**, categóricas con **moda**.  
- **Escalado**: estandariza numéricas para estabilizar modelos lineales.  
- **One‑Hot**: transforma categóricas a indicadores binarios (`handle_unknown="ignore"`).  
- **Pipeline**: asegura idénticas transformaciones en entrenamiento e inferencia.

---

## Modelos y búsqueda de hiperparámetros

- **RandomForestClassifier (`rf`)**:  
  `n_estimators` ∈ {200, 400, 800}, `max_depth` ∈ {None, 6, 10, 14}, `min_samples_split` ∈ {2, 4, 8}.

- **LogisticRegression (`logreg`)**:  
  `C` ∈ {0.1, 1, 3, 10}, `solver` ∈ {lbfgs, saga}, `penalty` = L2.

**Por qué GridSearchCV:** selecciona la mejor combinación con CV, reduciendo el sesgo a un único split.

---

## Métricas y evaluación

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

## Artefactos generados

Cada carpeta `outdir` (p. ej., `artifacts_rf/`, `artifacts_logreg/`) contiene:
- `penguins_model.joblib` → **Pipeline completo** (preprocesamiento + mejor modelo).
- `metrics.json` → métricas de CV/Test y mejores hiperparámetros.
- `schema.json` → columnas esperadas (`numeric`/`categorical`), target y un ejemplo.

---

## API (FastAPI) — Modo multi‑modelo

La API puede cargar **varios modelos** a la vez y te deja **elegir** cuál usar por request, o **compararlos** lado a lado.

### Ejecutar
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Endpoints

- `GET /healthz`  
  *Health check.* Indica modelos cargados y modelo por defecto.

- `GET /models`  
  Lista los modelos cargados, clases y (si están) métricas clave (`test_accuracy`, `cv_best_score`, `cv_best_params`).

- `GET /model/schema?model=rf|logreg`  
  Devuelve el `schema.json` del modelo indicado (útil para formularios y validación del cliente).  
  Si omites `model`, usa el **default**.

- `POST /predict?model=rf|logreg`  
  Predice con el modelo elegido. El `model` también puede ir en el body.  
  **Entrada (JSON):**
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
  **Salida (JSON):**
  ```json
  {
    "model": "logreg",
    "predictions": ["Gentoo"],
    "probabilities": [{"Adelie": 0.01, "Chinstrap": 0.02, "Gentoo": 0.97}],
    "classes": ["Adelie","Chinstrap","Gentoo"]
  }
  ```

- `POST /predict/compare`  
  Ejecuta **todos los modelos cargados** con los mismos registros y devuelve resultados por modelo.
  **Salida (resumen):**
  ```json
  {
    "results": {
      "rf": { "model": "rf", "predictions": ["Gentoo"], "probabilities": [...], "classes": [...] },
      "logreg": { "model": "logreg", "predictions": ["Gentoo"], "probabilities": [...], "classes": [...] }
    }
  }
  ```

> **Formato de entrada:** actualmente `/predict` y `/predict/compare` reciben **JSON** (no Excel/CSV). Si necesitas subir archivos, añade un endpoint específico para `UploadFile` y usa `pandas.read_csv`/`read_excel`.

---

## Ejemplos de uso

**Elegir modelo por query param**
```bash
curl -X POST "http://localhost:8000/predict?model=rf" \
  -H "Content-Type: application/json" \
  -d '{"records":[{"bill_length_mm":45.1,"bill_depth_mm":17.0,"flipper_length_mm":200,"body_mass_g":4200,"island":"Biscoe","sex":"male"}]}'
```

**Elegir modelo en el body**
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"model":"logreg","records":[{"bill_length_mm":45.1,"bill_depth_mm":17.0,"flipper_length_mm":200,"body_mass_g":4200,"island":"Biscoe","sex":"male"}]}'
```

**Comparar todos los modelos cargados**
```bash
curl -X POST "http://localhost:8000/predict/compare" \
  -H "Content-Type: application/json" \
  -d '{"records":[{"bill_length_mm":45.1,"bill_depth_mm":17.0,"flipper_length_mm":200,"body_mass_g":4200,"island":"Biscoe","sex":"male"}]}'
```

---

## Variables de entorno

Puedes configurar carpetas y modelo por defecto sin tocar el código:

```bash
# Directorios de artefactos
export RF_DIR="artifacts_rf"
export LOGREG_DIR="artifacts_logreg"

# Modelo por defecto si no se indica en la request
export DEFAULT_MODEL="rf"   # o "logreg"
```

> Si agregas más modelos, expón otra variable y añádela al diccionario de configuración en el código (`MODELS_CONFIG`).

---

## Estructura sugerida del repositorio

```
.
├─ README.md
├─ train_penguins.py
├─ api.py                         # API multi‑modelo
├─ artifacts_rf/
│  ├─ penguins_model.joblib
│  ├─ metrics.json
│  └─ schema.json
├─ artifacts_logreg/
│  ├─ penguins_model.joblib
│  ├─ metrics.json
│  └─ schema.json
├─ .venv/                         # (opcional)
└─ requirements.txt               # (opcional)
```

---

## Solución de problemas

- **“No se cargó ningún modelo” al iniciar la API**  
  → Verifica que existan `penguins_model.joblib` en las carpetas configuradas y que las rutas sean correctas.

- **Error de validación en `/predict`**  
  → Revisa tipos y nombres en `/model/schema?model=...`. Envía números como `number`, no strings.

- **Categoría desconocida en `island`/`sex`**  
  → No falla: `OneHotEncoder(handle_unknown="ignore")` convierte a ceros para esa categoría.

- **Resultados distintos a los del README**  
  → La aleatoriedad del split/semillas y la versión de librerías pueden cambiar levemente las métricas. Usa `random_state=42` para reproducibilidad.
