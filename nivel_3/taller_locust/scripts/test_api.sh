#!/bin/bash
# Script para probar la API

set -e

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_URL=${1:-http://localhost:8000}

echo -e "${GREEN}🧪 Probando API en: ${API_URL}${NC}\n"

# Test 1: Health check
echo -e "${YELLOW}Test 1: Health Check${NC}"
curl -s "${API_URL}/health" | jq '.'
echo -e "\n"

# Test 2: Root endpoint
echo -e "${YELLOW}Test 2: Root Endpoint${NC}"
curl -s "${API_URL}/" | jq '.'
echo -e "\n"

# Test 3: Predicción - Setosa
echo -e "${YELLOW}Test 3: Predicción - Iris Setosa${NC}"
curl -s -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}' | jq '.'
echo -e "\n"

# Test 4: Predicción - Versicolor
echo -e "${YELLOW}Test 4: Predicción - Iris Versicolor${NC}"
curl -s -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"features": [6.0, 2.7, 5.1, 1.6]}' | jq '.'
echo -e "\n"

# Test 5: Predicción - Virginica
echo -e "${YELLOW}Test 5: Predicción - Iris Virginica${NC}"
curl -s -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"features": [7.2, 3.0, 5.8, 1.6]}' | jq '.'
echo -e "\n"

# Test 6: Error - características insuficientes
echo -e "${YELLOW}Test 6: Error - Características insuficientes${NC}"
curl -s -X POST "${API_URL}/predict" \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5]}' | jq '.'
echo -e "\n"

# Test 7: Métricas
echo -e "${YELLOW}Test 7: Métricas${NC}"
curl -s "${API_URL}/metrics" | jq '.'
echo -e "\n"

echo -e "${GREEN}✅ Pruebas completadas${NC}"
echo -e "Documentación interactiva: ${API_URL}/docs"

