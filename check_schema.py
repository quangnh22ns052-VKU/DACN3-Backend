#!/usr/bin/env python3
"""Check schema of both databases"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

load_dotenv()

# Check Neon schema
print("=" * 70)
print("📋 NEON (Primary) - Scans Table Schema")
print("=" * 70)

db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url)
inspector = inspect(engine)

try:
    columns = inspector.get_columns('scans')
    print(f"\nColumns in 'scans' table ({len(columns)} total):\n")
    for col in columns:
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"  • {col['name']:25} {str(col['type']):20} {nullable}")
except Exception as e:
    print(f"❌ Error: {e}")

# Check Supabase schema
print("\n" + "=" * 70)
print("📋 SUPABASE (Backup) - Scans Table Schema")
print("=" * 70)

db_url_backup = os.getenv('DATABASE_URL_BACKUP')
if db_url_backup:
    engine_backup = create_engine(db_url_backup)
    inspector_backup = inspect(engine_backup)
    
    try:
        columns_backup = inspector_backup.get_columns('scans')
        print(f"\nColumns in 'scans' table ({len(columns_backup)} total):\n")
        for col in columns_backup:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"  • {col['name']:25} {str(col['type']):20} {nullable}")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ DATABASE_URL_BACKUP not set in .env")

# Compare
print("\n" + "=" * 70)
print("📊 COMPARISON")
print("=" * 70)

try:
    neon_cols = {c['name'] for c in inspector.get_columns('scans')}
    supabase_cols = {c['name'] for c in inspector_backup.get_columns('scans')} if db_url_backup else set()
    
    only_neon = neon_cols - supabase_cols
    only_supabase = supabase_cols - neon_cols
    
    if only_neon:
        print(f"\n❌ Only in Neon (will cause migration error):")
        for col in only_neon:
            print(f"  • {col}")
    
    if only_supabase:
        print(f"\n⚠️  Only in Supabase:")
        for col in only_supabase:
            print(f"  • {col}")
    
    if not only_neon and not only_supabase:
        print("\n✅ Schemas match perfectly!")
        
except Exception as e:
    print(f"❌ Error: {e}")
