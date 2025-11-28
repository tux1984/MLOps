#!/bin/bash

# Test services script - Verifies all services are running correctly

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

API_URL=${API_URL:-http://localhost:8000}
MLFLOW_URL=${MLFLOW_URL:-http://localhost:5001}
AIRFLOW_URL=${AIRFLOW_URL:-http://localhost:8080}
FRONTEND_URL=${FRONTEND_URL:-http://localhost:8501}

test_api() {
    echo -n "Testing API... "
    response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/health)
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗ (HTTP $response)${NC}"
        return 1
    fi
}

test_mlflow() {
    echo -n "Testing MLflow... "
    response=$(curl -s -o /dev/null -w "%{http_code}" $MLFLOW_URL)
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗ (HTTP $response)${NC}"
        return 1
    fi
}

test_airflow() {
    echo -n "Testing Airflow... "
    response=$(curl -s -o /dev/null -w "%{http_code}" $AIRFLOW_URL/health)
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗ (HTTP $response)${NC}"
        return 1
    fi
}

test_frontend() {
    echo -n "Testing Frontend... "
    response=$(curl -s -o /dev/null -w "%{http_code}" $FRONTEND_URL)
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗ (HTTP $response)${NC}"
        return 1
    fi
}

# TODO: Add more tests
# - Database connections
# - Model availability in MLflow
# - DAG status in Airflow
# - Prometheus metrics
# - Grafana dashboards

echo "========================================="
echo "Testing MLOps Services"
echo "========================================="
echo ""

test_api
test_mlflow
test_airflow
test_frontend

echo ""
echo "========================================="
echo "Service tests completed"
echo "========================================="
