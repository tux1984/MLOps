#!/bin/bash

# Cleanup script - Removes all deployed resources

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

cleanup_docker() {
    log_info "Cleaning up Docker Compose deployment..."
    
    # Stop and remove containers
    docker-compose down -v
    
    # Remove images (optional)
    read -p "Do you want to remove Docker images? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down --rmi all
    fi
    
    log_info "Docker cleanup completed"
}

cleanup_kubernetes() {
    log_info "Cleaning up Kubernetes deployment..."
    
    # Delete all resources in mlops namespace
    kubectl delete namespace mlops --ignore-not-found=true
    
    log_info "Kubernetes cleanup completed"
}

# Main
echo "========================================="
echo "MLOps Cleanup Script"
echo "========================================="
echo ""

CLEANUP_TYPE=${1:-docker}

case $CLEANUP_TYPE in
    docker)
        cleanup_docker
        ;;
    kubernetes|k8s)
        cleanup_kubernetes
        ;;
    all)
        cleanup_docker
        cleanup_kubernetes
        ;;
    *)
        echo "Usage: $0 [docker|kubernetes|all]"
        exit 1
        ;;
esac

log_info "Cleanup completed successfully!"
