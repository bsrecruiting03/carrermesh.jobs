
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add root to python path to import database module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from us_ats_jobs.db import database

def migrate():
    print("🚀 Starting Schema Migration: Adding Hybrid Enrichment Columns...")
    
    
    # database.get_connection() returns a context manager in some implementations, 
    # but we need the raw connection object for set_isolation_level.
    # Let's try to get it properly.
    try:
        conn = database.get_connection()
        if hasattr(conn, '__enter__'):
             # If it's a context manager (pool), enter it
             conn = conn.__enter__()
    except Exception:
        # Fallback if get_connection logic is different
        conn = psycopg2.connect(database.DATABASE_URL)

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    try:
        # 1. Create ENUM type for enrichment_tier if not exists
        print("   - Checking enum 'enrichment_tier_enum'...")
        try:
            cur.execute("CREATE TYPE enrichment_tier_enum AS ENUM ('basic', 'standard', 'premium');")
            print("     ✅ Created ENUM 'enrichment_tier_enum'")
        except psycopg2.errors.DuplicateObject:
            print("     ℹ️  ENUM 'enrichment_tier_enum' already exists")
            
        # 2. Add 'enrichment_tier' column
        print("   - Adding column 'enrichment_tier'...")
        try:
            cur.execute("ALTER TABLE job_enrichment ADD COLUMN enrichment_tier enrichment_tier_enum DEFAULT 'basic';")
            print("     ✅ Added column 'enrichment_tier'")
        except psycopg2.errors.DuplicateColumn:
            print("     ℹ️  Column 'enrichment_tier' already exists")

        # 3. Add 'enrichment_source' column
        print("   - Adding column 'enrichment_source'...")
        try:
            cur.execute("ALTER TABLE job_enrichment ADD COLUMN enrichment_source TEXT DEFAULT 'local';")
            print("     ✅ Added column 'enrichment_source'")
        except psycopg2.errors.DuplicateColumn:
            print("     ℹ️  Column 'enrichment_source' already exists")

        print("\n✅ Migration Completed Successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration Failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
