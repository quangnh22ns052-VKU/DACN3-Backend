#!/usr/bin/env python3
"""View actual data from scans table in both databases"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

load_dotenv()

print("\n" + "="*80)
print("📊 SCANS DATA FROM BOTH DATABASES")
print("="*80)

# Neon (Primary)
print("\n🟢 NEON (Primary Database)")
print("-" * 80)

try:
    neon_engine = create_engine(os.getenv('DATABASE_URL'))
    
    with neon_engine.connect() as conn:
        # Get all scans
        query = """
        SELECT 
            id,
            user_id,
            input_text,
            result,
            probability,
            heuristic_result,
            ml_result,
            created_at
        FROM scans
        ORDER BY created_at DESC
        """
        
        df_neon = pd.read_sql_query(query, conn)
        
        if len(df_neon) > 0:
            print(f"\n✅ Total rows in Neon: {len(df_neon)}\n")
            
            # Display all rows with formatting
            for idx, row in df_neon.iterrows():
                print(f"ID: {row['id']}")
                print(f"  Input: {row['input_text'][:60]}...")
                print(f"  Result: {row['result']} (Prob: {row['probability']:.2%})")
                print(f"  ML: {row['ml_result']} | Heuristic: {row['heuristic_result']}")
                print(f"  Created: {row['created_at']}")
                print()
        else:
            print("❌ No data in Neon")
            
except Exception as e:
    print(f"❌ Error connecting to Neon: {str(e)}")

# Supabase (Backup)
print("\n" + "="*80)
print("🔵 SUPABASE (Backup Database)")
print("-" * 80)

try:
    supabase_engine = create_engine(os.getenv('DATABASE_URL_BACKUP'))
    
    with supabase_engine.connect() as conn:
        query = """
        SELECT 
            id,
            user_id,
            input_text,
            result,
            probability,
            heuristic_result,
            ml_result,
            created_at
        FROM scans
        ORDER BY created_at DESC
        """
        
        df_supabase = pd.read_sql_query(query, conn)
        
        if len(df_supabase) > 0:
            print(f"\n✅ Total rows in Supabase: {len(df_supabase)}\n")
            
            # Display all rows with formatting
            for idx, row in df_supabase.iterrows():
                print(f"ID: {row['id']}")
                print(f"  Input: {row['input_text'][:60]}...")
                print(f"  Result: {row['result']} (Prob: {row['probability']:.2%})")
                print(f"  ML: {row['ml_result']} | Heuristic: {row['heuristic_result']}")
                print(f"  Created: {row['created_at']}")
                print()
        else:
            print("❌ No data in Supabase")
            
except Exception as e:
    print(f"❌ Error connecting to Supabase: {str(e)}")

# Comparison
print("\n" + "="*80)
print("📊 COMPARISON")
print("="*80)

try:
    neon_count = len(df_neon) if 'df_neon' in locals() else 0
    supabase_count = len(df_supabase) if 'df_supabase' in locals() else 0
    
    print(f"\nNeon rows:     {neon_count}")
    print(f"Supabase rows: {supabase_count}")
    
    if neon_count == supabase_count and neon_count > 0:
        print("\n✅ Both databases IN SYNC!")
    elif neon_count > 0 and supabase_count > 0:
        print(f"\n⚠️  Difference: {abs(neon_count - supabase_count)} rows")
    else:
        print("\n❌ Data mismatch or empty")
        
except Exception as e:
    print(f"Error: {str(e)}")

print("\n" + "="*80 + "\n")
