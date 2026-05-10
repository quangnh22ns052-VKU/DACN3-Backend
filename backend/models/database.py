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
# DATABASE CONFIGURATION - DUAL DATABASE SUPPORT
# =====================================================

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL_BACKUP = os.getenv("DATABASE_URL_BACKUP")

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

# Dual database configuration
DB_SYNC_ENABLED = os.getenv("DB_SYNC_ENABLED", "true").lower() == "true"
DB_FAILOVER_ENABLED = os.getenv("DB_FAILOVER_ENABLED", "true").lower() == "true"

# =====================================================
# DATABASE STATUS TRACKING
# =====================================================

class DatabaseStatus:
    """Track which database is currently active"""
    primary_active = True  # True = using DATABASE_URL, False = using DATABASE_URL_BACKUP
    backup_available = bool(DATABASE_URL_BACKUP)
    
    @staticmethod
    def switch_to_backup():
        DatabaseStatus.primary_active = False
        logger.warning("🔄 SWITCHED TO BACKUP DATABASE (Supabase)")
    
    @staticmethod
    def switch_to_primary():
        DatabaseStatus.primary_active = True
        logger.info("🔄 SWITCHED BACK TO PRIMARY DATABASE (Neon)")
    
    @staticmethod
    def get_active_db():
        if DatabaseStatus.primary_active:
            return DATABASE_URL
        return DATABASE_URL_BACKUP

# =====================================================
# CREATE SQLALCHEMY ENGINES (PRIMARY + BACKUP)
# =====================================================

def _create_engine(database_url, engine_name="primary"):
    """Create SQLAlchemy engine with proper configuration"""
    try:
        return create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            pool_recycle=DB_POOL_RECYCLE,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
            echo=False,
        )
    except Exception as e:
        logger.error(f"❌ Failed to create {engine_name} engine: {str(e)}")
        raise

# Create primary engine
engine = _create_engine(DATABASE_URL, "primary")

# Create backup engine if available
backup_engine = None
if DATABASE_URL_BACKUP and DB_FAILOVER_ENABLED:
    try:
        backup_engine = _create_engine(DATABASE_URL_BACKUP, "backup")
        logger.info("✅ Backup database (Supabase) engine initialized")
    except Exception as e:
        logger.warning(f"⚠️  Backup engine initialization failed: {str(e)}")

# =====================================================
# FAILOVER ENGINE SELECTOR
# =====================================================

def get_active_engine():
    """Get the currently active database engine with failover support"""
    if DatabaseStatus.primary_active:
        return engine
    elif backup_engine:
        return backup_engine
    else:
        return engine  # Fall back to primary if backup not available

# =====================================================
# CREATE SESSION FACTORY (WITH FAILOVER SUPPORT)
# =====================================================

def _create_session_factory(database_engine):
    """Create a session factory for the given engine"""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=database_engine
    )

# Primary session factory
SessionLocal = _create_session_factory(engine)

# Backup session factory (if available)
SessionLocalBackup = None
if backup_engine:
    SessionLocalBackup = _create_session_factory(backup_engine)

# =====================================================
# FAILOVER-AWARE SESSION FUNCTION
# =====================================================

def get_db_session():
    """Get database session with automatic failover support"""
    
    if DatabaseStatus.primary_active:
        try:
            session = SessionLocal()
            session.execute(text("SELECT 1"))
            session.commit()  # ✅ Thêm commit để clear transaction state
            return session
        except Exception as e:
            logger.warning(f"⚠️ Primary database failed: {str(e)}")
            try:
                session.close()
            except:
                pass
            
            if backup_engine and SessionLocalBackup and DB_FAILOVER_ENABLED:
                DatabaseStatus.switch_to_backup()
                logger.warning("🔄 SWITCHED TO BACKUP DATABASE (Supabase)")
                try:
                    backup_session = SessionLocalBackup()
                    backup_session.execute(text("SELECT 1"))
                    backup_session.commit()
                    return backup_session
                except Exception as e2:
                    logger.error(f"❌ Backup database also failed: {str(e2)}")
                    raise HTTPException(
                        status_code=503,
                        detail="Cả hai database đều không khả dụng"
                    )
            else:
                raise
    else:
        # Đang dùng Backup
        try:
            session = SessionLocalBackup()
            session.execute(text("SELECT 1"))
            session.commit()
            return session
        except Exception as e:
            logger.warning(f"⚠️ Backup database failed, switching back to primary: {str(e)}")
            try:
                session.close()
            except:
                pass
            DatabaseStatus.switch_to_primary()
            primary_session = SessionLocal()
            primary_session.execute(text("SELECT 1"))
            primary_session.commit()
            return primary_session
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
    Supports automatic failover to backup database.
    
    Usage in routes:
        from sqlalchemy.orm import Session
        from backend.models.database import get_db
        
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    try:
        db = get_db_session()  # Uses failover-aware session
        yield db
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        if 'db' in locals():
            db.rollback()
        raise
    finally:
        if 'db' in locals():
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
