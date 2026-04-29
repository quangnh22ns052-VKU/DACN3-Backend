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
    "http://localhost:8501",  # Streamlit local
    "http://127.0.0.1:8501",
]

# Add production/cloud URLs
if Config.RENDER_EXTERNAL_URL:
    allowed_origins.append(Config.RENDER_EXTERNAL_URL)

if Config.RAILWAY_STATIC_URL:
    allowed_origins.append(Config.RAILWAY_STATIC_URL)

if Config.APPRUNNER_URL:
    allowed_origins.append(Config.APPRUNNER_URL)

if Config.FRONTEND_URL and Config.FRONTEND_URL not in allowed_origins:
    allowed_origins.append(Config.FRONTEND_URL)

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
    logger.info(f"📍 Environment: {Config.ENVIRONMENT}")
    logger.info(f"📍 Database URL: {'✅ Set' if Config.DATABASE_URL else '⚠️ Not set'}")
    
    # Validate configuration (non-blocking warnings)
    Config.validate()
    
    # Initialize database (don't crash if fails - app can still serve health check)
    try:
        if Config.DATABASE_URL:
            init_db()
            logger.info("✅ Database initialized")
        else:
            logger.warning("⚠️  DATABASE_URL not configured - database features will be unavailable")
    except Exception as e:
        logger.warning(f"⚠️  Database initialization warning: {str(e)}")
        logger.warning("⚠️  Continuing without database (health check will still work)")
    
    # =====================================================
    # SELF-TEST: Verify API is working correctly
    # =====================================================
    logger.info("🧪 Running startup diagnostics...")
    
    # Test 1: Check Model Loading
    try:
        from backend.routes.scan import get_detector
        detector = get_detector()
        logger.info("✅ ML Model loaded successfully")
    except Exception as e:
        logger.error(f"❌ ML Model loading failed: {str(e)}")
    
    # Test 2: Database connectivity
    try:
        if Config.DATABASE_URL:
            from backend.models.database import health_check
            if health_check():
                logger.info("✅ Database connection verified")
            else:
                logger.warning("⚠️  Database health check failed")
    except Exception as e:
        logger.warning(f"⚠️  Database health check skipped: {str(e)}")
    
    # Test 3: Sample Prediction
    try:
        from backend.routes.scan import get_detector
        detector = get_detector()
        test_url = "https://example.com"
        result = detector.predict(test_url)
        logger.info(f"✅ Sample prediction successful: {test_url} → {result.get('label')}")
    except Exception as e:
        logger.error(f"❌ Sample prediction failed: {str(e)}")
    
    # Test 4: Configuration Summary
    logger.info("=" * 60)
    logger.info("📊 PhishGuard API Ready - Configuration Summary:")
    logger.info(f"  • Environment: {Config.ENVIRONMENT}")
    logger.info(f"  • Database: {'Configured ✅' if Config.DATABASE_URL else 'Disabled ⚠️'}")
    logger.info(f"  • ML Model: Loaded ✅")
    logger.info(f"  • CORS Origins: {len(allowed_origins)} endpoints allowed")
    logger.info(f"  • Port: {Config.BACKEND_PORT}")
    logger.info("=" * 60)
    logger.info("✅ PhishGuard API is READY for requests! 🚀")
    logger.info("=" * 60)

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