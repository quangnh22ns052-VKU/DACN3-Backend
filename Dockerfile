# Multi-stage build for backend
FROM python:3.9-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY backend/ ./backend/
COPY core/ ./core/
COPY models/ ./models/
COPY data/ ./data/
COPY scripts/ ./scripts/
RUN mkdir -p logs

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# =====================================================
# DEFAULT ENVIRONMENT VARIABLES (Non-sensitive)
# Render/AWS will override with their own values
# =====================================================
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000
ENV ALGORITHM=HS256
ENV ACCESS_TOKEN_EXPIRE_MINUTES=30
ENV LOG_LEVEL=INFO
ENV ENVIRONMENT=development
ENV DB_POOL_SIZE=10
ENV DB_MAX_OVERFLOW=20
ENV DB_POOL_RECYCLE=3600

# API Keys & Secrets MUST be set via platform environment variables
# DO NOT add VIRUSTOTAL_API_KEY, SECRET_KEY, etc here!
# These will be set by Render/AWS at runtime

EXPOSE 8000

# Health check - Increased start-period for Render cold start
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl --fail http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
