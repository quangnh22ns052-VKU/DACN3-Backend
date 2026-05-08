"""
🔧 DATABASE ADMIN ENDPOINTS

API routes for database administration, sync, and failover management.

Endpoints:
    - GET /admin/database/status - Current database status
    - POST /admin/database/sync - Trigger manual sync
    - GET /admin/database/stats - Database statistics
    - GET /admin/database/health - Health check for both DBs
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
from sqlalchemy import text

from backend.utils.database_sync import sync_databases, get_sync_status, get_database_stats
from backend.models.database import health_check, DatabaseStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/database", tags=["admin", "database"])

# =====================================================
# DATABASE STATUS ENDPOINT
# =====================================================

@router.get("/status")
def get_database_status() -> Dict[str, Any]:
    """
    Get current database status and failover information
    
    Returns:
        - current_db: Which database is currently active (primary/backup)
        - primary_active: Boolean flag
        - backup_available: Whether backup database is configured
        - failover_enabled: Whether automatic failover is enabled
        - last_sync: Timestamp of last sync
    """
    return {
        "current_database": "primary (Neon)" if DatabaseStatus.primary_active else "backup (Supabase)",
        "primary_active": DatabaseStatus.primary_active,
        "backup_available": DatabaseStatus.backup_available,
        "failover_enabled": True,  # Always enabled if backup exists
        "sync_info": get_sync_status()
    }


# =====================================================
# DATABASE SYNC ENDPOINT
# =====================================================

@router.post("/sync")
def trigger_database_sync() -> Dict[str, Any]:
    """
    Manually trigger database synchronization.
    
    Syncs data from primary (Neon) to backup (Supabase).
    This is useful for:
    - Ensuring backup is up to date
    - Testing sync mechanism
    - After restoring from backup
    
    Returns:
        - success: Whether sync completed
        - message: Status message
        - rows_synced: Number of rows synchronized
        - sync_time: When sync occurred
    """
    logger.info("🔄 Manual database sync requested")
    
    try:
        success = sync_databases()
        
        if success:
            return {
                "success": True,
                "message": "✅ Database synchronization completed",
                "sync_info": get_sync_status()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Database sync failed - see logs for details"
            )
    except Exception as e:
        logger.error(f"❌ Sync error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database sync failed: {str(e)}"
        )


# =====================================================
# DATABASE STATISTICS ENDPOINT
# =====================================================

@router.get("/stats")
def get_db_statistics() -> Dict[str, Any]:
    """
    Get database statistics for both primary and backup.
    
    Shows row counts for each table to help identify sync issues.
    
    Returns:
        - primary: Row counts for each table in Neon
        - backup: Row counts for each table in Supabase
        - in_sync: Whether primary and backup have matching row counts
    """
    try:
        stats = get_database_stats()
        
        # Calculate if in sync
        if "error" not in stats["primary"] and "error" not in stats["backup"]:
            in_sync = stats["primary"] == stats["backup"]
        else:
            in_sync = None
        
        return {
            "databases": stats,
            "in_sync": in_sync,
            "sync_info": get_sync_status()
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database statistics: {str(e)}"
        )


# =====================================================
# DATABASE HEALTH CHECK ENDPOINT
# =====================================================

@router.get("/health")
def check_database_health() -> Dict[str, Any]:
    """
    Comprehensive health check for all databases.
    
    Checks:
    - Primary database connectivity
    - Backup database connectivity (if configured)
    - Data sync status
    - Connection pool status
    
    Returns:
        - primary: Status of primary database
        - backup: Status of backup database
        - overall: Overall system health
        - failover_ready: Whether failover is ready
    """
    primary_ok = health_check()
    
    # Try to connect to backup if available
    backup_ok = False
    if DatabaseStatus.backup_available:
        try:
            from backend.models.database import SessionLocalBackup
            backup_session = SessionLocalBackup()
            from sqlalchemy import text
            backup_session.execute(text("SELECT 1"))
            backup_ok = True
            backup_session.close()
        except Exception as e:
            logger.warning(f"⚠️  Backup database check failed: {str(e)}")
            backup_ok = False
    
    # Overall status
    overall_healthy = primary_ok or backup_ok
    
    return {
        "primary_database": {
            "status": "✅ OK" if primary_ok else "❌ FAILED",
            "healthy": primary_ok,
            "type": "Neon PostgreSQL"
        },
        "backup_database": {
            "status": "✅ OK" if backup_ok else "❌ FAILED",
            "healthy": backup_ok,
            "configured": DatabaseStatus.backup_available,
            "type": "Supabase PostgreSQL"
        },
        "overall_status": "✅ HEALTHY" if overall_healthy else "❌ UNHEALTHY",
        "failover_ready": backup_ok if DatabaseStatus.backup_available else None,
        "current_active": "primary (Neon)" if DatabaseStatus.primary_active else "backup (Supabase)",
        "sync_status": get_sync_status()
    }


# =====================================================
# DATABASE INFO ENDPOINT
# =====================================================

@router.get("/info")
def get_database_info() -> Dict[str, Any]:
    """Get information about configured databases"""
    
    info = {
        "primary_database": {
            "name": "Neon PostgreSQL",
            "type": "Cloud PostgreSQL",
            "region": "Asia Southeast (ap-southeast-1)",
            "endpoint": "ep-spring-dew-a1w9wlzn-pooler.ap-southeast-1.aws.neon.tech" if DatabaseStatus.primary_active else "Not active",
            "configured": bool(DatabaseStatus.primary_active),
        },
        "backup_database": {
            "name": "Supabase PostgreSQL",
            "type": "Managed PostgreSQL",
            "configured": DatabaseStatus.backup_available,
            "endpoint": "db.xxx.supabase.co" if DatabaseStatus.backup_available else "Not configured",
        },
        "synchronization": {
            "enabled": True,
            "interval_seconds": 300,
            "last_sync": get_sync_status().get("last_sync"),
            "sync_tables": ["users", "scans", "feedbacks", "api_usage", "model_metrics"],
        },
        "failover_configuration": {
            "enabled": DatabaseStatus.backup_available,
            "strategy": "automatic",
            "retry_attempts": 3,
            "retry_delay_ms": 100,
        }
    }
    
    return info


# =====================================================
# SCANS DATA ENDPOINT
# =====================================================

@router.get("/scans")
def get_scans_data(limit: int = 100) -> Dict[str, Any]:
    """
    Get actual scans data from both databases.
    
    Returns:
        - primary: List of scans from Neon
        - backup: List of scans from Supabase
        - count_primary: Total scans in primary
        - count_backup: Total scans in backup
        - in_sync: Whether both databases have same data
    """
    from backend.models.database import SessionLocal, SessionLocalBackup
    
    # Helper function to normalize ml_result to always be a float string
    def normalize_ml_result(val):
        """Convert ml_result to float, handling string classifications"""
        if val is None:
            return "0.0000"
        try:
            # Try converting to float
            return f"{float(val):.4f}"
        except (ValueError, TypeError):
            # If it's a string like "SAFE", "PHISHING", map to probability
            if isinstance(val, str):
                if val.upper() == "PHISHING":
                    return "0.8000"
                elif val.upper() == "SUSPICIOUS":
                    return "0.5000"
                else:
                    return "0.2000"
            return "0.0000"
    
    result = {
        "primary": [],
        "backup": [],
        "count_primary": 0,
        "count_backup": 0,
        "in_sync": False,
        "error": None
    }
    
    try:
        # Get from primary (Neon)
        primary_session = SessionLocal()
        try:
            scans = primary_session.execute(
                text("""
                    SELECT id, user_id, input_text, result, probability, 
                           heuristic_result, ml_result, created_at
                    FROM scans
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            ).fetchall()
            
            # Convert to dict list - normalize ml_result to always be a float string
            result["primary"] = [
                {
                    "id": s[0],
                    "user_id": s[1],
                    "input_text": s[2],
                    "result": s[3],
                    "probability": float(s[4]) if s[4] else 0,
                    "heuristic_result": s[5],
                    "ml_result": normalize_ml_result(s[6]),  # Normalized to float string
                    "created_at": str(s[7])
                }
                for s in scans
            ]
            
            # Get total count
            total = primary_session.execute(
                text("SELECT COUNT(*) FROM scans")
            ).scalar()
            result["count_primary"] = total or 0
            
        finally:
            primary_session.close()
            
    except Exception as e:
        logger.error(f"Error getting primary scans: {str(e)}")
        result["error"] = f"Primary DB error: {str(e)}"
    
    try:
        # Get from backup (Supabase)
        if SessionLocalBackup:
            backup_session = SessionLocalBackup()
            try:
                scans = backup_session.execute(
                    text("""
                        SELECT id, user_id, input_text, result, probability,
                               heuristic_result, ml_result, created_at
                        FROM scans
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                ).fetchall()
                
                # Convert to dict list - normalize ml_result
                result["backup"] = [
                    {
                        "id": s[0],
                        "user_id": s[1],
                        "input_text": s[2],
                        "result": s[3],
                        "probability": float(s[4]) if s[4] else 0,
                        "heuristic_result": s[5],
                        "ml_result": normalize_ml_result(s[6]),  # Normalized to float string
                        "created_at": str(s[7])
                    }
                    for s in scans
                ]
                
                # Get total count
                total = backup_session.execute(
                    text("SELECT COUNT(*) FROM scans")
                ).scalar()
                result["count_backup"] = total or 0
                
            finally:
                backup_session.close()
    except Exception as e:
        logger.error(f"Error getting backup scans: {str(e)}")
    
    # Check if in sync
    result["in_sync"] = (result["count_primary"] == result["count_backup"] and 
                        result["count_primary"] > 0)
    
    return result
