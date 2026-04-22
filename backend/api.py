"""
╔═══════════════════════════════════════════════════════════════════╗
║                   PHISHGUARD BACKEND API                          ║
║              🚀 FastAPI Main Application Server                   ║
╚═══════════════════════════════════════════════════════════════════╝

TÊN FILE: backend/api.py

CÔNG DỤNG:
  - Khởi tạo ứng dụng FastAPI chính cho PhishGuard
  - Cấu hình CORS middleware để kết nối với frontend (Streamlit)
  - Kết nối tất cả routes (scan, feedback, health)
  - Khởi tạo database khi server startup
  - Quản lý lifecycle của ứng dụng

CÁC THÀNH PHẦN CHÍNH:
  • CORS: Cho phép kết nối từ http://localhost:8501 (Streamlit)
  • Routes: /scan (phát hiện), /feedback (phản hồi), /health (kiểm tra)
  • Database: Tự động khởi tạo bảng khi server start
  • Config: Tải từ environment variables (.env)

CÁCH CHẠY:
  uvicorn backend.api:app --reload --port 8000

PORT: 8000
TITLE: PhishGuard API v1.0.0
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import Config
from backend.models.database import init_db, health_check
import logging

logger = logging.getLogger(__name__)

# Import routes
from backend.routes import scan, feedback, health

app = FastAPI(
    title="PhishGuard API",
    version="1.0.0",
    description="AI-powered phishing detection API"
)

# =====================================================
# CORS MIDDLEWARE
# =====================================================
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8501",  # Streamlit default port
    "http://127.0.0.1:8501",
]

if Config.RENDER_EXTERNAL_URL:
    allowed_origins.append(Config.RENDER_EXTERNAL_URL)

if Config.RAILWAY_STATIC_URL:
    allowed_origins.append(Config.RAILWAY_STATIC_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# STARTUP & SHUTDOWN EVENTS
# =====================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database and validate configuration on startup"""
    logger.info("🚀 Starting PhishGuard API...")
    
    # Validate configuration
    if not Config.validate():
        logger.error("❌ Configuration validation failed")
        raise RuntimeError("Configuration validation failed")
    
    # Initialize database (don't crash if fails)
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning(f"⚠️  Database initialization failed: {str(e)}")
        logger.warning("⚠️  Continuing without database (app will work but data won't be saved)")
    
    logger.info("✅ PhishGuard API ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down PhishGuard API...")

# =====================================================
# ROUTES
# =====================================================

app.include_router(scan.router, prefix="/scan", tags=["Scan"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
app.include_router(health.router, prefix="/health", tags=["Health"])

@app.get("/")
def root():
    return {"message": "PhishGuard API is running 🚀", "version": "1.0.0"}

@app.get("/api-info")
def api_info():
    """Get API information (safe - no secrets exposed)"""
    return {
        "name": "PhishGuard API",
        "version": "1.0.0",
        "environment": Config.ENVIRONMENT,
        "database_configured": bool(Config.DATABASE_URL),
    }