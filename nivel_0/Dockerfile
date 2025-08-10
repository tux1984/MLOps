# =========================
# 1) Imagen base ligera
# =========================
FROM python:3.12-slim

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# =========================
# 2) Crear usuario no-root
# =========================
RUN useradd -m appuser
WORKDIR /app

# =========================
# 3) Instalar dependencias del sistema mínimas
# =========================
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# =========================
# 4) Copiar dependencias primero (cache de capas)
# =========================
COPY requirements.txt /app/requirements.txt

# =========================
# 5) Instalar dependencias de Python
# =========================
RUN pip install --no-cache-dir -r /app/requirements.txt

# =========================
# 6) Copiar el resto del proyecto
# =========================
COPY app /app/app
COPY artifacts /app/artifacts

# =========================
# 7) Configuración del contenedor
# =========================
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8989
ENV MODEL_PATH=/app/artifacts/model.joblib

# =========================
# 8) Comando de arranque
# =========================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8989"]
