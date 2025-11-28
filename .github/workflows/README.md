# GitHub Actions CI/CD Workflows

Este directorio contiene los workflows de GitHub Actions para implementar CI/CD completo en el proyecto MLOps.

## Estructura

```
.github/workflows/
├── build-airflow.yml    # Build y push de imagen Airflow
├── build-api.yml        # Build y push de imagen FastAPI
├── build-frontend.yml   # Build y push de imagen Streamlit
├── build-mlflow.yml     # Build y push de imagen MLflow
└── ci.yml               # Tests, linting y security scan
```

## Workflows Implementados

### 1. `build-airflow.yml`
**Construye y publica imagen Docker de Airflow**

- **Trigger**: Push a `main`/`master` en archivos `proyecto_final/dags/**`
- **Imagen**: `<DOCKERHUB_USERNAME>/mlops-airflow:latest`
- **Contexto**: `./proyecto_final/dags`
- **Dockerfile**: `proyecto_final/dags/Dockerfile.airflow`

### 2. `build-api.yml`
**Construye y publica imagen Docker de FastAPI**

- **Trigger**: Push a `main`/`master` en archivos `proyecto_final/services/api/**`
- **Imagen**: `<DOCKERHUB_USERNAME>/mlops-api:latest`
- **Contexto**: `./proyecto_final/services/api`
- **Dockerfile**: `proyecto_final/services/api/Dockerfile`

### 3. `build-frontend.yml`
**Construye y publica imagen Docker de Streamlit**

- **Trigger**: Push a `main`/`master` en archivos `proyecto_final/services/frontend/**`
- **Imagen**: `<DOCKERHUB_USERNAME>/mlops-frontend:latest`
- **Contexto**: `./proyecto_final/services/frontend`
- **Dockerfile**: `proyecto_final/services/frontend/Dockerfile`

### 4. `build-mlflow.yml`
**Construye y publica imagen Docker de MLflow**

- **Trigger**: Push a `main`/`master` en archivos `proyecto_final/services/mlflow/**`
- **Imagen**: `<DOCKERHUB_USERNAME>/mlops-mlflow:latest`
- **Contexto**: `./proyecto_final/services/mlflow`
- **Dockerfile**: `proyecto_final/services/mlflow/Dockerfile`

### 5. `ci.yml`
**Pipeline de Integración Continua**

- **Trigger**: Push/PR a `main`, `master`, `develop`
- **Jobs**:
  - `lint`: Flake8 + Black code formatting
  - `test-api`: Pytest para API tests
  - `test-pipeline`: Pytest para pipeline tests
  - `security-scan`: Trivy vulnerability scanner

## Configuración de Secrets

Antes de usar estos workflows, configure los siguientes secrets en GitHub:

### Paso 1: Crear Token de DockerHub

1. Acceder a https://hub.docker.com/settings/security
2. Hacer clic en "New Access Token"
3. Nombre: `GitHub Actions - MLOps Project`
4. Permisos: Read, Write, Delete
5. Copiar el token generado

### Paso 2: Configurar Secrets en GitHub

1. Ir al repositorio → **Settings** → **Secrets and variables** → **Actions**
2. Hacer clic en **New repository secret**
3. Agregar los siguientes secrets:

| Secret Name | Valor | Descripción |
|------------|-------|-------------|
| `DOCKERHUB_USERNAME` | usuario-dockerhub | Username de DockerHub |
| `DOCKERHUB_TOKEN` | token-generado | Token de acceso de DockerHub |

## Uso

### Disparar Workflows Automáticamente

Los workflows se ejecutan automáticamente cuando se realizan cambios:

```bash
# Modificar código de API
git add proyecto_final/services/api/main.py
git commit -m "feat: add new endpoint"
git push origin main
# → Dispara build-api.yml

# Modificar código de Frontend
git add proyecto_final/services/frontend/app.py
git commit -m "feat: add SHAP visualization"
git push origin main
# → Dispara build-frontend.yml

# Modificar DAGs
git add proyecto_final/dags/1_ingest_from_external_api.py
git commit -m "fix: batch processing logic"
git push origin main
# → Dispara build-airflow.yml
```

### Disparar Workflows Manualmente

Desde GitHub UI:
1. Ir a la pestaña **Actions**
2. Seleccionar el workflow
3. Hacer clic en **Run workflow**
4. Seleccionar branch y ejecutar

Desde CLI con GitHub CLI:

```bash
# Instalar gh CLI: https://cli.github.com/

# Disparar build de API
gh workflow run build-api.yml

# Disparar build de Frontend
gh workflow run build-frontend.yml

# Disparar todos los tests
gh workflow run ci.yml
```

## Monitoreo de Workflows

### Ver Estado de Workflows

```bash
# Listar workflows
gh workflow list

# Ver runs recientes
gh run list

# Ver detalles de un run
gh run view <run-id>

# Ver logs de un run
gh run view <run-id> --log
```

### Badges de Estado

Se pueden agregar badges al README.md:

```markdown
![Build Airflow](https://github.com/tux1984/MLOps/actions/workflows/build-airflow.yml/badge.svg)
![Build API](https://github.com/tux1984/MLOps/actions/workflows/build-api.yml/badge.svg)
![Build Frontend](https://github.com/tux1984/MLOps/actions/workflows/build-frontend.yml/badge.svg)
![CI Tests](https://github.com/tux1984/MLOps/actions/workflows/ci.yml/badge.svg)
```

## Flujo de CI/CD Completo

### Desarrollo → Producción

```
1. Desarrollador hace push a main
   ↓
2. GitHub Actions detecta cambios
   ↓
3. Ejecuta CI pipeline (tests, linting, security)
   ↓
4. Si CI pasa, construye imagen Docker
   ↓
5. Tagea imagen: latest, branch-sha
   ↓
6. Push imagen a DockerHub
   ↓
7. Argo CD detecta nueva imagen en DockerHub
   ↓
8. Argo CD sincroniza manifiestos de Kubernetes
   ↓
9. Kubernetes pull nueva imagen y actualiza pods
   ↓
10. Nuevo servicio desplegado en producción
```

## Estrategia de Tagging

Los workflows usan `docker/metadata-action` para generar tags automáticos:

| Evento | Tags Generados |
|--------|----------------|
| Push a `main` | `latest`, `main-<sha>` |
| Push a `develop` | `develop`, `develop-<sha>` |
| Push a branch | `<branch>`, `<branch>-<sha>` |

Ejemplo:
```
tux1984/mlops-api:latest
tux1984/mlops-api:main-a1b2c3d
```

## Nota Importante sobre la Estructura del Repositorio

Los workflows están configurados en la **raíz del repositorio** (`/.github/workflows/`) pero apuntan a los archivos dentro de `proyecto_final/`. Esto permite que GitHub Actions los detecte automáticamente mientras mantiene el código del proyecto organizado en su subdirectorio.

**Rutas clave**:
- Workflows: `/.github/workflows/`
- Código proyecto: `/proyecto_final/`
- DAGs: `/proyecto_final/dags/`
- Servicios: `/proyecto_final/services/`
- Tests: `/proyecto_final/tests/`

## Troubleshooting

### Error: "Cannot find Dockerfile"
- Verificar que las rutas en el workflow apunten a `proyecto_final/`
- Ejemplo: `context: ./proyecto_final/dags`

### Error: "Login to DockerHub failed"
- Verificar que los secrets `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` estén configurados
- Verificar que el token tenga permisos de Write

### Error: "Tests failed"
- Ejecutar tests localmente primero: `cd proyecto_final && pytest tests/`
- Verificar que todas las dependencias estén en `requirements.txt`
