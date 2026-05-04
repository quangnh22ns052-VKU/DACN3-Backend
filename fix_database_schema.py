"""
fix_database_schema.py
Thêm các cột bị thiếu vào bảng scans trong database
"""

from backend.models.database import engine, Base
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_missing_columns():
    """Thêm các cột bị thiếu: heuristic_result, ml_result, explanation"""
    
    with engine.connect() as conn:
        try:
            columns_to_add = [
                ('heuristic_result', "VARCHAR(50) DEFAULT 'UNKNOWN'"),
                ('ml_result', "VARCHAR(50) DEFAULT 'UNKNOWN'"),
                ('explanation', "TEXT"),
            ]
            
            for col_name, col_type in columns_to_add:
                # Kiểm tra xem cột đã tồn tại chưa
                result = conn.execute(text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'scans' AND column_name = '{col_name}'
                """))
                
                if result.fetchone():
                    logger.info(f"✅ Cột '{col_name}' đã tồn tại")
                else:
                    logger.info(f"➕ Thêm cột '{col_name}'...")
                    conn.execute(text(f"""
                        ALTER TABLE scans 
                        ADD COLUMN {col_name} {col_type}
                    """))
                    conn.commit()
                    logger.info(f"✅ Cột '{col_name}' đã thêm")
            
            logger.info("✅ Sửa schema database thành công!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Lỗi: {str(e)}")
            conn.rollback()
            return False

if __name__ == "__main__":
    logger.info("🔧 Bắt đầu sửa schema database...")
    add_missing_columns()
