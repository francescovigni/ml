#!/usr/bin/env sh
set -eu

RUN_TESTS_ON_START="${RUN_TESTS_ON_START:-1}"

if [ "$RUN_TESTS_ON_START" = "1" ]; then
  echo "[entrypoint] Running startup tests..."
  # Avoid noisy output; fail fast on first error
  python -m pytest -q --maxfail=1 --disable-warnings tests || {
    echo "[entrypoint] Tests failed. Exiting." >&2
    exit 1
  }
  echo "[entrypoint] Tests passed. Starting server."
else
  echo "[entrypoint] Skipping startup tests (RUN_TESTS_ON_START=$RUN_TESTS_ON_START)"
fi

# Start via gunicorn, fall back to uvicorn if it fails
if command -v gunicorn >/dev/null 2>&1; then
  gunicorn -k uvicorn.workers.UvicornWorker -w ${ST_WORKERS:-1} -b 0.0.0.0:8000 src.server:app --timeout 300 || \
  uvicorn src.server:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300
else
  uvicorn src.server:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300
fi
