# Guía de Testing

## Tipos de Tests

### 1. Tests Unitarios
### 2. Tests de Integración
### 3. Tests End-to-End
### 4. Tests de Carga
### 5. Tests de Modelo

## Configuración de Entorno de Testing

```bash
# Instalar dependencias de testing
pip install -r tests/requirements.txt

# O con virtualenv
python -m venv venv-test
source venv-test/bin/activate  # En Windows: venv-test\Scripts\activate
pip install -r tests/requirements.txt
```

## Tests Unitarios

### Ejecutar Tests Unitarios

```bash
# Todos los tests
pytest tests/ -v

# Tests específicos
pytest tests/test_api.py -v
pytest tests/test_pipeline.py -v

# Con coverage
pytest tests/ --cov=. --cov-report=html

# Ver reporte de coverage
open htmlcov/index.html  # En Windows: start htmlcov/index.html
```

### Estructura de Tests

```
tests/
├── conftest.py              # Fixtures compartidos
├── test_api.py              # Tests de API
├── test_pipeline.py         # Tests de pipeline
└── test_model.py            # Tests de modelo
```

## Tests de API

### Tests Manuales con curl

```bash
# Health check
curl http://localhost:8000/health

# Model info
curl http://localhost:8000/model-info

# Predicción individual
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "patient": {
      "age": 65,
      "gender": "Male",
      "admission_type": "Emergency"
    }
  }'

# Batch prediction
curl -X POST http://localhost:8000/predict-batch \
  -H "Content-Type: application/json" \
  -d '{
    "patients": [
      {"age": 65, "gender": "Male"},
      {"age": 45, "gender": "Female"}
    ]
  }'

# SHAP explanation
curl -X POST http://localhost:8000/explain \
  -H "Content-Type: application/json" \
  -d '{
    "patient": {
      "age": 65,
      "gender": "Male"
    }
  }'
```

### Tests Automatizados de API

```bash
# Ejecutar tests de API
pytest tests/test_api.py -v

# Tests específicos
pytest tests/test_api.py::TestHealthEndpoints::test_health_check -v
pytest tests/test_api.py::TestPredictionEndpoints::test_single_prediction -v
```

## Tests de Pipeline

### Tests de DAGs de Airflow

```bash
# Ejecutar tests de pipeline
pytest tests/test_pipeline.py -v

# Test de ingesta
pytest tests/test_pipeline.py::TestDataIngestion -v

# Test de preprocesamiento
pytest tests/test_pipeline.py::TestDataPreprocessing -v

# Test de entrenamiento
pytest tests/test_pipeline.py::TestModelTraining -v
```

### Validación Manual de DAGs

```bash
# Listar DAGs
docker-compose exec airflow-scheduler airflow dags list

# Test de parsing de DAG
docker-compose exec airflow-scheduler airflow dags test 1_raw_batch_ingest_15k

# Ejecutar DAG manualmente
docker-compose exec airflow-scheduler airflow dags trigger 1_raw_batch_ingest_15k
```

## Tests de Carga (Locust)

### Configuración de Locust

```bash
# Iniciar Locust
docker-compose up -d locust

# O localmente
pip install locust
locust -f services/locust/locustfile.py --host=http://localhost:8000
```

### Ejecutar Tests de Carga

1. **Via Web UI**:
   - Abrir http://localhost:8089
   - Configurar:
     - Number of users: 100
     - Spawn rate: 10 users/second
     - Host: http://api:8000
   - Click "Start swarming"

2. **Via CLI**:
```bash
# Test rápido
locust -f services/locust/locustfile.py \
  --host=http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 2m \
  --headless

# Test de stress
locust -f services/locust/locustfile.py \
  --host=http://localhost:8000 \
  --users 500 \
  --spawn-rate 50 \
  --run-time 10m \
  --headless
```

### Métricas a Monitorear

- **Response Time**: p50, p95, p99
- **RPS (Requests per Second)**: Throughput del sistema
- **Failure Rate**: Porcentaje de errores
- **Concurrent Users**: Usuarios simultáneos soportados

### Objetivos de Performance

- p95 latency < 500ms para predicciones individuales
- p95 latency < 2s para predicciones batch (10 pacientes)
- Throughput > 100 RPS
- Error rate < 1%

## Tests de Modelo

### Validación de Modelo en MLflow

```python
# Script de validación
import mlflow

mlflow.set_tracking_uri("http://localhost:5001")

# Obtener modelo en Production
client = mlflow.tracking.MlflowClient()
model_name = "diabetic_risk_model"
production_versions = client.get_latest_versions(model_name, stages=["Production"])

# Verificar métricas
for version in production_versions:
    run = client.get_run(version.run_id)
    metrics = run.data.metrics
    print(f"Model version {version.version} metrics:")
    print(f"  Accuracy: {metrics.get('accuracy', 0):.4f}")
    print(f"  F1-Score: {metrics.get('f1_score', 0):.4f}")
    print(f"  ROC-AUC: {metrics.get('roc_auc', 0):.4f}")
```

### Tests de Calidad de Modelo

```bash
# Ejecutar tests de modelo
pytest tests/test_model.py -v

# Tests de métricas
pytest tests/test_model.py::TestModelMetrics -v

# Tests de predicciones
pytest tests/test_model.py::TestModelPredictions -v
```

## Tests End-to-End

### Flujo Completo

```bash
# 1. Ejecutar pipeline completo
# En Airflow UI: Trigger DAG 1 → DAG 2 → DAG 3

# 2. Verificar modelo en MLflow
# MLflow UI: Ver que modelo está en Production

# 3. Test de API con modelo nuevo
curl http://localhost:8000/model-info

# 4. Test de predicción
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"patient": {...}}'

# 5. Verificar métricas en Prometheus/Grafana
# Grafana UI: Ver dashboard de métricas
```

## Tests de Regresión

### Antes de Desplegar Cambios

```bash
# 1. Ejecutar suite completa de tests
pytest tests/ -v

# 2. Verificar coverage
pytest tests/ --cov=. --cov-report=term-missing

# 3. Tests de carga
locust -f services/locust/locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless

# 4. Verificar métricas no se degradan
# Comparar con baseline en Grafana
```

## Continuous Testing

### GitHub Actions (CI)

```yaml
# TODO: Implementar en .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r tests/requirements.txt
      - name: Run tests
        run: pytest tests/ -v --cov
```

## Debugging Tests

### Debugging con pytest

```bash
# Ejecutar con output verbose
pytest tests/test_api.py -v -s

# Ejecutar con debugger
pytest tests/test_api.py --pdb

# Ejecutar solo tests fallidos
pytest --lf

# Ejecutar con warnings
pytest -W all
```

### Debugging de API

```bash
# Ver logs de API
docker-compose logs -f api

# Modo debug de FastAPI
# Editar services/api/main.py:
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, log_level="debug")
```

## Checklist de Testing

Antes de considerar el sistema listo para producción:

- [ ] Todos los tests unitarios pasan
- [ ] Coverage > 80%
- [ ] Tests de integración pasan
- [ ] API responde a todos los endpoints
- [ ] Modelo carga correctamente
- [ ] Predicciones son coherentes
- [ ] Tests de carga cumplen SLOs
- [ ] Métricas se registran correctamente
- [ ] Logs se generan apropiadamente
- [ ] Sistema se recupera de fallos
- [ ] Documentación está actualizada

## Recursos Adicionales

- [Pytest Documentation](https://docs.pytest.org/)
- [Locust Documentation](https://docs.locust.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [MLflow Model Validation](https://mlflow.org/docs/latest/models.html#model-validation)
