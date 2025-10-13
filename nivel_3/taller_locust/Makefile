# Makefile para facilitar el uso del proyecto

.PHONY: help train build run test load clean scale venv

# Variables
DOCKER_USER ?= your-dockerhub-username
IMAGE_NAME = ml-inference-api
TAG ?= latest
PYTHON = python3
VENV = .venv
VENV_BIN = $(VENV)/bin

help: ## Mostrar esta ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Crear entorno virtual
	$(PYTHON) -m venv $(VENV)
	@echo "Entorno virtual creado. Activa con: source $(VENV_BIN)/activate"

install-deps: ## Instalar dependencias locales
	@if [ ! -d "$(VENV)" ]; then \
		echo "⚠️  Entorno virtual no encontrado. Ejecuta 'make venv' primero"; \
		exit 1; \
	fi
	$(VENV_BIN)/pip install -r api/requirements.txt
	$(VENV_BIN)/pip install -r locust/requirements.txt

train: ## Entrenar y guardar el modelo
	@if [ ! -d "$(VENV)" ]; then \
		echo "⚠️  Entorno virtual no encontrado. Creándolo..."; \
		$(MAKE) venv; \
		$(MAKE) install-deps; \
	fi
	$(VENV_BIN)/python api/train_model.py

build: train ## Construir la imagen Docker
	docker build -t $(IMAGE_NAME):$(TAG) .

push: build ## Publicar imagen en DockerHub
	docker tag $(IMAGE_NAME):$(TAG) $(DOCKER_USER)/$(IMAGE_NAME):$(TAG)
	docker push $(DOCKER_USER)/$(IMAGE_NAME):$(TAG)

run: ## Ejecutar la API con Docker Compose
	docker-compose -f docker-compose.api.yaml up -d

run-local: ## Ejecutar la API localmente (sin Docker)
	@if [ ! -d "$(VENV)" ]; then \
		echo "⚠️  Entorno virtual no encontrado. Ejecuta 'make venv' e 'make install-deps' primero"; \
		exit 1; \
	fi
	$(VENV_BIN)/python -m uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

test: ## Probar la API
	@chmod +x scripts/test_api.sh
	./scripts/test_api.sh

load: ## Iniciar pruebas de carga
	docker-compose -f docker-compose.load.yaml up -d
	@echo "Interfaz de Locust: http://localhost:8089"

scale: ## Escalar la API (uso: make scale REPLICAS=3)
	@if [ -z "$(REPLICAS)" ]; then \
		echo "❌ Error: Debes especificar REPLICAS"; \
		echo "Uso: make scale REPLICAS=2"; \
		exit 1; \
	fi
	docker-compose -f docker-compose.api.yaml up --scale api=$(REPLICAS) -d
	@echo "✅ API escalada a $(REPLICAS) réplica(s)"
	@echo "Ver estado: docker ps | grep api"

scale-load: ## Escalar API en ambiente de carga (uso: make scale-load REPLICAS=3)
	@if [ -z "$(REPLICAS)" ]; then \
		echo "❌ Error: Debes especificar REPLICAS"; \
		echo "Uso: make scale-load REPLICAS=2"; \
		exit 1; \
	fi
	docker-compose -f docker-compose.load.yaml up --scale api=$(REPLICAS) -d
	@echo "✅ API escalada a $(REPLICAS) réplica(s) en ambiente de carga"
	@echo "Ver estado: docker ps | grep api"

stats: ## Mostrar estadísticas de recursos
	docker stats

logs: ## Ver logs de la API
	docker-compose -f docker-compose.api.yaml logs -f

stop: ## Detener todos los servicios
	docker-compose -f docker-compose.api.yaml down
	docker-compose -f docker-compose.load.yaml down

clean: stop ## Limpiar contenedores e imágenes
	docker rmi $(IMAGE_NAME):$(TAG) || true
	docker system prune -f

clean-all: clean ## Limpiar todo incluyendo entorno virtual
	rm -rf $(VENV)
	rm -rf model/*.pkl
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Experimentos
experiment-1: ## Experimento 1: Configuración base
	@echo "Experimento 1: Configuración base (CPU: 0.5, MEM: 512M)"
	docker-compose -f docker-compose.load.yaml up -d
	@echo "Ir a http://localhost:8089 y ejecutar con 10000 usuarios, spawn rate 500"

experiment-scale-2: ## Experimento: Escalar a 2 réplicas en pruebas de carga
	@echo "🔬 Experimento: Escalando a 2 réplicas..."
	$(MAKE) scale-load REPLICAS=2
	@echo "📊 Ir a http://localhost:8089 y ejecutar prueba"
	@echo "💡 Monitorear: make stats"

experiment-scale-3: ## Experimento: Escalar a 3 réplicas en pruebas de carga
	@echo "🔬 Experimento: Escalando a 3 réplicas..."
	$(MAKE) scale-load REPLICAS=3
	@echo "📊 Ir a http://localhost:8089 y ejecutar prueba"
	@echo "💡 Monitorear: make stats"

# Atajos útiles
up: run ## Alias para run
down: stop ## Alias para stop
restart: stop run ## Reiniciar servicios

