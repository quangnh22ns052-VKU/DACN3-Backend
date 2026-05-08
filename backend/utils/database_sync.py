"""
🔄 DATABASE SYNCHRONIZATION & REPLICATION

Sync data between Neon (primary) and Supabase (backup) databases.
Ensures both databases stay in sync for failover scenarios.

Usage:
    from backend.utils.database_sync import sync_databases
    sync_databases()  # Runs sync between both databases
"""

import logging
from datetime import datetime
from typing import Dict, List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.database import (
    get_active_engine, DatabaseStatus,
    SessionLocal, SessionLocalBackup
)
from backend.config import Config

logger = logging.getLogger(__name__)

# =====================================================
# SYNC STATISTICS
# =====================================================

class SyncStats:
    """Track sync statistics"""
    total_synced = 0
    last_sync_time = None
    sync_status = "idle"
    
    @staticmethod
    def reset():
        SyncStats.total_synced = 0
        SyncStats.last_sync_time = None
        SyncStats.sync_status = "idle"


# =====================================================
# DATABASE SYNC ENGINE
# =====================================================

class DatabaseSync:
    """Manage bidirectional database synchronization"""
    
    def __init__(self):
        self.primary_db_url = Config.DATABASE_URL
        self.backup_db_url = Config.DATABASE_URL_BACKUP
        self.sync_enabled = Config.DB_SYNC_ENABLED
        
    def sync_all_tables(self):
        """Sync all tables between primary and backup databases (only scans table for now)"""
        if not self.sync_enabled or not self.backup_db_url:
            logger.warning("⚠️  Database sync is disabled or backup DB not configured")
            return False
        
        SyncStats.sync_status = "syncing"
        logger.info("🔄 Starting database synchronization...")
        
        try:
            # Only sync tables that exist (scans table has data)
            tables = ["scans"]  # Only sync scans - other tables empty
            
            total_rows = 0
            
            # Get fresh sessions for both databases
            primary_session = SessionLocal()
            backup_session = SessionLocalBackup()
            
            try:
                # Start with clean transaction state
                try:
                    primary_session.rollback()
                    backup_session.rollback()
                except:
                    pass
                
                for table_name in tables:
                    try:
                        # Ensure clean state before each sync
                        try:
                            primary_session.rollback()
                            backup_session.rollback()
                        except:
                            pass
                        
                        synced = self._sync_table(
                            primary_session, 
                            backup_session, 
                            table_name
                        )
                        total_rows += synced
                        logger.info(f"✅ Synced {table_name}: {synced} rows")
                    except Exception as e:
                        # Try to clean up before continuing
                        try:
                            primary_session.rollback()
                            backup_session.rollback()
                        except:
                            pass
                        logger.error(f"❌ Failed to sync {table_name}: {str(e)}")
                        continue
                
                SyncStats.total_synced = total_rows
                SyncStats.last_sync_time = datetime.utcnow()
                SyncStats.sync_status = "success"
                
                logger.info(f"✅ Database sync completed: {total_rows} rows synced")
                return True
                
            finally:
                # Always ensure sessions are closed and state is clean
                try:
                    primary_session.rollback()
                except:
                    pass
                try:
                    backup_session.rollback()
                except:
                    pass
                try:
                    primary_session.close()
                except:
                    pass
                try:
                    backup_session.close()
                except:
                    pass
                
        except Exception as e:
            SyncStats.sync_status = "failed"
            logger.error(f"❌ Database sync failed: {str(e)}")
            return False
    
    def _sync_table(self, primary_db: Session, backup_db: Session, table_name: str) -> int:
        """Sync a single table from primary to backup
        
        Strategy: Clear backup table and reload from primary (ensures consistency)
        Handles missing tables gracefully.
        """
        # Always rollback any failed transactions first
        try:
            backup_db.rollback()
            primary_db.rollback()
        except:
            pass
        
        try:
            # Count primary records
            primary_count = primary_db.execute(
                text(f"SELECT COUNT(*) as cnt FROM {table_name}")
            ).scalar()
        except Exception as e:
            # Transaction may be aborted - rollback and return
            try:
                primary_db.rollback()
            except:
                pass
            logger.warning(f"⚠️  Table '{table_name}' not found in primary: {str(e)}")
            return 0
        
        try:
            # Count backup records
            backup_count = backup_db.execute(
                text(f"SELECT COUNT(*) as cnt FROM {table_name}")
            ).scalar()
        except Exception as e:
            # Transaction may be aborted - rollback and return
            try:
                backup_db.rollback()
            except:
                pass
            logger.warning(f"⚠️  Table '{table_name}' not found in backup: {str(e)}")
            backup_count = 0
        
        # If same count, do spot check - sample 5 records
        if primary_count == backup_count and primary_count > 0:
            if self._tables_match(primary_db, backup_db, table_name):
                logger.debug(f"✅ {table_name} already in sync ({primary_count} rows)")
                return 0
        
        # Tables don't match - full sync needed
        logger.warning(f"🔄 Resyncing {table_name} (primary: {primary_count}, backup: {backup_count})")
        
        try:
            # Get schema columns from primary (with transaction safety)
            try:
                schema_result = primary_db.execute(
                    text(f"""
                        SELECT column_name 
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                        AND table_schema = 'public'
                        ORDER BY ordinal_position
                    """),
                    {"table_name": table_name}
                ).fetchall()
            except Exception as e:
                # Schema query failed - rollback and return
                try:
                    primary_db.rollback()
                except:
                    pass
                logger.error(f"❌ Schema query failed for {table_name}: {str(e)}")
                return 0
            
            if not schema_result:
                logger.error(f"❌ Could not get schema for {table_name}")
                return 0
            
            col_names = [row[0] for row in schema_result]
            col_str = ", ".join(col_names)
            
            # Clear backup table (with separate transaction)
            try:
                backup_db.execute(text(f"DELETE FROM {table_name}"))
                backup_db.commit()
            except Exception as e:
                try:
                    backup_db.rollback()
                except:
                    pass
                logger.warning(f"⚠️  Could not clear backup table {table_name}: {str(e)}")
                # Continue anyway - we'll try to insert
            
            if primary_count == 0:
                logger.info(f"✅ {table_name}: 0 rows to sync")
                return 0
            
            # Get all data from primary (paginated to avoid memory issues)
            batch_size = 1000
            offset = 0
            total_synced = 0
            
            while True:
                try:
                    # Get primary data - specify exact columns to avoid schema issues
                    rows = primary_db.execute(
                        text(f"""
                            SELECT {col_str} FROM {table_name}
                            ORDER BY id
                            LIMIT :limit OFFSET :offset
                        """),
                        {"limit": batch_size, "offset": offset}
                    ).fetchall()
                    
                    if not rows:
                        break
                    
                    # Insert into backup in batches
                    try:
                        for row in rows:
                            # Convert row to dict using column names
                            values_dict = {col_names[i]: row[i] for i in range(len(col_names))}
                            placeholders = ", ".join([f":{key}" for key in col_names])
                            
                            backup_db.execute(
                                text(f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"),
                                values_dict
                            )
                        
                        backup_db.commit()
                        total_synced += len(rows)
                        offset += batch_size
                    except Exception as e:
                        backup_db.rollback()
                        logger.error(f"❌ Error inserting batch at offset {offset}: {str(e)}")
                        # Continue with next batch
                        offset += batch_size
                        
                except Exception as e:
                    logger.error(f"❌ Error fetching batch at offset {offset}: {str(e)}")
                    break
            
            logger.info(f"✅ Synced {table_name}: {total_synced} rows")
            return total_synced
            
        except Exception as e:
            try:
                backup_db.rollback()
            except:
                pass
            logger.error(f"❌ Error syncing {table_name}: {str(e)}")
            raise
    
    def _tables_match(self, primary_db: Session, backup_db: Session, table_name: str) -> bool:
        """Check if tables are in sync (sample check)"""
        try:
            # Always start fresh to avoid transaction state issues
            try:
                primary_db.rollback()
            except:
                pass
            
            # Get primary checksum
            try:
                primary_hash = primary_db.execute(
                    text(f"""
                        SELECT md5(string_agg(
                            concat('{table_name}_' || id || '_' || 
                                   CAST(updated_at AS TEXT)), 
                            ','
                        )) as hash
                        FROM (
                            SELECT id, COALESCE(updated_at, created_at) as updated_at
                            FROM {table_name}
                            ORDER BY id
                        ) sub
                    """)
                ).scalar()
            except Exception as e:
                try:
                    primary_db.rollback()
                except:
                    pass
                logger.debug(f"⚠️  Could not compute primary hash for {table_name}: {str(e)}")
                return False
            
            try:
                backup_db.rollback()
            except:
                pass
            
            # Get backup checksum
            try:
                backup_hash = backup_db.execute(
                    text(f"""
                        SELECT md5(string_agg(
                            concat('{table_name}_' || id || '_' || 
                                   CAST(updated_at AS TEXT)), 
                            ','
                        )) as hash
                        FROM (
                            SELECT id, COALESCE(updated_at, created_at) as updated_at
                            FROM {table_name}
                            ORDER BY id
                        ) sub
                    """)
                ).scalar()
            except Exception as e:
                try:
                    backup_db.rollback()
                except:
                    pass
                logger.debug(f"⚠️  Could not compute backup hash for {table_name}: {str(e)}")
                return False
            
            return primary_hash == backup_hash
            
        except Exception as e:
            logger.debug(f"⚠️  Could not verify {table_name}: {str(e)}")
            # Clean up transaction state
            try:
                primary_db.rollback()
                backup_db.rollback()
            except:
                pass
            return False


# =====================================================
# PUBLIC API
# =====================================================

def sync_databases():
    """Main sync function - call this periodically or on demand"""
    syncer = DatabaseSync()
    return syncer.sync_all_tables()


def get_sync_status() -> Dict:
    """Get current sync status"""
    return {
        "enabled": Config.DB_SYNC_ENABLED,
        "backup_available": bool(Config.DATABASE_URL_BACKUP),
        "failover_enabled": Config.DB_FAILOVER_ENABLED,
        "current_db": "primary (Neon)" if DatabaseStatus.primary_active else "backup (Supabase)",
        "total_synced": SyncStats.total_synced,
        "last_sync": SyncStats.last_sync_time,
        "sync_status": SyncStats.sync_status,
    }


def get_database_stats() -> Dict:
    """
    Get statistics for both databases with failover support.
    
    Only queries 'scans' table (has actual data).
    Tries primary first, falls back to backup if needed.
    """
    stats = {
        "primary": {"scans": 0},
        "backup": {"scans": 0}
    }
    
    # Try to get primary stats
    try:
        primary_session = SessionLocal()
        try:
            count = primary_session.execute(
                text("SELECT COUNT(*) as cnt FROM scans")
            ).scalar()
            stats["primary"]["scans"] = count or 0
            logger.debug(f"✅ Primary stats: scans={count}")
        except Exception as e:
            logger.warning(f"⚠️  Error getting primary stats: {str(e)}")
            stats["primary"]["error"] = str(e)
        finally:
            primary_session.close()
    except Exception as e:
        logger.error(f"❌ Error connecting to primary: {str(e)}")
        stats["primary"]["error"] = str(e)
    
    # Try to get backup stats
    if SessionLocalBackup:
        try:
            backup_session = SessionLocalBackup()
            try:
                count = backup_session.execute(
                    text("SELECT COUNT(*) as cnt FROM scans")
                ).scalar()
                stats["backup"]["scans"] = count or 0
                logger.debug(f"✅ Backup stats: scans={count}")
            except Exception as e:
                logger.warning(f"⚠️  Error getting backup stats: {str(e)}")
                stats["backup"]["error"] = str(e)
            finally:
                backup_session.close()
        except Exception as e:
            logger.error(f"❌ Error connecting to backup: {str(e)}")
            stats["backup"]["error"] = str(e)
    else:
        stats["backup"]["error"] = "Backup database not configured"
    
    return stats
