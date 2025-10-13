# 📚 Taller MLOps: API de Inferencia con FastAPI, Docker y Pruebas de Carga


**Equipo:** MLOps Equipo 8  
**Fecha:** Octubre 2025  
**Objetivo:** Implementar y optimizar una API de inferencia ML con pruebas de carga y escalamiento horizontal

---

## 📑 Tabla de Contenidos

1. [Resumen Ejecutivo](#-resumen-ejecutivo)
2. [Objetivos del Taller](#-objetivos-del-taller)
3. [Arquitectura y Tecnologías](#-arquitectura-y-tecnologías)
4. [Setup del Proyecto](#-setup-del-proyecto)
5. [Experimentos Realizados](#-experimentos-realizados)
6. [Análisis de Resultados](#-análisis-de-resultados)
7. [Conclusiones y Respuestas](#-conclusiones-y-respuestas)
8. [Guía de Uso Rápida](#-guía-de-uso-rápida)
9. [Troubleshooting](#-troubleshooting)

---

## 🎯 Resumen Ejecutivo

Este proyecto implementa una **API REST de inferencia ML** usando FastAPI, containerizada con Docker, y sometida a pruebas de carga exhaustivas usando Locust. Se realizaron **3 iteraciones experimentales** para encontrar la configuración óptima de recursos y estrategia de escalamiento.

### Logros Principales

✅ **API funcional** con modelo de clasificación Iris (Random Forest)  
✅ **Imagen Docker optimizada** publicada en DockerHub  
✅ **Pruebas de carga** soportando hasta 10,000 usuarios simultáneos  
✅ **Escalamiento horizontal** implementado sin Nginx  
✅ **Reducción de errores** de 14.9% → 6.1% → 0.24%  
✅ **Mejora de throughput** de 288 RPS → 574 RPS → 1015 RPS  

### Configuración Óptima Encontrada

```yaml
Réplicas: 2
CPU por réplica: 1.0 core
Memoria por réplica: 1024MB (1GB)
Total recursos: 2.0 cores, 2GB RAM

Resultados:
- RPS: 1015 req/s (3.5x mejor que config inicial)
- Latencia P95: 900ms (37x mejor)
- Tasa de error: 0.24% (62x mejor)
```

---

## 🎓 Objetivos del Taller

### Requisitos Funcionales

1. ✅ Crear imagen Docker con API FastAPI para inferencia ML
2. ✅ Consumir modelo entrenado (simulando MLflow)
3. ✅ Publicar imagen en DockerHub
4. ✅ Crear docker-compose para despliegue de la API
5. ✅ Crear docker-compose para pruebas de carga con Locust
6. ✅ Limitar recursos al mínimo para soportar 10,000 usuarios (500/s spawn rate)

### Requisitos de Rendimiento

- **Usuarios simultáneos:** 10,000
- **Spawn rate:** 500 usuarios/segundo
- **Tasa de error objetivo:** < 1%
- **Latencia P95 objetivo:** < 1,000ms

### Preguntas a Responder

1. ¿Cuáles son los recursos mínimos necesarios?
2. ¿Es posible reducir recursos con múltiples réplicas?
3. ¿Cuál es la mayor cantidad de peticiones soportadas?
4. ¿Qué diferencia hay entre una o múltiples instancias?

---

## 🏗️ Arquitectura y Tecnologías

### Stack Tecnológico

**Backend & API:**
- FastAPI 0.115.0
- Uvicorn 0.32.0
- Pydantic 2.9.2

**Machine Learning:**
- scikit-learn 1.5.2
- numpy 2.1.2
- joblib 1.4.2
- Modelo: Random Forest Classifier (Iris Dataset)

**Containerización:**
- Docker
- Docker Compose
- Python 3.11 slim (imagen base)

**Pruebas de Carga:**
- Locust 2.17.0
- Arquitectura Master-Worker (1 master + 2 workers)

### Estructura del Proyecto

```
taller_locust/
├── api/
│   ├── app.py              # Aplicación FastAPI
│   ├── model.py            # Gestor del modelo ML
│   ├── train_model.py      # Script de entrenamiento
│   ├── requirements.txt    # Dependencias
│   └── __init__.py         # Package marker
├── model/
│   ├── model.pkl          # Modelo entrenado (175KB)
│   └── metadata.pkl       # Metadata del modelo
├── locust/
│   ├── locustfile.py      # Scripts de pruebas
│   └── requirements.txt   # Dependencias
├── Dockerfile              # Imagen de la API
├── docker-compose.api.yaml     # Despliegue desarrollo
├── docker-compose.load.yaml    # Ambiente pruebas carga
├── Makefile               # Comandos automatizados
└── DOCUMENTACION_COMPLETA.md  # Este archivo
```

### Endpoints de la API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Health check básico |
| `/health` | GET | Health check detallado con metadata |
| `/predict` | POST | Inferencia del modelo ML |
| `/metrics` | GET | Métricas del modelo |
| `/docs` | GET | Documentación Swagger |

---

## 🚀 Setup del Proyecto

### Requisitos Previos

- Python 3.11+ (probado con 3.13)
- Docker & Docker Compose
- 4GB RAM disponibles para experimentos

### Instalación y Setup

```bash
# 1. Clonar/acceder al proyecto
cd taller_locust

# 2. Crear entorno virtual
make venv
# o: python3 -m venv .venv

# 3. Activar entorno virtual
source .venv/bin/activate

# 4. Instalar dependencias
make install-deps

# 5. Entrenar modelo
make train

# 6. Construir imagen Docker
make build

# 7. Publicar en DockerHub (opcional)
docker login
make push DOCKER_USER=tu-usuario
```


## 🧪 Experimentos Realizados

Se realizaron **3 iteraciones experimentales** con configuraciones progresivamente optimizadas.

### Configuración de Pruebas

**Parámetros constantes:**
- Usuarios totales: 10,000
- Spawn rate: 500 usuarios/segundo
- Duración: ~2 minutos por prueba
- Locust: 1 master + 2 workers

---

### 📊 Experimento 1: Configuración Base (1 Réplica)

**Objetivo:** Establecer baseline de rendimiento con recursos mínimos iniciales

#### Configuración
```yaml
Réplicas: 1
CPU: 0.5 cores
Memoria: 512MB
```

#### Resultados Detallados

| Endpoint | Requests | Failures | Failure % | RPS | P50 | P95 | P99 |
|----------|----------|----------|-----------|-----|-----|-----|-----|
| GET / | 628 | 39 | 6.2% | 5.2 | 790ms | 15s | 28s |
| GET /health | 2,810 | 1,384 | 49.3% | 23.5 | 16s | 69s | 81s |
| POST /predict | 31,028 | 3,720 | 12.0% | 259.1 | 810ms | 28s | 68s |
| **Agregado** | **34,466** | **5,143** | **14.9%** | **287.8** | **820ms** | **30s** | **69s** |

#### Errores Encontrados

| Error | Endpoint | Ocurrencias | % |
|-------|----------|-------------|---|
| ConnectionResetError | POST /predict | 2,867 | 55.7% |
| ConnectionResetError | GET /health | 1,235 | 24.0% |
| CatchResponseError (status 0) | POST /predict | 430 | 8.4% |
| ConnectTimeoutError | POST /predict | 423 | 8.2% |
| ConnectTimeoutError | GET /health | 149 | 2.9% |

#### Análisis

🔴 **FALLIDO - Recursos Insuficientes**

- ❌ Tasa de error: 14.9% (objetivo: <1%)
- ❌ Latencia P95: 30,000ms (objetivo: <1,000ms)
- ❌ Latencia P99: 69,000ms (inaceptable)
- ⚠️ 55.7% de errores por conexiones reseteadas
- ⚠️ Contenedor al límite de recursos

**Conclusión:** 0.5 CPU + 512MB es completamente insuficiente para la carga requerida.

---

### 📊 Experimento 2: Recursos Incrementados (1 Réplica)

**Objetivo:** Encontrar recursos mínimos para 1 réplica que soporte la carga

#### Configuración
```yaml
Réplicas: 1
CPU: 1.0 cores (↑ 100%)
Memoria: 1024MB / 1GB (↑ 100%)
```

#### Resultados Detallados

| Endpoint | Requests | Failures | Failure % | RPS | P50 | P95 | P99 |
|----------|----------|----------|-----------|-----|-----|-----|-----|
| GET / | 1,425 | 35 | 2.5% | 11.9 | 420ms | 760ms | 25s |
| GET /health | 4,581 | 1,265 | 27.6% | 38.3 | 550ms | 77s | 112s |
| POST /predict | 62,676 | 2,901 | 4.6% | 524.1 | 390ms | 940ms | 38s |
| **Agregado** | **68,682** | **4,201** | **6.1%** | **574.3** | **400ms** | **17s** | **55s** |

#### Errores Encontrados

| Error | Endpoint | Ocurrencias | % |
|-------|----------|-------------|---|
| ConnectionResetError | POST /predict | 2,588 | 61.6% |
| ConnectionResetError | GET /health | 1,265 | 30.1% |
| CatchResponseError (status 0) | POST /predict | 287 | 6.8% |
| ConnectTimeoutError | POST /predict | 26 | 0.6% |
| ConnectionResetError | GET / | 35 | 0.8% |

#### Mejoras vs Experimento 1

| Métrica | Exp 1 | Exp 2 | Mejora |
|---------|-------|-------|--------|
| RPS | 287.8 | 574.3 | **+99.5%** ⬆️ |
| Tasa de error | 14.9% | 6.1% | **-59.1%** ⬇️ |
| Latencia P50 | 820ms | 400ms | **-51.2%** ⬇️ |
| Total Requests | 34,466 | 68,682 | **+99.3%** ⬆️ |

#### Análisis

🟡 **MEJORADO - Pero Aún Insuficiente**

- 🟡 Tasa de error: 6.1% (objetivo: <1%) - **Mejor pero no suficiente**
- ✅ Latencia P50: 400ms (excelente)
- ❌ Latencia P95: 17,000ms (aún muy alta)
- ⬆️ RPS duplicado: de 288 a 574 req/s
- ⚠️ Endpoint /health sigue teniendo 27.6% de errores
- ⚠️ Aún hay 4,201 conexiones reseteadas

**Conclusión:** Duplicar recursos mejora significativamente pero no es suficiente. Se requiere escalamiento horizontal.

---

### 📊 Experimento 3: Escalamiento Horizontal (2 Réplicas)

**Objetivo:** Evaluar beneficio de múltiples réplicas vs una instancia más grande

#### Configuración
```yaml
Réplicas: 2 (↑ 100%)
CPU por réplica: 1.0 cores
Memoria por réplica: 1024MB
Total: 2.0 cores, 2GB RAM
```

#### Resultados Detallados

| Endpoint | Requests | Failures | Failure % | RPS | P50 | P95 | P99 |
|----------|----------|----------|-----------|-----|-----|-----|-----|
| GET / | 2,450 | 0 | 0.0% | 20.5 | 530ms | 910ms | 1,100ms |
| GET /health | 5,936 | 172 | 2.9% | 49.6 | 550ms | 60s | 107s |
| POST /predict | 113,150 | 123 | 0.11% | 945.2 | 520ms | 890ms | 1,000ms |
| **Agregado** | **121,536** | **295** | **0.24%** | **1,015.3** | **520ms** | **900ms** | **1,100ms** |

#### Errores Encontrados

| Error | Endpoint | Ocurrencias | % |
|-------|----------|-------------|---|
| ConnectionResetError | GET /health | 172 | 58.3% |
| ConnectionResetError | POST /predict | 123 | 41.7% |

#### Comparación con Configuraciones Anteriores

| Métrica | 1 Réplica (0.5CPU) | 1 Réplica (1.0CPU) | 2 Réplicas (1.0CPU) | Mejora Total |
|---------|---------------------|---------------------|----------------------|--------------|
| **Total Requests** | 34,466 | 68,682 | **121,536** | **+252.6%** 🚀 |
| **RPS** | 287.8 | 574.3 | **1,015.3** | **+252.8%** 🚀 |
| **Tasa de Error** | 14.9% | 6.1% | **0.24%** | **-98.4%** ✅ |
| **Failures** | 5,143 | 4,201 | **295** | **-94.3%** ✅ |
| **Latencia P50** | 820ms | 400ms | **520ms** | **-36.6%** ✅ |
| **Latencia P95** | 30,000ms | 17,000ms | **900ms** | **-97.0%** 🎯 |
| **Latencia P99** | 69,000ms | 55,000ms | **1,100ms** | **-98.4%** 🎯 |
| **CPU Total** | 0.5 | 1.0 | 2.0 | +300% |
| **Memoria Total** | 512MB | 1GB | 2GB | +292% |

#### Análisis

✅ **EXITOSO - Cumple Objetivos del Taller**

- ✅ Tasa de error: **0.24%** (objetivo: <1%) - **CUMPLIDO**
- ✅ Latencia P95: **900ms** (objetivo: <1,000ms) - **CUMPLIDO**
- ✅ Latencia P99: **1,100ms** (excelente)
- ✅ RPS: **1,015 req/s** - **3.5x mejor que config inicial**
- ✅ Endpoint GET / sin errores (0%)
- ✅ POST /predict con solo 0.11% de errores
- ⚠️ GET /health aún tiene 2.9% errores (posible mejora)

**Distribución de Carga:**
- Docker DNS balanceó automáticamente entre 2 réplicas
- Ambas réplicas mostraron uso similar de recursos (~50% CPU cada una)
- Sin hotspots ni desbalanceo significativo

**Conclusión:** El escalamiento horizontal con 2 réplicas es la **solución óptima** para este caso de uso.

---

## 📈 Análisis de Resultados

### Gráfica Comparativa de Rendimiento

```
RPS (Requests Per Second)
┌────────────────────────────────────────────────────┐
│ Exp 1 (0.5CPU, 1R)  ████████                288    │
│ Exp 2 (1.0CPU, 1R)  ████████████████        574    │
│ Exp 3 (1.0CPU, 2R)  ███████████████████████ 1,015  │
└────────────────────────────────────────────────────┘
                      +99%        +77%
```

```
Tasa de Error (%)
┌────────────────────────────────────────────────────┐
│ Exp 1 (0.5CPU, 1R)  ███████████████        14.9%   │
│ Exp 2 (1.0CPU, 1R)  ██████                  6.1%   │
│ Exp 3 (1.0CPU, 2R)  ▌                       0.24%  │
└────────────────────────────────────────────────────┘
          Objetivo: <1%  ───────────────────────✓
```

```
Latencia P95 (ms)
┌────────────────────────────────────────────────────┐
│ Exp 1 (0.5CPU, 1R)  ████████████████████  30,000   │
│ Exp 2 (1.0CPU, 1R)  ██████████████████    17,000   │
│ Exp 3 (1.0CPU, 2R)  ▌                        900   │
└────────────────────────────────────────────────────┘
          Objetivo: <1,000ms ────────────────────✓
```

### Análisis de Costo-Beneficio

| Config | CPU | RAM | RPS | Error% | Costo Relativo | Eficiencia (RPS/CPU) |
|--------|-----|-----|-----|--------|----------------|----------------------|
| Exp 1 | 0.5 | 512MB | 288 | 14.9% | 1x | 576 |
| Exp 2 | 1.0 | 1GB | 574 | 6.1% | 2x | 574 |
| Exp 3 | 2.0 | 2GB | 1,015 | 0.24% | 4x | **507.5** |

**Observación:** Aunque la eficiencia por CPU disminuye ligeramente con réplicas, la **mejora en confiabilidad y throughput** justifica el costo adicional.

### Tipos de Errores por Experimento

**Experimento 1:** Saturación completa
- 55.7% ConnectionResetError en /predict
- 24.0% ConnectionResetError en /health
- 8.4% CatchResponseError (contenedor murió)

**Experimento 2:** Sobrecarga intermitente
- 61.6% ConnectionResetError en /predict
- 30.1% ConnectionResetError en /health
- Menos timeouts (0.6% vs 11.1%)

**Experimento 3:** Estabilidad alcanzada
- Solo 295 errores totales (vs 5,143 y 4,201)
- Sin timeouts
- Sin status code 0
- Principalmente errores en /health (posible health check overhead)

### Análisis de Latencia

#### Percentiles de Latencia (ms)

| Config | P50 | P75 | P90 | P95 | P99 | P99.9 |
|--------|-----|-----|-----|-----|-----|-------|
| **Exp 1** | 820 | 1,100 | 18,000 | 30,000 | 69,000 | 97,000 |
| **Exp 2** | 400 | 540 | 740 | 17,000 | 55,000 | 112,000 |
| **Exp 3** | 520 | 680 | 820 | 900 | 1,100 | 107,000 |

**Insight:** Con 2 réplicas, el P95 y P99 mejoran dramáticamente, indicando que la mayoría de las peticiones se sirven rápidamente y solo casos excepcionales tienen latencias altas.

---

## 🎯 Conclusiones y Respuestas

### Respuestas a las Preguntas del Taller

#### 1. ¿Cuáles son los recursos mínimos necesarios?

**Para 1 Réplica:**
```yaml
CPU: 1.0 core (mínimo absoluto)
Memoria: 1024MB (1GB)
Resultado: 574 RPS, 6.1% errores (NO CUMPLE objetivo <1%)
```

**Para Cumplir Objetivos del Taller:**
```yaml
Configuración: 2 Réplicas
CPU por réplica: 1.0 core
Memoria por réplica: 1024MB
Total: 2.0 cores, 2GB RAM

Resultado: 1,015 RPS, 0.24% errores ✅
```

**Conclusión:** Los recursos mínimos **absolutos** son 2.0 CPU + 2GB RAM en configuración de 2 réplicas.

---

#### 2. ¿Es posible reducir recursos con múltiples réplicas?

**Respuesta: NO, pero se obtiene mejor rendimiento y confiabilidad**

| Enfoque | Config | CPU Total | RAM Total | RPS | Error % | ¿Cumple? |
|---------|--------|-----------|-----------|-----|---------|----------|
| 1 réplica grande | 1.0 CPU | 1.0 | 1GB | 574 | 6.1% | ❌ |
| 2 réplicas medianas | 2x 1.0 CPU | 2.0 | 2GB | 1,015 | 0.24% | ✅ |
| 2 réplicas pequeñas | 2x 0.5 CPU | 1.0 | 1GB | ~450* | ~8%* | ❌ |

*Estimado basado en tendencias observadas

**Trade-off:**
- 💰 **Costo:** 2 réplicas requieren el doble de recursos totales
- ⚡ **Rendimiento:** +77% más RPS
- 🛡️ **Confiabilidad:** -96% menos errores
- 🔄 **Resiliencia:** Si 1 réplica falla, la otra continúa

**Conclusión:** No se pueden reducir recursos totales con réplicas, pero se obtiene **mejor ROI** en términos de rendimiento y confiabilidad.

---

#### 3. ¿Cuál es la mayor cantidad de peticiones soportadas?

**Máximo Sostenido Encontrado:**

```
Configuración: 2 réplicas, 1.0 CPU + 1GB cada una
RPS Máximo: 1,015 requests/segundo
Throughput: ~60,900 requests/minuto
Con: 99.76% de éxito (0.24% errores)
```

**Extrapolación:**

Si escalamos linealmente:
- 3 réplicas: ~1,500 RPS estimado
- 4 réplicas: ~2,000 RPS estimado

**Límites Encontrados:**

- Con 0.5 CPU (1 réplica): ~288 RPS con 85% éxito
- Con 1.0 CPU (1 réplica): ~574 RPS con 94% éxito
- Con 2.0 CPU (2 réplicas): ~1,015 RPS con 99.76% éxito

**Conclusión:** Con la configuración óptima encontrada, el sistema soporta **1,015 req/s de manera sostenida** con excelente confiabilidad.

---

#### 4. ¿Qué diferencia hay entre una o múltiples instancias?

### Comparación Detallada

#### Una Instancia (1 Réplica)

**✅ Ventajas:**
- Configuración más simple
- Menos overhead de coordinación
- Menor uso total de recursos (si no necesita escalar)
- Más fácil de debuggear (un solo proceso)
- Sesiones y estado más fáciles de manejar

**❌ Desventajas:**
- Single Point of Failure (SPOF)
- Limitado por capacidad de 1 CPU
- No aprovecha paralelismo de múltiples cores
- Mayor latencia bajo carga (colas largas)
- Si falla, servicio completo cae

**📊 Rendimiento Observado:**
- RPS: 574
- Errores: 6.1%
- P95: 17 segundos
- Utilización CPU: ~95-100%

---

#### Múltiples Instancias (2 Réplicas)

**✅ Ventajas:**
- Alta disponibilidad (si una falla, otra continúa)
- Mejor distribución de carga
- Aprovecha paralelismo
- Menor latencia individual por réplica
- Escalamiento horizontal fácil
- Mejor manejo de picos de tráfico
- Degradación graceful (una réplica puede saturarse sin afectar a todas)

**❌ Desventajas:**
- Mayor complejidad operacional
- Más recursos totales requeridos
- Necesita load balancer (Docker DNS en nuestro caso)
- Sesiones stateful más complejas de manejar
- Mayor costo de infraestructura

**📊 Rendimiento Observado:**
- RPS: 1,015 (+77%)
- Errores: 0.24% (-96%)
- P95: 900ms (-94%)
- Utilización CPU: ~50% cada réplica (mejor distribución)

---

### Tabla Comparativa Final

| Aspecto | 1 Réplica | 2 Réplicas | Ganador |
|---------|-----------|------------|---------|
| **Throughput (RPS)** | 574 | 1,015 | 🏆 2R (+77%) |
| **Confiabilidad** | 93.9% | 99.76% | 🏆 2R |
| **Latencia P95** | 17s | 900ms | 🏆 2R (-94%) |
| **Disponibilidad** | SPOF | Alta | 🏆 2R |
| **Costo Recursos** | 1x | 2x | 🏆 1R |
| **Complejidad** | Simple | Media | 🏆 1R |
| **Escalabilidad** | Limitada | Alta | 🏆 2R |
| **Resiliencia** | Baja | Alta | 🏆 2R |

**Conclusión General:** Para producción con requisitos de alta disponibilidad y rendimiento, **múltiples réplicas son superiores** a pesar del mayor costo en recursos.

---

## 🎓 Lecciones Aprendidas

### 1. Escalamiento Vertical vs Horizontal

**Escalamiento Vertical (más recursos por instancia):**
- Mejora rendimiento linealmente hasta cierto punto
- Límite físico de una máquina
- Duplicar recursos (0.5→1.0 CPU) duplicó RPS (288→574)
- Pero no fue suficiente para cumplir objetivos (<1% error)

**Escalamiento Horizontal (más instancias):**
- Mejora rendimiento y confiabilidad simultáneamente
- Sin límite teórico (agregar más réplicas)
- 2 réplicas lograron +77% RPS vs 1 réplica (con mismos recursos individuales)
- **Lección:** Para APIs stateless, horizontal > vertical

### 2. Importancia de Health Checks

El endpoint `/health` tuvo más errores relativamente:
- Exp 1: 49.3% de errores
- Exp 2: 27.6% de errores
- Exp 3: 2.9% de errores

**Razón:** Health checks frecuentes del Docker healthcheck + Locust crean overhead adicional.

**Recomendación:** Configurar health checks con intervalos más largos en producción.

### 3. Docker DNS Load Balancing

Docker DNS con round-robin funcionó sorprendentemente bien:
- Distribución equitativa (~50% cada réplica)
- Sin configuración adicional requerida
- Sin necesidad de Nginx para este caso
- **Suficientemente bueno** para la mayoría de casos

### 4. Importancia de Monitoreo

`docker stats` fue crucial para:
- Identificar réplicas saturadas
- Detectar límites de memoria
- Observar distribución de carga
- Tomar decisiones sobre escalamiento

### 5. Errores de Conexión como Indicador

`ConnectionResetError` fue el **indicador clave** de saturación:
- Alta tasa → Recursos insuficientes
- Baja tasa → Sistema saludable
- **Métrica más importante** que latencia promedio

---

## 🚀 Guía de Uso Rápida

### Setup Inicial (Una Vez)

```bash
# 1. Entrenar modelo
make train

# 2. Construir imagen
make build

# 3. Publicar en DockerHub (opcional)
docker login
make push DOCKER_USER=tu-usuario
```

### Ejecutar Pruebas de Carga

```bash
# Iniciar con configuración óptima (2 réplicas)
make scale-load REPLICAS=2

# Abrir Locust
open http://localhost:8089

# Configurar en UI:
# - Users: 10000
# - Spawn rate: 500
# - Click "Start swarming"

# Monitorear (en otra terminal)
make stats
```

### Experimentos con Diferentes Configuraciones

```bash
# 1 réplica
make load

# 2 réplicas (óptimo)
make scale-load REPLICAS=2

# 3 réplicas
make scale-load REPLICAS=3

# Detener
make stop
```

### Comandos Útiles

```bash
# Ver todas las opciones
make help

# Ver réplicas activas
docker ps | grep api

# Logs de una réplica específica
docker logs taller_locust-api-1

# Limpiar todo
make clean-all
```

---

## 📊 Anexo: Datos Completos de Experimentos

### Experimento 1 - Datos Completos

```csv
Type,Request Count,Failure Count,Median RT,Avg RT,RPS,Failures/s
GET /,628,39,790.0,2063.7,5.2,0.33
GET /health,2810,1384,16000.0,17594.3,23.5,11.56
POST /predict,31028,3720,810.0,4043.2,259.1,31.07
Aggregated,34466,5143,820.0,5111.9,287.8,42.95
```

### Experimento 2 - Datos Completos

```csv
Type,Request Count,Failure Count,Median RT,Avg RT,RPS,Failures/s
GET /,1425,35,420.0,1006.4,11.9,0.29
GET /health,4581,1265,550.0,14397.3,38.3,10.58
POST /predict,62676,2901,390.0,1942.5,524.1,24.26
Aggregated,68682,4201,400.0,2753.8,574.3,35.13
```

### Experimento 3 - Datos Completos

```csv
Type,Request Count,Failure Count,Median RT,Avg RT,RPS,Failures/s
GET /,2450,0,530.0,537.1,20.5,0.0
GET /health,5936,172,550.0,6782.1,49.6,1.44
POST /predict,113150,123,520.0,784.8,945.2,1.03
Aggregated,121536,295,520.0,1072.7,1015.3,2.46
```

---

**Fecha de Finalización:** Octubre 13, 2025  
**Equipo:** MLOps Equipo 8  

---
