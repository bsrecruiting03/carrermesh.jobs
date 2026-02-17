"""Register Tier-0 Workday companies directly in career_endpoints table"""
import os
import sys
from datetime import datetime

# Add project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

# Database config from environment
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "dbname": "job_board",
    "user": "postgres",
    "password": "password"
}

# Tier-0 Workday companies to register
TIER0_WORKDAY = [
    {
        "name": "PayPal",
        "canonical_url": "https://paypal.wd1.myworkdayjobs.com/jobs",
        "ats_provider": "workday",
        "ats_slug": "paypal",
        "priority": 1  # High priority
    },
    {
        "name": "Netflix",
        "canonical_url": "https://netflix.wd1.myworkdayjobs.com/en-US",
        "ats_provider": "workday",
        "ats_slug": "netflix",
        "priority": 1
    }
]

def register_endpoints():
    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    for company in TIER0_WORKDAY:
        print(f"\n--- Registering {company['name']} ---")
        
        # Check if already exists
        cursor.execute("""
            SELECT id FROM career_endpoints 
            WHERE canonical_url = %s OR ats_slug = %s
        """, (company['canonical_url'], company['ats_slug']))
        
        existing = cursor.fetchone()
        if existing:
            print(f"  Already exists (ID: {existing[0]})")
            continue
        
        # Insert new endpoint
        cursor.execute("""
            INSERT INTO career_endpoints 
            (canonical_url, ats_provider, ats_slug, is_active, created_at)
            VALUES (%s, %s, %s, true, %s)
            RETURNING id
        """, (
            company['canonical_url'],
            company['ats_provider'],
            company['ats_slug'],
            datetime.now()
        ))
        
        new_id = cursor.fetchone()[0]
        print(f"  ✅ Registered with ID: {new_id}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ Registration complete!")

if __name__ == "__main__":
    register_endpoints()
