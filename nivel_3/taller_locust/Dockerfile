# Dockerfile para la API de inferencia ML
FROM python:3.11-slim

# Información del maintainer
LABEL maintainer="MLOps Equipo 8"
LABEL description="API de inferencia ML con FastAPI"

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements primero (para aprovechar cache de Docker)
COPY api/requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Crear __init__.py vacío en el directorio raíz
RUN touch __init__.py

# Copiar código de la aplicación
COPY api/ ./api/

# Copiar modelo entrenado
COPY model/ ./model/

# Exponer puerto
EXPOSE 8000

# Variable de entorno para el puerto
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Comando para ejecutar la aplicación
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

