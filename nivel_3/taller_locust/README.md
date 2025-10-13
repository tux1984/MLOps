# Taller MLOps: API de Inferencia con FastAPI, Docker y Pruebas de Carga

**Equipo:** MLOps Equipo 8  

---

## 📖 Documentación Completa

**Para ver la documentación completa del proyecto, consulta:**

### 📚 [DOCUMENTACION_COMPLETA.md](./DOCUMENTACION_COMPLETA.md)

Este documento contiene:
- ✅ Resumen ejecutivo con resultados finales
- ✅ Análisis detallado de los 3 experimentos realizados
- ✅ Comparación de métricas y rendimiento
- ✅ Respuestas a todas las preguntas del taller
- ✅ Guía de uso rápida
- ✅ Troubleshooting y recomendaciones

---

## 🎯 Resultados Principales

### Configuración Óptima Encontrada

```yaml
Réplicas: 2
CPU por réplica: 1.0 core
Memoria por réplica: 1024MB
Total: 2.0 CPU, 2GB RAM
```

### Métricas Finales

| Métrica | Resultado | Objetivo | Estado |
|---------|-----------|----------|--------|
| **RPS** | 1,015 req/s | - | ✅ 3.5x mejor |
| **Tasa de Error** | 0.24% | < 1% | ✅ Cumplido |
| **Latencia P95** | 900ms | < 1,000ms | ✅ Cumplido |
| **Usuarios Soportados** | 10,000 | 10,000 | ✅ Cumplido |

### Comparación de Experimentos

| Config | CPU | RAM | RPS | Error % | P95 |
|--------|-----|-----|-----|---------|-----|
| **Exp 1:** 1 réplica | 0.5 | 512MB | 288 | 14.9% | 30s |
| **Exp 2:** 1 réplica | 1.0 | 1GB | 574 | 6.1% | 17s |
| **Exp 3:** 2 réplicas | 2.0 | 2GB | **1,015** | **0.24%** | **900ms** |

---

## 🚀 Inicio Rápido

### Prerequisitos

- Python 3.11+
- Docker y Docker Compose
- 4GB RAM disponibles

### Setup en 5 Minutos

```bash
# 1. Entrenar modelo
make train

# 2. Construir imagen
make build

# 3. Ejecutar con configuración óptima (2 réplicas)
make scale-load REPLICAS=2

# 4. Abrir Locust
open http://localhost:8089

# 5. Monitorear recursos
make stats
```

---

## 📁 Estructura del Proyecto

```
taller_locust/
├── api/                         # API FastAPI
│   ├── app.py                  # Aplicación principal
│   ├── model.py                # Gestor del modelo
│   └── train_model.py          # Entrenamiento
├── model/                       # Modelo ML
│   ├── model.pkl               # Random Forest (175KB)
│   └── metadata.pkl            # Metadata
├── locust/                      # Pruebas de carga
│   └── locustfile.py           # Scripts Locust
├── Dockerfile                   # Imagen API
├── docker-compose.api.yaml     # Despliegue
├── docker-compose.load.yaml    # Pruebas carga
├── Makefile                     # Comandos
├── README.md                    # Este archivo
└── DOCUMENTACION_COMPLETA.md   # 📚 Doc completa
```

---

## 🎓 Respuestas del Taller

### 1. ¿Recursos mínimos necesarios?

**2.0 CPU + 2GB RAM** (2 réplicas de 1.0 CPU + 1GB cada una)

### 2. ¿Reducir recursos con réplicas?

**NO**, pero se obtiene **mejor rendimiento** y **confiabilidad** (+77% RPS, -96% errores)

### 3. ¿Máximas peticiones soportadas?

**1,015 req/s sostenidos** con 99.76% de éxito

### 4. ¿Diferencia entre 1 vs múltiples instancias?

**Múltiples réplicas** ofrecen:
- ✅ +77% más throughput
- ✅ -96% menos errores
- ✅ -94% mejor latencia P95
- ✅ Alta disponibilidad

---

## 🔧 Comandos Útiles

```bash
# Ver todos los comandos disponibles
make help

# Ciclo completo de prueba
make scale-load REPLICAS=2
open http://localhost:8089
make stats

# Detener todo
make stop

# Limpiar
make clean-all
```

---

## 📊 Endpoints de la API

- `GET /` - Health check básico
- `GET /health` - Health check detallado con metadata
- `POST /predict` - Predicción del modelo ML
- `GET /docs` - Documentación Swagger interactiva

---

## 🐳 Imagen Docker

**Publicada en DockerHub:**
```bash
docker pull sefanchil/ml-inference-api:latest
```

**Uso:**
```bash
docker run -p 8000:8000 sefanchil/ml-inference-api:latest
curl http://localhost:8000/health
```

---

## 📈 Tecnologías Utilizadas

- **FastAPI** 0.115.0 - Framework web
- **scikit-learn** 1.5.2 - Machine Learning
- **Locust** 2.17.0 - Load testing
- **Docker** - Containerización
- **Python** 3.13 - Lenguaje base

---

## 📖 Documentación Adicional

Para información detallada sobre:
- Análisis completo de experimentos
- Gráficas y comparaciones
- Troubleshooting
- Recomendaciones para producción
- Lecciones aprendidas

**Consulta:** [DOCUMENTACION_COMPLETA.md](./DOCUMENTACION_COMPLETA.md)

---

## 👥 Equipo

**MLOps Equipo 8**  
Universidad Javeriana - 2025

