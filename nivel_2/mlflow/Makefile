# ---------------------------
# CONFIG
# ---------------------------
PROJECT_NAME = mlflow_project
CSV_PATH = data/sample_data.csv
PYTHON_LOAD_SCRIPT = scripts/load_data.py
JUPYTER_URL = http://localhost:8888
API_DOCS = http://localhost:8000/docs

# ---------------------------
# DOCKER COMMANDS
# ---------------------------
up:
	docker compose up -d

build:
	docker compose build

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	$(DOCKER_COMPOSE) down && $(DOCKER_COMPOSE) up -d --build

reset-db:
	docker compose down -v --remove-orphans
	docker volume rm mlflow_project_pgdata || true

reset-minio:
	docker volume rm mlflow_project_minio_data || true

# ---------------------------
# DATA LOAD
# ---------------------------
load-data:
	@echo "Loading CSV into PostgreSQL..."
	docker compose exec jupyterlab python $(PYTHON_LOAD_SCRIPT)

# ---------------------------
# DEV SHORTCUTS
# ---------------------------
notebook:
	@echo "Open: $(JUPYTER_URL)"
	open $(JUPYTER_URL)

notebook-list:
	$(DOCKER_COMPOSE) exec $(JUPYTERLAB_SERVICE) jupyter notebook list

api:
	@echo "Open: $(API_DOCS)"
	open $(API_DOCS)

test-api:
	curl -X POST http://localhost:8000/predict \
		-H "Content-Type: application/json" \
		-d '{"age": 35, "income": 80000, "education_level": "Master"}'

# --------------------------------------------------
# Limpieza
# --------------------------------------------------
clean:
	$(DOCKER_COMPOSE) down -v
	docker system prune -f