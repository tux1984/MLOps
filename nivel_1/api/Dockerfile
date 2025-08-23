FROM python:3.11-slim

# Instalar dependencias del sistema necesarias para compilación
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requerimientos
COPY requirements.uv.txt .

# Instalar uv
RUN pip install uv

# Usar uv para instalar requerimientos
RUN uv pip install --system -r requirements.uv.txt

# Copiar código fuente de la API
COPY . /app

# Exponer puerto de FastAPI
EXPOSE 8000

# Comando de arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
