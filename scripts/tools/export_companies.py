import os
import sys
import psycopg2
import json
from datetime import datetime

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def export_to_json():
    print("📦 Exporting Companies and Endpoints to JSON...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # Get Companies
        cur.execute("SELECT name, ats_url, ats_provider FROM companies WHERE active = TRUE")
        rows = cur.fetchall()
        
        companies_data = []
        for name, url, provider in rows:
            companies_data.append({
                "name": name,
                "url": url,
                "provider": provider
            })
            
        # Get Endpoints
        cur.execute("""
            SELECT canonical_url, ats_provider, ats_slug, verification_status 
            FROM career_endpoints 
            WHERE active = TRUE
        """)
        rec_endpoints = cur.fetchall()
        
        endpoints_data = []
        for url, provider, slug, status in rec_endpoints:
            endpoints_data.append({
                "url": url,
                "provider": provider,
                "slug": slug,
                "status": status
            })
            
        output = {
            "generated_at": datetime.now().isoformat(),
            "stats": {
                "companies": len(companies_data),
                "endpoints": len(endpoints_data)
            },
            "companies": companies_data,
            # "endpoints": endpoints_data # Optional, might be huge
        }
        
        outfile = "companies_snapshot.json"
        with open(outfile, "w") as f:
            json.dump(output, f, indent=2)
            
        print(f"✅ Exported {len(companies_data)} companies to {outfile}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    export_to_json()
