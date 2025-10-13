#!/bin/bash
# Script para ejecutar pruebas de carga con diferentes configuraciones

set -e

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Valores por defecto
USERS=${1:-10000}
SPAWN_RATE=${2:-500}
RUN_TIME=${3:-5m}

print_info "Configuración de prueba de carga:"
echo "  - Usuarios: ${USERS}"
echo "  - Spawn rate: ${SPAWN_RATE} usuarios/seg"
echo "  - Duración: ${RUN_TIME}"
echo ""

# Verificar que docker-compose está corriendo
if ! docker ps | grep -q "ml-api-load-test"; then
    print_warning "La API no está corriendo"
    print_info "Iniciando docker-compose..."
    docker-compose -f docker-compose.load.yaml up -d
    
    print_info "Esperando a que la API esté lista..."
    sleep 10
fi

print_info "🚀 Iniciando prueba de carga..."
print_info "Interfaz web disponible en: http://localhost:8089"
echo ""

# Opción 1: Abrir interfaz web
read -p "¿Deseas usar la interfaz web? (y/n): " use_web

if [[ $use_web == "y" || $use_web == "Y" ]]; then
    print_info "Abriendo interfaz web..."
    
    # Detectar sistema operativo y abrir navegador
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open http://localhost:8089
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open http://localhost:8089 2>/dev/null || print_info "Abre manualmente: http://localhost:8089"
    else
        print_info "Abre manualmente: http://localhost:8089"
    fi
    
    print_info "Configura la prueba en la interfaz web y presiona 'Start swarming'"
    print_info "Monitorea los recursos con: docker stats"
else
    # Opción 2: Modo headless
    print_info "Ejecutando en modo headless..."
    
    REPORT_DIR="reports/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $REPORT_DIR
    
    print_info "Los reportes se guardarán en: ${REPORT_DIR}"
    
    docker-compose -f docker-compose.load.yaml run --rm locust-master \
        -f /mnt/locust/locustfile.py \
        --host=http://api:8000 \
        --users=${USERS} \
        --spawn-rate=${SPAWN_RATE} \
        --run-time=${RUN_TIME} \
        --headless \
        --html=/mnt/locust/report.html \
        --csv=/mnt/locust/results
    
    # Copiar reportes
    docker cp locust-master:/mnt/locust/report.html ${REPORT_DIR}/
    docker cp locust-master:/mnt/locust/results_stats.csv ${REPORT_DIR}/
    docker cp locust-master:/mnt/locust/results_stats_history.csv ${REPORT_DIR}/
    docker cp locust-master:/mnt/locust/results_failures.csv ${REPORT_DIR}/
    
    print_info "✅ Prueba completada"
    print_info "Reportes guardados en: ${REPORT_DIR}"
fi

print_info ""
print_info "📊 Para ver estadísticas de recursos, ejecuta:"
print_info "   docker stats ml-api-load-test"

