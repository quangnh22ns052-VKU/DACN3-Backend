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
    
    # Validate SECRET_KEY in production
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    if ENVIRONMENT == "production" and not SECRET_KEY:
        raise ValueError(
            "❌ CRITICAL: SECRET_KEY must be set in production environment!"
        )
    
    # =====================================================
    # API KEYS (Threat Intelligence Services)
    # =====================================================
    # NOTE: Never log or print API keys
    _VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
    _GSB_API_KEY = os.getenv("GSB_API_KEY")
    _ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY")
    
    @staticmethod
    def get_api_key(key_name: str) -> str | None:
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
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    @staticmethod
    def validate():
        """Validate critical configuration at startup"""
        errors = []
        
        if not Config.DATABASE_URL:
            errors.append("DATABASE_URL not configured")
        
        if Config.ENVIRONMENT == "production":
            if not Config.SECRET_KEY:
                errors.append("SECRET_KEY required in production")
            if not Config.RENDER_EXTERNAL_URL and not Config.RAILWAY_STATIC_URL:
                errors.append("Cloud deployment URL not configured")
        
        if errors:
            logger.error("❌ Configuration errors: " + "; ".join(errors))
            return False
        
        logger.info("✅ Configuration validated successfully")
        return True