import sqlite3
import os
from pathlib import Path

DB_PATH = Path("us_ats_jobs/db/jobs.db")

def check_db():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check counts by provider
    print("\n--- Company Counts by Provider ---")
    cursor.execute("SELECT ats_provider, count(*) FROM companies WHERE active=1 GROUP BY ats_provider")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
        
    # Check open circuits
    print("\n--- Circuit Breaker Status ---")
    cursor.execute("SELECT count(*) FROM companies WHERE circuit_open_until IS NOT NULL AND circuit_open_until > datetime('now')")
    open_count = cursor.fetchone()[0]
    print(f"  Open Circuits: {open_count}")
    
    # Samples of open circuits
    if open_count > 0:
        print("\n  Sample Open Circuits:")
        cursor.execute("SELECT name, ats_provider, circuit_open_until FROM companies WHERE circuit_open_until IS NOT NULL AND circuit_open_until > datetime('now') LIMIT 5")
        for row in cursor.fetchall():
            print(f"    - {row[0]} ({row[1]}) until {row[2]}")

    # Check for specific workable companies
    print("\n--- Workable Companies in DB ---")
    cursor.execute("SELECT name, active FROM companies WHERE ats_provider = 'workable'")
    workable = cursor.fetchall()
    if not workable:
        print("  None found.")
    else:
        for row in workable:
            print(f"  - {row[0]} (Active: {row[1]})")

    conn.close()

if __name__ == "__main__":
    check_db()
