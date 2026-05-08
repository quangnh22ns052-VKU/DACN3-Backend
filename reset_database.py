"""
reset_database.py
🔧 Reset database - xóa tất cả tables cũ và tạo lại schema sạch

Dùng khi:
  • Database bị corrupted
  • Transaction aborted error
  • Schema bị lỗi
  • Cần khởi tạo lại từ đầu

Usage:
  python reset_database.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import inspect, text, create_engine
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

def reset_database():
    """Xóa tất cả tables và tạo lại schema sạch"""
    
    from backend.models.database import engine, Base, SessionLocal
    from backend.models.user import User
    from backend.models.scan import Scan
    from backend.models.feedback import Feedback
    from backend.models.api_usage import APIUsage
    from backend.models.model_metrics import ModelMetrics
    
    logger.info("=" * 70)
    logger.info("🔧 RESET DATABASE - XÓA TABLES VÀ TẠO LẠI SCHEMA")
    logger.info("=" * 70)
    
    try:
        # 1️⃣ Drop all tables
        logger.info("\n📍 Bước 1: XÓA TẤT CẢ TABLES CŨ...")
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ Tất cả tables đã xóa")
        
        # 2️⃣ Create all tables
        logger.info("\n📍 Bước 2: TẠO LẠI SCHEMA...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Schema đã tạo lại")
        
        # 3️⃣ Verify tables
        logger.info("\n📍 Bước 3: KIỂM TRA TABLES...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"✅ Tổng {len(tables)} tables đã tạo:")
        for table_name in sorted(tables):
            columns = inspector.get_columns(table_name)
            col_names = [col['name'] for col in columns]
            logger.info(f"   • {table_name}: {', '.join(col_names)}")
        
        # 4️⃣ Test connection
        logger.info("\n📍 Bước 4: KIỂM TRA KẾT NỐI...")
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db.commit()
            logger.info("✅ Kết nối database OK")
        finally:
            db.close()
        
        # 5️⃣ Summary
        logger.info("\n" + "=" * 70)
        logger.info("✅ RESET DATABASE HOÀN TẤT!")
        logger.info("=" * 70)
        logger.info("\n📝 Tiếp theo:")
        logger.info("   1. Khởi động backend: uvicorn backend.api:app --reload")
        logger.info("   2. Khởi động frontend: streamlit run app/Home.py")
        logger.info("   3. Test ở: http://localhost:8501")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ LỖI: {str(e)}")
        logger.error(f"Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


def check_database_status():
    """Kiểm tra trạng thái database trước khi reset"""
    
    logger.info("=" * 70)
    logger.info("🔍 KIỂM TRA TRẠNG THÁI DATABASE")
    logger.info("=" * 70)
    
    from backend.models.database import engine, SessionLocal
    
    try:
        # Check connection
        logger.info("\n📍 Kiểm tra kết nối...")
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        logger.info("✅ Kết nối OK")
        
        # Check tables
        logger.info("\n📍 Kiểm tra tables hiện tại...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if tables:
            logger.info(f"✅ Tìm thấy {len(tables)} tables:")
            for table_name in sorted(tables):
                logger.info(f"   • {table_name}")
        else:
            logger.info("❌ Không tìm thấy tables")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ LỖI: {str(e)}")
        return False


if __name__ == "__main__":
    
    # Check environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL không được set!")
        logger.error("   Set biến environment DATABASE_URL trước khi chạy")
        sys.exit(1)
    
    logger.info(f"📌 Database URL: {db_url[:50]}...")
    
    # Check status before reset
    logger.info("\n")
    check_database_status()
    
    # Confirm before reset
    logger.info("\n" + "=" * 70)
    response = input("🚨 RESET sẽ XÓA TẤT CẢ DỮ LIỆU! Tiếp tục? (yes/no): ").strip().lower()
    
    if response != "yes":
        logger.info("❌ Đã hủy reset")
        sys.exit(0)
    
    # Reset database
    success = reset_database()
    sys.exit(0 if success else 1)
