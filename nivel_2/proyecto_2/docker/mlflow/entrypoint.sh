#!/bin/sh
set -euo pipefail

if [ -z "${BACKEND_STORE_URI:-}" ]; then
  echo "BACKEND_STORE_URI environment variable not set" >&2
  exit 1
fi

if [ -z "${DEFAULT_ARTIFACT_ROOT:-}" ]; then
  echo "DEFAULT_ARTIFACT_ROOT environment variable not set" >&2
  exit 1
fi

exec mlflow server \
  --host 0.0.0.0 \
  --port 5000 \
  --backend-store-uri "${BACKEND_STORE_URI}" \
  --default-artifact-root "${DEFAULT_ARTIFACT_ROOT}"
