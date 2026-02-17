"""
Migration: Backfill career_endpoints from existing companies table.

This ensures we don't lose any existing coverage when switching to the new architecture.
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Force correct DB URL
DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"


def run_backfill():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            print("🔄 Starting Backfill from Companies...")
            
            # Select relevant data
            cur.execute("""
                SELECT id, name, ats_url, ats_provider, active 
                FROM companies 
                WHERE ats_url IS NOT NULL 
                AND ats_url != ''
            """)
            
            companies = cur.fetchall()
            print(f"   Found {len(companies)} companies with ATS URLs")
            
            added = 0
            skipped = 0
            
            for company in companies:
                c_id, name, url, provider, active = company
                
                # Cleanup URL
                canonical = url.strip()
                if not canonical.startswith("http"):
                    canonical = f"https://{canonical}"
                
                # Try to extract slug (heuristic)
                # e.g., boards.greenhouse.io/stripe -> stripe
                slug = None
                try:
                    path = urlparse(canonical).path.strip("/")
                    if path:
                        slug = path.split("/")[-1]
                except:
                    pass
                
                # Insert
                try:
                    cur.execute("""
                        INSERT INTO career_endpoints (
                            canonical_url, ats_provider, ats_slug, 
                            active, verification_status, confidence_score,
                            discovered_from
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (canonical_url) DO NOTHING
                    """, (
                        canonical, 
                        provider or 'unknown', 
                        slug, 
                        active, 
                        'verified', # Assume verified since it was in our companies DB
                        1.0, 
                        'migration_backfill'
                    ))
                    
                    if cur.rowcount > 0:
                        added += 1
                    else:
                        skipped += 1
                        
                except Exception as e:
                    print(f"   ❌ Error inserting {name}: {e}")
            
            print(f"\n✅ Backfill Complete!")
            print(f"   Added: {added}")
            print(f"   Skipped (Duplicate): {skipped}")
            
            # Also backfill from Workday Tenants if they exist
            print("\n🔄 Checking Workday Tenants...")
            try:
                cur.execute("""
                    SELECT tenant_domain, tenant_slug, status 
                    FROM workday_tenants
                """)
                workday_tenants = cur.fetchall()
                print(f"   Found {len(workday_tenants)} Workday tenants")
                
                wd_added = 0
                for wd in workday_tenants:
                    domain, slug, status = wd
                    
                    # Workday domains usually look like: https://wd5.myworkday.com/tenant/d/external.htm
                    # But we stored pure domain in registry? Let's assume tenant_domain is the URL or domain.
                    url = domain
                    if not url.startswith("http"):
                        url = f"https://{url}"
                        
                    try:
                        cur.execute("""
                            INSERT INTO career_endpoints (
                                canonical_url, ats_provider, ats_slug, 
                                active, verification_status, confidence_score,
                                discovered_from
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (canonical_url) DO NOTHING
                        """, (
                            url, 
                            'workday', 
                            slug, 
                            True, 
                            'pending_verification' if status == 'pending_validation' else 'verified',
                            0.9, 
                            'migration_workday_registry'
                        ))
                        if cur.rowcount > 0:
                            wd_added += 1
                    except:
                        pass
                
                print(f"   Added Workday Endpoints: {wd_added}")
                
            except psycopg2.Error:
                print("   ⚠️ Workday tenants table not ready or empty (Skipping)")
            
    finally:
        conn.close()

if __name__ == "__main__":
    run_backfill()
