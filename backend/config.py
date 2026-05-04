"""
╔═══════════════════════════════════════════════════════════════════╗
║              PHISHGUARD CONFIGURATION MANAGER                     ║
║         ⚙️ Load Environment Variables & Settings                  ║
╚═══════════════════════════════════════════════════════════════════╝

TÊN FILE: backend/config.py

CÔNG DỤNG:
  - Tải tất cả environment variables từ file .env
  - Lưu trữ cài đặt cho Database, API, Security
  - Quản lý cấu hình cho các môi trường khác nhau (local, production)
  - Cung cấp giá trị mặc định nếu biến không được set

CÁC BIẾN CHÍNH:
  • DATABASE_URL: Đường dẫn kết nối PostgreSQL
  • API Keys: Google Safe Browsing, VirusTotal, AbuseIPDB
  • Ports: Cổng cho Backend, Frontend
  • Security: JWT secret, encryption keys

CÁCH SỬ DỤNG:
  from backend.config import Config
  db_url = Config.DATABASE_URL
  api_key = Config.GSB_API_KEY

LƯU Ý: Không được commit file .env, chỉ commit .env.example
"""

from dotenv import load_dotenv
import os
import logging
from typing import Optional

load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    # =====================================================
    # DATABASE CONFIGURATION
    # =====================================================
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.warning("⚠️  DATABASE_URL not set in .env")
    
    # Connection Pool Settings
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    
    # =====================================================
    # SECURITY & AUTHENTICATION
    # =====================================================
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # ENVIRONMENT setting (development allows missing SECRET_KEY)
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    if ENVIRONMENT == "production" and not SECRET_KEY:
        logger.warning("⚠️  SECRET_KEY not set in production mode - JWT tokens may fail")
    
    # =====================================================
    # API KEYS (Threat Intelligence Services)
    # =====================================================
    # NOTE: Never log or print API keys
    _VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
    _GSB_API_KEY = os.getenv("GSB_API_KEY")
    _ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY")
    
    @staticmethod
    def get_api_key(key_name: str) -> Optional[str]:
        """Safely get API key without logging"""
        key_map = {
            "virustotal": Config._VIRUSTOTAL_API_KEY,
            "gsb": Config._GSB_API_KEY,
            "abuseipdb": Config._ABUSEIPDB_API_KEY,
        }
        return key_map.get(key_name.lower())
    
    # =====================================================
    # ENVIRONMENT SETTINGS
    # =====================================================
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # =====================================================
    # CLOUD DEPLOYMENT
    # =====================================================
    RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
    RAILWAY_STATIC_URL = os.getenv("RAILWAY_STATIC_URL")
    APPRUNNER_URL = os.getenv("APPRUNNER_URL")  # AWS AppRunner
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")
    
    @staticmethod
    def validate():
        """Validate critical configuration at startup"""
        import sys
        errors = []
        warnings = []
        
        # DATABASE_URL validation
        if not Config.DATABASE_URL:
            msg = "⚠️  DATABASE_URL not set - database features will be unavailable"
            warnings.append(msg)
            logger.warning(msg)
            print(msg, flush=True, file=sys.stdout)
        elif "localhost" in Config.DATABASE_URL and Config.ENVIRONMENT == "production":
            msg = "⚠️  DATABASE_URL points to localhost in production - this will fail on cloud!"
            warnings.append(msg)
            logger.warning(msg)
            print(msg, flush=True, file=sys.stdout)
            print("💡 Use Neon (https://console.neon.tech/) or AWS RDS for cloud database", flush=True, file=sys.stdout)
        
        if Config.ENVIRONMENT == "production":
            if not Config.SECRET_KEY:
                errors.append("SECRET_KEY required in production")
            if not any([Config.RENDER_EXTERNAL_URL, Config.RAILWAY_STATIC_URL, Config.APPRUNNER_URL]):
                errors.append("Cloud deployment URL not configured (RENDER_EXTERNAL_URL, RAILWAY_STATIC_URL, or APPRUNNER_URL)")
        
        if errors:
            error_msg = "❌ Configuration errors: " + "; ".join(errors)
            logger.error(error_msg)
            print(error_msg, flush=True, file=sys.stdout)
            return False
        
        logger.info("✅ Configuration validated successfully")
        print("✅ Configuration validated successfully", flush=True, file=sys.stdout)
        return True