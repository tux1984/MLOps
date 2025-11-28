# Argo CD Configuration for MLOps Project

Este directorio contiene la configuración de Argo CD para el despliegue continuo (CD) del proyecto MLOps.

## Estructura

```
argocd/
├── application.yaml      # Application principal que despliega todo el sistema
├── project.yaml          # AppProject con permisos y políticas
├── applications.yaml     # Applications individuales por componente
└── README.md            # Esta documentación
```

## Componentes

### 1. AppProject (`project.yaml`)
Define el proyecto MLOps con:
- Repositorios permitidos
- Namespaces de destino
- Roles (developer, admin)
- Políticas de acceso

### 2. Application Principal (`application.yaml`)
Despliega todo el sistema desde `kubernetes/`:
- **Sync Policy**: Automated (prune, selfHeal)
- **Namespace**: mlops-final
- **Source**: proyecto_final/kubernetes

### 3. Applications por Componente (`applications.yaml`)
Aplicaciones individuales para control granular:
- `mlops-api`: API de inferencia FastAPI
- `mlops-frontend`: UI Streamlit
- `mlops-mlflow`: MLflow Tracking Server
- `mlops-airflow`: Orquestador de DAGs
- `mlops-databases`: PostgreSQL (4 instancias)
- `mlops-observability`: Prometheus + Grafana

## Instalación

### Paso 1: Instalar Argo CD

```bash
# Crear namespace
kubectl create namespace argocd

# Instalar Argo CD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Esperar a que esté listo
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
```

### Paso 2: Acceder a Argo CD UI

```bash
# Port forward
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Obtener password inicial
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Acceder a: https://localhost:8080
# Usuario: admin
# Password: (del comando anterior)
```

### Paso 3: Desplegar el Proyecto

#### Opción A: Application Principal (Todo el Sistema)

```bash
# Crear AppProject
kubectl apply -f argocd/project.yaml

# Crear Application principal
kubectl apply -f argocd/application.yaml

# Verificar sync
kubectl get applications -n argocd
```

#### Opción B: Applications Individuales

```bash
# Crear AppProject
kubectl apply -f argocd/project.yaml

# Crear applications por componente
kubectl apply -f argocd/applications.yaml

# Verificar
kubectl get applications -n argocd
```

## Configuración de Repositorio

Si el repositorio es privado, configurar credenciales:

```bash
# Vía CLI
argocd repo add https://github.com/tux1984/MLOps.git \
  --username <tu-usuario> \
  --password <tu-token>

# O vía YAML
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: mlops-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  type: git
  url: https://github.com/tux1984/MLOps.git
  username: <tu-usuario>
  password: <tu-token>
EOF
```

## Sincronización Manual

```bash
# Sync completo
argocd app sync mlops-proyecto-final

# Sync de componente específico
argocd app sync mlops-api
argocd app sync mlops-frontend

# Ver estado
argocd app get mlops-proyecto-final
```

## Monitoreo

```bash
# Ver todas las applications
kubectl get applications -n argocd

# Ver detalles de una application
kubectl describe application mlops-proyecto-final -n argocd

# Ver logs de sync
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller

# Ver recursos desplegados
kubectl get all -n mlops-final
```

## Política de Sync

### Automated Sync
- **Prune**: Elimina recursos no definidos en Git
- **SelfHeal**: Auto-corrige desviaciones del estado deseado
- **AllowEmpty**: Permite apps sin recursos

### Excepciones
- **Airflow**: `prune: false` (sync manual para proteger DAGs)
- **Databases**: `prune: false` (proteger datos persistentes)

## Rollback

```bash
# Ver historial
argocd app history mlops-api

# Rollback a versión anterior
argocd app rollback mlops-api <revision-id>
```

## Health Checks

Argo CD verifica automáticamente:
- **Deployments**: replicas ready
- **StatefulSets**: replicas ready
- **Services**: endpoints disponibles
- **PVCs**: bound status

## Troubleshooting

### Application no sincroniza

```bash
# Forzar sync
argocd app sync mlops-proyecto-final --force

# Ver diferencias
argocd app diff mlops-proyecto-final

# Ver eventos
kubectl get events -n mlops-final --sort-by='.lastTimestamp'
```

### Recursos en estado Degraded

```bash
# Ver detalles del recurso
kubectl describe <resource-type> <resource-name> -n mlops-final

# Ver logs
kubectl logs <pod-name> -n mlops-final
```

### Sync Hook failures

```bash
# Ver logs de hooks
kubectl logs -n mlops-final -l argocd.argoproj.io/hook-name=<hook-name>
```

## Integración con GitHub Actions

El workflow de CI construye imágenes Docker → las sube a DockerHub → Argo CD detecta cambios en Git → sincroniza automáticamente.

**Flujo completo**:
1. Push a `main`/`master`
2. GitHub Actions construye imagen → DockerHub
3. Actualizar `kubernetes/*.yaml` con nuevo tag
4. Push cambios a Git
5. Argo CD detecta cambio → sync automático

## Acceso a Servicios Desplegados

Después del despliegue:

```bash
# API
kubectl port-forward -n mlops-final svc/api-service 8000:8000

# Frontend
kubectl port-forward -n mlops-final svc/frontend-service 8501:8501

# MLflow
kubectl port-forward -n mlops-final svc/mlflow-service 5000:5000

# Grafana
kubectl port-forward -n mlops-final svc/grafana 3000:3000
```

## Referencias

- [Argo CD Documentation](https://argo-cd.readthedocs.io/)
- [Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)
- [GitOps Principles](https://opengitops.dev/)
