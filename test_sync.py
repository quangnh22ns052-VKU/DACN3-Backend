"""
🔄 Database Sync Debug Script
Test if data from Neon is syncing to Supabase
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from backend.models.database import SessionLocal, SessionLocalBackup
from backend.utils.database_sync import sync_databases, get_sync_status
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("\n" + "="*70)
print("🔄 PHISHGUARD DATABASE SYNC DEBUG")
print("="*70)

# ============================================================
# 1. Check Configuration
# ============================================================
from backend.config import Config

print("\n1️⃣ Configuration Check:")
print(f"   DB_SYNC_ENABLED: {Config.DB_SYNC_ENABLED}")
print(f"   DB_SYNC_INTERVAL: {Config.DB_SYNC_INTERVAL}s")
print(f"   Neon (Primary): {'✅ Set' if Config.DATABASE_URL else '❌ Not set'}")
print(f"   Supabase (Backup): {'✅ Set' if Config.DATABASE_URL_BACKUP else '❌ Not set'}")

# ============================================================
# 2. Test Connection to Both Databases
# ============================================================
print("\n2️⃣ Database Connections:")

try:
    primary = SessionLocal()
    result = primary.execute(text("SELECT 1"))
    print(f"   ✅ Neon (Primary) - Connection OK")
    primary.close()
except Exception as e:
    print(f"   ❌ Neon (Primary) - Error: {str(e)}")

try:
    backup = SessionLocalBackup()
    result = backup.execute(text("SELECT 1"))
    print(f"   ✅ Supabase (Backup) - Connection OK")
    backup.close()
except Exception as e:
    print(f"   ❌ Supabase (Backup) - Error: {str(e)}")

# ============================================================
# 3. Count Records in Both Databases
# ============================================================
print("\n3️⃣ Data Count (Scans Table):")

try:
    primary = SessionLocal()
    neon_count = primary.execute(text("SELECT COUNT(*) as cnt FROM scans")).scalar()
    print(f"   📊 Neon: {neon_count} scans")
    primary.close()
except Exception as e:
    print(f"   ❌ Neon Error: {str(e)}")
    neon_count = 0

try:
    backup = SessionLocalBackup()
    supabase_count = backup.execute(text("SELECT COUNT(*) as cnt FROM scans")).scalar()
    print(f"   📊 Supabase: {supabase_count} scans")
    backup.close()
except Exception as e:
    print(f"   ❌ Supabase Error: {str(e)}")
    supabase_count = 0

if neon_count > supabase_count:
    print(f"\n   ⚠️  SYNC NEEDED: Neon has {neon_count - supabase_count} more records than Supabase")
elif neon_count == supabase_count:
    print(f"\n   ✅ Both databases have {neon_count} records - In sync!")
else:
    print(f"\n   ⚠️  Supabase has {supabase_count - neon_count} more records than Neon (unusual)")

# ============================================================
# 4. Run Manual Sync
# ============================================================
print("\n4️⃣ Running Manual Sync:")
print("   Starting sync_databases()...")

success = sync_databases()

if success:
    print("   ✅ Sync completed successfully")
else:
    print("   ❌ Sync failed or no changes needed")

# ============================================================
# 5. Count Again After Sync
# ============================================================
print("\n5️⃣ Data Count After Sync:")

try:
    primary = SessionLocal()
    neon_count_after = primary.execute(text("SELECT COUNT(*) as cnt FROM scans")).scalar()
    print(f"   📊 Neon: {neon_count_after} scans")
    primary.close()
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

try:
    backup = SessionLocalBackup()
    supabase_count_after = backup.execute(text("SELECT COUNT(*) as cnt FROM scans")).scalar()
    print(f"   📊 Supabase: {supabase_count_after} scans")
    backup.close()
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# ============================================================
# 6. Sync Status
# ============================================================
print("\n6️⃣ Sync Status:")
status = get_sync_status()
for key, value in status.items():
    print(f"   • {key}: {value}")

print("\n" + "="*70)
if supabase_count_after >= neon_count_after:
    print("✅ SYNC IS WORKING - Supabase is up to date!")
else:
    print("❌ SYNC NOT WORKING - Supabase still behind Neon")
print("="*70 + "\n")
