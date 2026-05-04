"""
╔═══════════════════════════════════════════════════════════════════╗
║           PHISHGUARD DATABASE CONFIGURATION & MODELS              ║
║         🗄️ SQLAlchemy ORM & Database Schema                      ║
╚═══════════════════════════════════════════════════════════════════╝

TÊN FILE: backend/models/database.py

CÔNG DỤNG:
  - Cấu hình kết nối PostgreSQL với SQLAlchemy
  - Định nghĩa các bảng dữ liệu (models) chính
  - Quản lý phiên làm việc (sessions) với database
  - Cung cấp functions để khởi tạo và kiểm tra database

CÁC BẢNG CHÍNH:
  • User: Thông tin người dùng
  • Scan: Lưu kết quả quét (URL, kết quả, thời gian)
  • Feedback: Phản hồi từ người dùng
  • APIUsage: Theo dõi số lần gọi API
  • ModelMetrics: Hiệu suất mô hình ML

CÁCH SỬ DỤNG:
  from backend.models.database import SessionLocal, User, Scan
  db = SessionLocal()
  user = db.query(User).filter(User.id == 1).first()
  scans = db.query(Scan).filter(Scan.result == "phishing").all()

CỌI STARTUP:
  • init_db(): Khởi tạo tất cả bảng khi app start
  • health_check(): Kiểm tra kết nối database

CỬ HẠN:
  - Kết nối pooling: 10 connections (mặc định)
  - Connection timeout: 30 giây
  - Pool recycle: 3600 giây (1 giờ)

Database
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
import logging
import threading

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# =====================================================
# DATABASE CONFIGURATION
# =====================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.warning(
        "⚠️  DATABASE_URL not set! "
        "App will start but database operations will fail. "
        "Set DATABASE_URL in environment variables."
    )
    # Set placeholder to allow import (will fail at connection time)
    DATABASE_URL = "postgresql://disabled:disabled@localhost/disabled"

# Get connection pool settings from environment
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# =====================================================
# CREATE SQLALCHEMY ENGINE
# =====================================================

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,              # Connections in pool when idle
    max_overflow=DB_MAX_OVERFLOW,        # Additional connections when busy
    pool_recycle=DB_POOL_RECYCLE,        # Recycle connections (1 hour)
    pool_pre_ping=True,                  # Test connection before using
    echo=False,                          # Set True for SQL debugging
)

# =====================================================
# CREATE SESSION FACTORY
# =====================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =====================================================
# BASE CLASS FOR ORM MODELS
# =====================================================

Base = declarative_base()

# =====================================================
# DATABASE FUNCTIONS
# =====================================================

def get_db() -> Session:
    """
    Dependency function for FastAPI to get database session.
    
    Usage in routes:
        from sqlalchemy.orm import Session
        from backend.models.database import get_db
        
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    Non-blocking: doesn't crash app if database is unavailable.
    
    Usage:
        from backend.models.database import init_db
        init_db()
    """
    import sys
    
    def _create_tables():
        try:
            # In development, drop and recreate to match current model schema
            if os.getenv("ENVIRONMENT") == "development":
                try:
                    Base.metadata.drop_all(bind=engine)
                    logger.warning("⚠️  Development mode: dropped existing tables")
                except:
                    pass
            
            Base.metadata.create_all(bind=engine)
            msg = "✅ Database initialized - all tables created"
            logger.info(msg)
            print(msg, flush=True, file=sys.stdout)
            return True
        except Exception as e:
            error_msg = f"⚠️  Failed to initialize database: {str(e)}"
            logger.warning(error_msg)
            print(error_msg, flush=True, file=sys.stdout)
            print("💡 Continuing without database - API will still work for non-DB operations", flush=True, file=sys.stdout)
            return False
    
    try:
        # Run with timeout to prevent hanging
        result = [False]
        thread = threading.Thread(target=lambda: result.append(_create_tables()))
        thread.daemon = True
        thread.start()
        thread.join(timeout=3)  # 3 second timeout
        
        if thread.is_alive():
            warning_msg = "⚠️  Database initialization timed out (database may be unreachable)"
            logger.warning(warning_msg)
            print(warning_msg, flush=True, file=sys.stdout)
            print("💡 Continuing without database - API will still work", flush=True, file=sys.stdout)
            return False
        
        return result[-1] if result else False
    
    except Exception as outer_e:
        outer_error = f"⚠️  Unexpected error in database initialization: {str(outer_e)}"
        logger.warning(outer_error)
        print(outer_error, flush=True, file=sys.stdout)
        return False


def health_check() -> bool:
    """
    Check if database is accessible and healthy.
    Non-blocking: returns False if database is unavailable.
    
    Usage:
        from backend.models.database import health_check
        if health_check():
            print("Database is healthy")
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.debug("✅ Database health check passed")
        return True
    except Exception as e:
        logger.debug(f"⚠️  Database health check failed: {str(e)}")
        return False


def drop_all_tables():
    """
    Drop all tables and recreate them.
    WARNING: This will delete all data!
    
    Usage:
        from backend.models.database import drop_all_tables
        drop_all_tables()  # Call once, then restart server
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("⚠️  All database tables dropped")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables recreated successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to drop/recreate tables: {str(e)}")
        return False
