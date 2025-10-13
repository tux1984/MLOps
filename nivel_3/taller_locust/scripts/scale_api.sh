#!/bin/bash
# Script para escalar la API fácilmente

set -e

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Número de réplicas
REPLICAS=${1:-1}

if [ -z "$1" ]; then
    echo "Uso: ./scale_api.sh NUMERO_REPLICAS"
    echo "Ejemplo: ./scale_api.sh 3"
    exit 1
fi

print_info "Escalando API a ${REPLICAS} réplica(s)..."

# Detener si está corriendo
docker-compose -f docker-compose.api.yaml down 2>/dev/null || true

# Iniciar con el número especificado de réplicas
docker-compose -f docker-compose.api.yaml up --scale api=${REPLICAS} -d

print_info "Esperando a que los contenedores estén listos..."
sleep 5

# Mostrar estado
print_info "Estado de los contenedores:"
docker-compose -f docker-compose.api.yaml ps

print_info ""
print_info "✅ API escalada a ${REPLICAS} réplica(s)"
print_info "Monitorea los recursos con: docker stats"

