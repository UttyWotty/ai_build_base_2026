# Container for the operations copilot on Cloud Run: installs the package, generates both synthetic worlds, the bridge,
# and the failure model at build time, then serves the Streamlit app on the port Cloud Run provides.
# The image is self-contained: no data volume, no database, and the model is reached through Vertex AI at run time.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    LLM_PROVIDER=gemini

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends make && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m venv .venv && .venv/bin/pip install -q .

COPY Makefile ./
COPY semantic ./semantic
COPY evaluation ./evaluation
COPY demo ./demo
COPY .streamlit ./.streamlit
RUN make data models

EXPOSE 8080
# The shell expands the PORT Cloud Run injects; exec hands signals straight to Streamlit for a clean shutdown.
CMD ["sh", "-c", "exec .venv/bin/streamlit run src/backend/copilot/ui/app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true"]
