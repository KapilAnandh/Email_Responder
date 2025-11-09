# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

# --- Runtime hygiene ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=1

# --- System deps (curl for healthcheck; build-essential for some libs) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Install Python deps first (better layer caching) ---
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# --- App code ---
COPY . /app

# --- Non-root user ---
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# --- Sensible defaults (override at runtime) ---
ENV OLLAMA_BASE_URL="http://host.docker.internal:11434" \
    OLLAMA_MODEL="gemma3:270m" \
    EMBED_MODEL="nomic-embed-text" \
    GMAIL_SCOPES="read_only,send,modify" \
    GMAIL_USER="me"

# Persist Gmail tokens + ChromaDB locally (mount this)
VOLUME ["/app/data"]

# --- Healthcheck: verify Ollama is reachable ---
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 \
  CMD curl -fsS "$OLLAMA_BASE_URL/api/tags" >/dev/null || exit 1

# --- CLI entrypoint (pass subcommands at the end of docker run) ---
ENTRYPOINT ["python", "-m", "src.main"]