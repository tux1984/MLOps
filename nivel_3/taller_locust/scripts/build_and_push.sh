#!/bin/bash
# Script para construir y publicar la imagen Docker

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Verificar que se pasó el usuario de DockerHub
if [ -z "$1" ]; then
    print_error "Debes proporcionar tu usuario de DockerHub"
    echo "Uso: ./build_and_push.sh TU_USUARIO_DOCKERHUB [TAG]"
    exit 1
fi

DOCKER_USER=$1
TAG=${2:-latest}
IMAGE_NAME="ml-inference-api"
FULL_IMAGE_NAME="${DOCKER_USER}/${IMAGE_NAME}:${TAG}"

# Verificar que existe el modelo
if [ ! -f "model/model.pkl" ]; then
    print_warning "El modelo no existe. Ejecutando entrenamiento..."
    python api/train_model.py
fi

# Construir imagen
print_info "Construyendo imagen Docker: ${IMAGE_NAME}:${TAG}"
docker build -t ${IMAGE_NAME}:${TAG} .

# Etiquetar imagen
print_info "Etiquetando imagen para DockerHub: ${FULL_IMAGE_NAME}"
docker tag ${IMAGE_NAME}:${TAG} ${FULL_IMAGE_NAME}

# Verificar si está logueado en Docker
print_info "Verificando login de Docker..."
if ! docker info | grep -q "Username"; then
    print_warning "No estás logueado en DockerHub"
    print_info "Ejecutando docker login..."
    docker login
fi

# Push a DockerHub
print_info "Publicando imagen en DockerHub: ${FULL_IMAGE_NAME}"
docker push ${FULL_IMAGE_NAME}

print_info "✅ ¡Imagen publicada exitosamente!"
print_info "Imagen: ${FULL_IMAGE_NAME}"
print_info ""
print_info "Para usar esta imagen, actualiza los archivos docker-compose:"
print_info "  image: ${FULL_IMAGE_NAME}"

