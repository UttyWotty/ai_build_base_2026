# Container for OSI on Cloud Run: stage one builds the React frontend, stage two installs the Python backend,
# generates both synthetic worlds, the bridge, and the failure model, then serves the API and the frontend with uvicorn.
# The image is self-contained: no data volume, no database, and Gemini is reached through Vertex AI at run time.
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm ci --silent
COPY src/frontend ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    LLM_PROVIDER=gemini \
    FRONTEND_DIST_DIR=/app/frontend

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends make && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/backend ./src/backend
RUN python -m venv .venv && .venv/bin/pip install -q .

COPY Makefile ./
COPY semantic ./semantic
COPY evaluation ./evaluation
COPY demo ./demo
RUN make data models

COPY --from=frontend /frontend/dist ./frontend

EXPOSE 8080
# The shell expands the PORT Cloud Run injects; exec hands signals straight to uvicorn for a clean shutdown.
CMD ["sh", "-c", "exec .venv/bin/uvicorn copilot.api.server:app --host 0.0.0.0 --port ${PORT}"]
