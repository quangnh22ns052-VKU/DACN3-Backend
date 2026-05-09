# Multi-stage build for backend
FROM python:3.9-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

# =====================================================
# FINAL STAGE
# =====================================================

FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy builder dependencies
COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

# =====================================================
# PYTHON SETTINGS
# =====================================================

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# =====================================================
# ENVIRONMENT VARIABLES
# =====================================================

ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000
ENV ALGORITHM=HS256
ENV ACCESS_TOKEN_EXPIRE_MINUTES=30
ENV LOG_LEVEL=INFO
ENV ENVIRONMENT=production

# =====================================================
# COPY SOURCE CODE
# =====================================================

COPY backend/ ./backend/
COPY core/ ./core/
COPY models/ ./models/
COPY data/ ./data/

# Optional
COPY scripts/ ./scripts/

RUN mkdir -p logs

# =====================================================
# CHECK MODEL EXISTS
# =====================================================

RUN if [ -f /app/models/tfidf_lr.pkl ]; then \
        echo "✅ ML model found: /app/models/tfidf_lr.pkl"; \
    else \
        echo "❌ ML model NOT FOUND!"; \
        exit 1; \
    fi

# =====================================================
# PORT
# =====================================================

EXPOSE 8000

# =====================================================
# HEALTHCHECK
# =====================================================

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl --fail http://localhost:8000/health || exit 1

# =====================================================
# START APP
# =====================================================

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]