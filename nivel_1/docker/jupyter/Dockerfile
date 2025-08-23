FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.uv.txt .

# Instalar uv
RUN pip install uv

# Usar uv para instalar requerimientos
RUN uv pip install --system -r requirements.uv.txt

# Jupyter usa usuario no-root
RUN useradd -ms /bin/bash jovyan
USER jovyan
WORKDIR /home/jovyan/work

EXPOSE 8888
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--allow-root", "--NotebookApp.token=''"]
