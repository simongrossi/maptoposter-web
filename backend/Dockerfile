FROM python:3.11-slim-bookworm as builder

WORKDIR /app

# Install system dependencies for Matplotlib/GeoPandas
# gdal-bin libgdal-dev required for fiona/geopandas sometimes, 
# but binary wheels usually sufficient on standard linux now.
# However, let's be safe for matplotlib fonts and generic utils.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install dependencies into a virtual environment to copy later (multi-stage reduction)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Final Stage ---
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime libs only (if necessary, like libgl1 for some mpl backends, though Agg is usually fine)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY backend/ ./backend/
# Copy folders required by backend
COPY themes/ ./themes/
COPY fonts/ ./fonts/
# Pre-create folders
# We expect 'static/posters' to be mounted as volume
RUN mkdir -p static/posters .cache

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV CACHE_DIR=/.cache

# Expose API port
EXPOSE 8000

# Run FastAPI via Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
