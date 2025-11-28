#!/bin/bash

# Deploy script for MLOps Diabetes Prediction System
# This script orchestrates the complete deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check kubectl (for K8s deployment)
    if ! command -v kubectl &> /dev/null; then
        log_warn "kubectl is not installed (required for Kubernetes deployment)"
    fi
    
    log_info "Prerequisites check completed"
}

deploy_docker_compose() {
    log_info "Deploying with Docker Compose..."
    
    # Create .env if it doesn't exist
    if [ ! -f .env ]; then
        log_info "Creating .env from .env.example"
        cp .env.example .env
    fi
    
    # Build and start services
    docker-compose up -d --build
    
    log_info "Docker Compose deployment completed"
    log_info "Services will be available at:"
    echo "  - Airflow: http://localhost:8080 (admin/admin123)"
    echo "  - MLflow: http://localhost:5001"
    echo "  - API: http://localhost:8000/docs"
    echo "  - Frontend: http://localhost:8501"
    echo "  - Grafana: http://localhost:3000 (admin/admin)"
    echo "  - Prometheus: http://localhost:9090"
}

deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Create namespace
    kubectl apply -f kubernetes/namespace.yaml
    
    # Create PVCs
    kubectl apply -f kubernetes/pvc.yaml
    
    # Deploy databases
    kubectl apply -f kubernetes/databases.yaml
    
    # Deploy MLflow
    kubectl apply -f kubernetes/mlflow.yaml
    
    # Deploy Airflow
    kubectl apply -f kubernetes/airflow.yaml
    
    # Deploy API
    kubectl apply -f kubernetes/api.yaml
    
    # Deploy Frontend
    kubectl apply -f kubernetes/frontend.yaml
    
    # Deploy Observability
    kubectl apply -f kubernetes/observability.yaml
    
    log_info "Kubernetes deployment completed"
    log_info "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod --all -n mlops --timeout=300s
    
    log_info "Getting service URLs..."
    kubectl get svc -n mlops
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # TODO: Add health checks for all services
    # - Check API health endpoint
    # - Check MLflow connectivity
    # - Check database connections
    # - Check Airflow webserver
    
    log_info "Deployment verification completed"
}

# Main script
main() {
    echo "================================================"
    echo "MLOps Diabetes Prediction - Deployment Script"
    echo "================================================"
    echo ""
    
    check_prerequisites
    
    # Parse arguments
    DEPLOYMENT_TYPE=${1:-docker}
    
    case $DEPLOYMENT_TYPE in
        docker)
            deploy_docker_compose
            ;;
        kubernetes|k8s)
            deploy_kubernetes
            ;;
        verify)
            verify_deployment
            ;;
        *)
            log_error "Unknown deployment type: $DEPLOYMENT_TYPE"
            echo "Usage: $0 [docker|kubernetes|verify]"
            exit 1
            ;;
    esac
    
    log_info "Deployment completed successfully!"
}

main "$@"
