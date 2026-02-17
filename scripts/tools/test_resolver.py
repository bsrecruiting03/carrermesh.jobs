import os
import sys
import psycopg2
import time

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def test_resolver():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    test_url = "https://jobs.lever.co/brandnewstartup"
    test_slug = "brandnewstartup"
    provider = "lever"
    
    print(f"🧪 Injecting orphan endpoint: {test_url}")
    
    try:
        # 1. Insert Orphan
        cur.execute("""
            INSERT INTO career_endpoints (canonical_url, ats_provider, ats_slug, active, company_id)
            VALUES (%s, %s, %s, TRUE, NULL)
            ON CONFLICT (canonical_url) DO UPDATE SET company_id = NULL
            RETURNING id;
        """, (test_url, provider, test_slug))
        endpoint_id = cur.fetchone()[0]
        print("   Orphan ID: {endpoint_id}")
        
        # 1b. Force Trigger (Since agent loops every 5m)
        print("⚡ Triggering Resolver Logic Manually...")
        from agents.resolver.main import ResolverAgent
        resolver = ResolverAgent()
        resolver.resolve_orphans()
        
        # 2. Wait for Resolver
        print("⏳ Checking status...")
        for i in range(10):
            time.sleep(3)
            cur.execute("SELECT company_id FROM career_endpoints WHERE id = %s", (endpoint_id,))
            company_id = cur.fetchone()[0]
            
            if company_id:
                print(f"   ✅ RESOLVED! Linked to Company ID: {company_id}")
                
                # Check Company Name
                cur.execute("SELECT name FROM companies WHERE id = %s", (company_id,))
                name = cur.fetchone()[0]
                print(f"   🏢 Company Name Created: '{name}'")
                
                # Clean up
                cur.execute("DELETE FROM career_endpoints WHERE id = %s", (endpoint_id,))
                cur.execute("DELETE FROM companies WHERE id = %s", (company_id,))
                print("   🧹 Cleaned up test data.")
                return
            
            print("   ... still waiting ...")
            
        print("❌ Resolver failed to link endpoint in time.")
        
    except Exception as e:
        print(f"❌ Test Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_resolver()
