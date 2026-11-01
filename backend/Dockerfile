# Backend MapPoster : API FastAPI + worker Celery (image commune)
# Base figee : python:3.11.11-slim-bookworm

FROM python:3.11.11-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# --- Image finale -----------------------------------------------------------
FROM python:3.11.11-slim-bookworm

WORKDIR /app

# Utilisateur non privilegie dedie.
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

# Bibliotheques runtime uniquement.
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=app:app backend/ ./backend/
COPY --chown=app:app themes/ ./themes/

# Le volume de cache OSM est monte sur /.cache : le repertoire doit exister
# dans l'image avec le bon proprietaire pour que le volume nomme herite de
# l'ownership a sa creation.
RUN mkdir -p /.cache /app/.cache /tmp/matplotlib \
    && chown -R app:app /.cache /app/.cache /tmp/matplotlib

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_ARENA_MAX=2 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    CACHE_DIR=/app/.cache \
    MPLCONFIGDIR=/tmp/matplotlib

USER app

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
