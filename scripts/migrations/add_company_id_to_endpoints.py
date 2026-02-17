"""
Database migration: Add company_id to career_endpoints.
This creates the link for the Resolver Agent to manage.
"""

import os
import sys
import psycopg2

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def run_migration():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            print("🔧 Adding company_id to career_endpoints...")
            
            cur.execute("""
                ALTER TABLE career_endpoints 
                ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_endpoints_company_id 
                ON career_endpoints(company_id);
            """)
            
            print("   ✅ Column added.")
            
            print("🔄 Backfilling company_id from existing companies...")
            
            # 1. Exact Match on ATS URL (Safe)
            cur.execute("""
                UPDATE career_endpoints ce
                SET company_id = c.id
                FROM companies c
                WHERE ce.canonical_url = c.ats_url
                AND ce.company_id IS NULL;
            """)
            updated_url = cur.rowcount
            print(f"   Matched by URL: {updated_url}")
            
            # 2. Match on Domain (if applicable, but endpoints don't store domain yet? URL parsing needed)
            # Not safe yet.
            
            # 3. Match on Name/Slug?
            # c.name vs ce.ats_slug.
            # Example: ce.ats_slug='stripe', c.name='stripe'.
            cur.execute("""
                UPDATE career_endpoints ce
                SET company_id = c.id
                FROM companies c
                WHERE LOWER(ce.ats_slug) = LOWER(c.name)
                AND ce.company_id IS NULL;
            """)
            updated_slug = cur.rowcount
            print(f"   Matched by Slug=Name: {updated_slug}")

            # Verify stats
            cur.execute("SELECT COUNT(*) FROM career_endpoints WHERE company_id IS NOT NULL")
            linked = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM career_endpoints WHERE company_id IS NULL")
            orphaned = cur.fetchone()[0]
            
            print(f"\n📊 Linkage Status:")
            print(f"   Linked: {linked}")
            print(f"   Orphaned: {orphaned}")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
