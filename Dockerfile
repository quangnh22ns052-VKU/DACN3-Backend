# =====================================================
# STAGE 1 - BUILD DEPENDENCIES
# =====================================================

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

# =====================================================
# STAGE 2 - FINAL IMAGE
# =====================================================

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages
COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

# =====================================================
# PYTHON SETTINGS
# =====================================================

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# =====================================================
# APP ENVIRONMENT
# =====================================================

ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000
ENV LOG_LEVEL=INFO
ENV ENVIRONMENT=production

# =====================================================
# COPY SOURCE CODE
# =====================================================

COPY backend/ ./backend/
COPY core/ ./core/
COPY models/ ./models/
COPY data/ ./data/

# KHÔNG copy scripts lên production
# COPY scripts/ ./scripts/

RUN mkdir -p logs

# =====================================================
# PORT
# =====================================================

EXPOSE 8000

# =====================================================
# HEALTH CHECK
# =====================================================

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl --fail http://localhost:8000/health || exit 1

# =====================================================
# START SERVER
# =====================================================

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]