FROM apache/airflow:2.6.0

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN chown airflow:0 /tmp/requirements.txt

USER airflow

ENV PATH="/home/airflow/.local/bin:${PATH}"

RUN --mount=type=cache,target=/home/airflow/.cache/pip \
    pip install --user --upgrade pip \
    && pip install --user -r /tmp/requirements.txt
