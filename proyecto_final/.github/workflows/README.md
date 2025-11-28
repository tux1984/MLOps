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

- **Trigger**: Push a `main`/`master` en archivos `dags/**`
- **Imagen**: `<DOCKERHUB_USERNAME>/mlops-airflow:latest`
- **Contexto**: `./dags`
- **Dockerfile**: `dags/Dockerfile.airflow`

### 2. `build-api.yml`
**Construye y publica imagen Docker de FastAPI**

- **Trigger**: Push a `main`/`master` en archivos `services/api/**`
- **Imagen**: `<DOCKERHUB_USERNAME>/mlops-api:latest`
- **Contexto**: `./services/api`
- **Dockerfile**: `services/api/Dockerfile`

### 3. `build-frontend.yml`
**Construye y publica imagen Docker de Streamlit**

- **Trigger**: Push a `main`/`master` en archivos `services/frontend/**`
- **Imagen**: `<DOCKERHUB_USERNAME>/mlops-frontend:latest`
- **Contexto**: `./services/frontend`
- **Dockerfile**: `services/frontend/Dockerfile`

### 4. `build-mlflow.yml`
**Construye y publica imagen Docker de MLflow**

- **Trigger**: Push a `main`/`master` en archivos `services/mlflow/**`
- **Imagen**: `<DOCKERHUB_USERNAME>/mlops-mlflow:latest`
- **Contexto**: `./services/mlflow`
- **Dockerfile**: `services/mlflow/Dockerfile`

### 5. `ci.yml`
**Pipeline de Integración Continua**

- **Trigger**: Push/PR a `main`, `master`, `develop`
- **Jobs**:
  - `lint`: Flake8 + Black code formatting
  - `test-api`: Pytest para API tests
  - `test-pipeline`: Pytest para pipeline tests
  - `security-scan`: Trivy vulnerability scanner

## Configuración de Secrets

Antes de usar estos workflows, configura los siguientes secrets en GitHub:

### Paso 1: Crear Token de DockerHub

1. Ve a https://hub.docker.com/settings/security
2. Clic en "New Access Token"
3. Nombre: `GitHub Actions - MLOps Project`
4. Permisos: Read, Write, Delete
5. Copia el token generado

### Paso 2: Configurar Secrets en GitHub

1. Ve a tu repositorio → **Settings** → **Secrets and variables** → **Actions**
2. Clic en **New repository secret**
3. Agrega los siguientes secrets:

| Secret Name | Valor | Descripción |
|------------|-------|-------------|
| `DOCKERHUB_USERNAME` | tu-usuario-dockerhub | Tu username de DockerHub |
| `DOCKERHUB_TOKEN` | token-generado | Token de acceso de DockerHub |

## Uso

### Disparar Workflows Automáticamente

Los workflows se ejecutan automáticamente cuando:

```bash
# Modificar código de API
git add services/api/main.py
git commit -m "feat: add new endpoint"
git push origin main
# → Dispara build-api.yml

# Modificar código de Frontend
git add services/frontend/app.py
git commit -m "feat: add SHAP visualization"
git push origin main
# → Dispara build-frontend.yml

# Modificar DAGs
git add dags/1_raw_batch_ingest_15k.py
git commit -m "fix: batch processing logic"
git push origin main
# → Dispara build-airflow.yml
```

### Disparar Workflows Manualmente

Desde GitHub UI:
1. Ve a **Actions** tab
2. Selecciona el workflow
3. Clic en **Run workflow**
4. Selecciona branch y ejecuta

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

Agrega badges al README.md:

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

## Optimizaciones

### Build Cache

Los workflows usan **Docker layer caching** para acelerar builds:

```yaml
cache-from: type=registry,ref=${{ secrets.DOCKERHUB_USERNAME }}/${{ env.IMAGE_NAME }}:buildcache
cache-to: type=registry,ref=${{ secrets.DOCKERHUB_USERNAME }}/${{ env.IMAGE_NAME }}:buildcache,mode=max
```

**Beneficios**:
- ⚡ Builds ~3-5x más rápidos
- 💰 Reduce uso de runners
- ♻️ Reutiliza layers sin cambios

### Matrix Builds (Futuro)

Para builds multi-arquitectura:

```yaml
strategy:
  matrix:
    platform:
      - linux/amd64
      - linux/arm64
```

## Troubleshooting

### Error: Invalid Credentials

```
Error: Cannot perform an interactive login from a non TTY device
```

**Solución**: Verifica que `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` estén configurados correctamente en GitHub Secrets.

### Error: Context not found

```
Error: failed to solve: failed to read dockerfile
```

**Solución**: Verifica que el `context` y `file` en el workflow coincidan con la estructura del proyecto.

### Build Timeout

Si builds toman >60 min:

1. Revisa dependencias en `requirements.txt`
2. Usa imágenes base más ligeras (`python:3.11-slim`)
3. Multi-stage builds para reducir tamaño final

### Security Scan Failures

Trivy puede reportar vulnerabilidades en dependencias:

```bash
# Actualizar dependencias localmente
pip install --upgrade -r requirements.txt

# Verificar vulnerabilidades
pip-audit
```

## Testing Local de Workflows

Usa [act](https://github.com/nektos/act) para ejecutar workflows localmente:

```bash
# Instalar act
brew install act  # macOS
choco install act  # Windows

# Ejecutar workflow localmente
act push -s DOCKERHUB_USERNAME=your-username -s DOCKERHUB_TOKEN=your-token

# Ejecutar workflow específico
act -W .github/workflows/build-api.yml
```

## Best Practices

1. **Commits Atómicos**: Un commit = un cambio lógico
2. **Mensajes Descriptivos**: Usa conventional commits (`feat:`, `fix:`, `chore:`)
3. **Branch Protection**: Requiere CI pass antes de merge a `main`
4. **Code Review**: Require approvals en PRs
5. **Versionado Semántico**: Tagea releases con `v1.0.0`, `v1.1.0`, etc.

## Integración con Argo CD

Después del push a DockerHub, actualiza manifiestos de Kubernetes:

### Opción 1: Manual

```bash
# Actualizar imagen en kubernetes/api.yaml
kubectl set image deployment/api-deployment api=tux1984/mlops-api:main-a1b2c3d
```

### Opción 2: GitOps (Recomendado)

1. GitHub Actions push imagen → DockerHub
2. Workflow actualiza `kubernetes/api.yaml` con nuevo tag
3. Commit + push cambios
4. Argo CD detecta cambio en Git
5. Argo CD sincroniza automáticamente

## Referencias

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Trivy Security Scanner](https://github.com/aquasecurity/trivy)
- [DockerHub](https://hub.docker.com/)
