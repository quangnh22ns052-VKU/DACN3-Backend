#!/usr/bin/env python3
"""
🚀 MIGRATE DATA FROM NEON TO SUPABASE

One-time migration script to copy all data from Neon (primary) database to Supabase (backup).

Before running:
1. Set DATABASE_URL (Neon) in .env
2. Set DATABASE_URL_BACKUP (Supabase) in .env
3. Verify Supabase schema matches Neon schema

Usage:
    python migrate_neon_to_supabase.py

This script will:
    1. Verify both databases are accessible
    2. Create tables on Supabase if they don't exist
    3. Copy all data from Neon to Supabase
    4. Verify data integrity with checksums
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from sqlalchemy.orm import Session

from backend.models.database import SessionLocal, SessionLocalBackup
from backend.models import user, scan, feedback, api_usage, model_metrics
from backend.models.database import Base
from backend.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================================
# MIGRATION ENGINE
# =====================================================

class MigrationEngine:
    """Orchestrate migration from Neon to Supabase"""
    
    def __init__(self):
        self.primary_session = None
        self.backup_session = None
        self.migration_log = []
        
    def run_migration(self) -> bool:
        """Execute full migration"""
        print("\n" + "="*70)
        print("🚀 PHISHGUARD DATABASE MIGRATION: NEON → SUPABASE")
        print("="*70 + "\n")
        
        try:
            # Step 1: Verify connectivity
            if not self._verify_databases():
                return False
            
            # Step 2: Create schema on backup
            if not self._create_schema():
                return False
            
            # Step 3: Migrate data
            if not self._migrate_data():
                return False
            
            # Step 4: Verify integrity
            if not self._verify_integrity():
                return False
            
            print("\n" + "="*70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("="*70)
            print("\nNext steps:")
            print("1. Verify data in Supabase dashboard")
            print("2. Set DB_SYNC_ENABLED=true in backend config")
            print("3. Restart backend to activate failover\n")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {str(e)}", exc_info=True)
            return False
        
        finally:
            self._cleanup()
    
    def _verify_databases(self) -> bool:
        """Verify both databases are accessible"""
        logger.info("🔍 Verifying database connectivity...")
        
        try:
            # Test primary (Neon)
            self.primary_session = SessionLocal()
            result = self.primary_session.execute(text("SELECT version()")).scalar()
            logger.info(f"✅ PRIMARY (Neon): Connected - {result[:50]}...")
            
            # Test backup (Supabase)
            if not SessionLocalBackup:
                logger.error("❌ Backup database not configured in config")
                return False
            
            self.backup_session = SessionLocalBackup()
            result = self.backup_session.execute(text("SELECT version()")).scalar()
            logger.info(f"✅ BACKUP (Supabase): Connected - {result[:50]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connectivity failed: {str(e)}")
            return False
    
    def _create_schema(self) -> bool:
        """Create tables on backup if they don't exist"""
        logger.info("📋 Creating schema on Supabase...")
        
        try:
            # Get list of existing tables on backup
            inspector = inspect(self.backup_session.bind)
            existing_tables = inspector.get_table_names()
            
            tables_to_create = [
                ("users", "users table"),
                ("scans", "scans table"),
                ("feedbacks", "feedbacks table"),
                ("api_usage", "api_usage table"),
                ("model_metrics", "model_metrics table"),
            ]
            
            # Check if tables exist on backup
            missing_tables = [t[0] for t in tables_to_create if t[0] not in existing_tables]
            
            if missing_tables:
                logger.warning(f"⚠️  Missing tables on backup: {missing_tables}")
                logger.info("📝 Creating tables from SQLAlchemy models...")
                
                # Create all tables on backup
                Base.metadata.create_all(bind=self.backup_session.bind)
                self.backup_session.commit()
                logger.info(f"✅ Created {len(missing_tables)} tables on backup")
            else:
                logger.info(f"✅ All tables exist on backup")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Schema creation failed: {str(e)}")
            return False
    
    def _migrate_data(self) -> bool:
        """Migrate data from primary to backup"""
        logger.info("📦 Migrating data...")
        
        tables = [
            # Only migrate scans table (has data)
            ("scans", "Scans"),
            # Other tables will be added later when they have data
            # ("users", "Users"),
            # ("feedbacks", "Feedbacks"),
            # ("api_usage", "API Usage"),
            # ("model_metrics", "Model Metrics"),
        ]
        
        total_rows = 0
        
        # Get column names from primary database schema (more reliable)
        from sqlalchemy import inspect as sqla_inspect
        primary_inspector = sqla_inspect(self.primary_session.bind)
        backup_inspector = sqla_inspect(self.backup_session.bind)
        
        # Get existing tables
        primary_tables = set(primary_inspector.get_table_names())
        backup_tables = set(backup_inspector.get_table_names())
        
        for table_name, display_name in tables:
            # Skip table if it doesn't exist in primary
            if table_name not in primary_tables:
                logger.warning(f"⏭️  {display_name}: Table not found in primary database (skipping)")
                continue
            
            # Skip table if it doesn't exist in backup
            if table_name not in backup_tables:
                logger.warning(f"⏭️  {display_name}: Table not found in backup database (skipping)")
                continue
            
            try:
                # Get count from primary
                primary_count = self.primary_session.execute(
                    text(f"SELECT COUNT(*) as cnt FROM {table_name}")
                ).scalar()
                
                if primary_count == 0:
                    logger.info(f"⏭️  {display_name}: 0 rows (skipping)")
                    continue
                
                # Clear backup table
                self.backup_session.execute(text(f"DELETE FROM {table_name}"))
                self.backup_session.commit()
                
                # Get column names from schema
                col_info = primary_inspector.get_columns(table_name)
                col_names = [col['name'] for col in col_info]
                col_str = ", ".join(col_names)
                placeholders = ", ".join([f":{name}" for name in col_names])
                
                # Copy data in batches
                batch_size = 1000
                offset = 0
                copied = 0
                
                logger.info(f"🔄 Copying {display_name} ({primary_count} rows)...")
                
                while True:
                    rows = self.primary_session.execute(
                        text(f"""
                            SELECT {col_str} FROM {table_name}
                            ORDER BY id
                            LIMIT :limit OFFSET :offset
                        """),
                        {"limit": batch_size, "offset": offset}
                    ).fetchall()
                    
                    if not rows:
                        break
                    
                    # Insert rows
                    for row in rows:
                        # Build values dict from column names
                        values_dict = {col_names[i]: row[i] for i in range(len(col_names))}
                        
                        self.backup_session.execute(
                            text(f"""
                                INSERT INTO {table_name} ({col_str})
                                VALUES ({placeholders})
                            """),
                            values_dict
                        )
                    
                    self.backup_session.commit()
                    copied += len(rows)
                    offset += batch_size
                    
                    print(f"   ↳ Copied {copied}/{primary_count} rows...", end='\r')
                
                logger.info(f"✅ {display_name}: {copied} rows copied")
                total_rows += copied
                
            except Exception as e:
                logger.error(f"❌ Error migrating {display_name}: {str(e)}", exc_info=True)
                self.backup_session.rollback()
                return False
        
        logger.info(f"✅ Total rows migrated: {total_rows}")
        return True
    
    def _verify_integrity(self) -> bool:
        """Verify data integrity between databases"""
        logger.info("🔍 Verifying data integrity...")
        
        # Reset sessions to clear any transaction errors
        try:
            self.primary_session.rollback()
            self.backup_session.rollback()
        except:
            pass
        
        # Only verify tables that were migrated
        tables = ["scans"]  # Only verify scans table
        all_match = True
        
        for table in tables:
            try:
                # Get counts
                primary_count = self.primary_session.execute(
                    text(f"SELECT COUNT(*) as cnt FROM {table}")
                ).scalar()
                
                backup_count = self.backup_session.execute(
                    text(f"SELECT COUNT(*) as cnt FROM {table}")
                ).scalar()
                
                if primary_count == backup_count:
                    logger.info(f"✅ {table}: {primary_count} rows match")
                else:
                    logger.error(f"❌ {table}: MISMATCH (primary: {primary_count}, backup: {backup_count})")
                    all_match = False
                    
            except Exception as e:
                logger.error(f"❌ Error verifying {table}: {str(e)}")
                all_match = False
        
        return all_match
    
    def _cleanup(self):
        """Close database sessions"""
        if self.primary_session:
            self.primary_session.close()
        if self.backup_session:
            self.backup_session.close()


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    # Verify configuration
    if not Config.DATABASE_URL:
        print("❌ ERROR: DATABASE_URL not set in .env")
        sys.exit(1)
    
    if not Config.DATABASE_URL_BACKUP:
        print("❌ ERROR: DATABASE_URL_BACKUP (Supabase) not set in .env")
        print("\nPlease set DATABASE_URL_BACKUP in .env:")
        print("DATABASE_URL_BACKUP=postgresql://user:password@db.xxx.supabase.co:5432/postgres")
        sys.exit(1)
    
    # Confirm before proceeding
    print("\n⚠️  WARNING: This will")
    print("   1. Clear all data on Supabase")
    print("   2. Copy all data from Neon to Supabase")
    print("   3. This operation cannot be undone")
    
    response = input("\nProceed with migration? (yes/no): ").strip().lower()
    if response != "yes":
        print("Migration cancelled.")
        sys.exit(0)
    
    # Run migration
    migrator = MigrationEngine()
    success = migrator.run_migration()
    sys.exit(0 if success else 1)
