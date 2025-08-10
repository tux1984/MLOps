# Dockerfile
FROM python:3.11-slim

# Ajustes básicos de Python y pip
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# (Opcional) instala utilidades mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Directorio de la app
WORKDIR /app

# Primero requirements para aprovechar cache de Docker
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos solo el código de la API (y cualquier módulo propio si lo tuvieras)
COPY api.py /app/

# Variables por defecto (puedes cambiarlas en runtime)
ENV RF_DIR="artifacts_rf" \
    LOGREG_DIR="artifacts_logreg" \
    DEFAULT_MODEL="rf"

# Exponemos el puerto de Uvicorn
EXPOSE 8000

# Creamos usuario no root por seguridad
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Comando por defecto: levanta la API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
