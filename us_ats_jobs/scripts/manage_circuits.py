"""
Admin script to manage circuit breaker states for companies.
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db.database as database

def show_open_circuits():
    """Display all companies with open circuits."""
    circuits = database.get_companies_with_open_circuits()
    
    if not circuits:
        print("✅ No companies with open circuits!")
        return
    
    print(f"\n{'='*80}")
    print(f"Companies with Open Circuits: {len(circuits)}")
    print(f"{'='*80}\n")
    
    for company in circuits:
        print(f"ID: {company['id']}")
        print(f"  Name: {company['name']}")
        print(f"  Provider: {company['ats_provider']}")
        print(f"  Consecutive Failures: {company['consecutive_failures']}")
        print(f"  Last Failure: {company['last_failure_at']}")
        print(f"  Circuit Open Until: {company['circuit_open_until']}")
        print()

def reset_circuit(company_id):
    """Manually reset a company's circuit."""
    with database.get_connection() as conn:
        conn.execute("""
            UPDATE companies 
            SET consecutive_failures = 0,
                circuit_open_until = NULL
            WHERE id = ?
        """, (company_id,))
    print(f"✅ Circuit reset for company ID {company_id}")

def show_failure_stats():
    """Show statistics on company failures."""
    with database.get_connection() as conn:
        # Companies by failure count
        cursor = conn.execute("""
            SELECT consecutive_failures, COUNT(*) as count
            FROM companies
            WHERE active = 1
            GROUP BY consecutive_failures
            ORDER BY consecutive_failures
        """)
        
        print(f"\n{'='*80}")
        print("Failure Statistics")
        print(f"{'='*80}\n")
        
        for row in cursor.fetchall():
            failures = row[0] or 0
            count = row[1]
            status = "🟢 Healthy" if failures == 0 else f"🟡 {failures} failures"
            if failures >= 3:
                status = f"🔴 Circuit Open ({failures} failures)"
            print(f"{status}: {count} companies")

def main():
    database.create_tables()
    
    print("\n" + "="*80)
    print("Circuit Breaker Admin Tool")
    print("="*80)
    
    while True:
        print("\nOptions:")
        print("1. Show companies with open circuits")
        print("2. Show failure statistics")
        print("3. Reset circuit for a company (by ID)")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            show_open_circuits()
        elif choice == "2":
            show_failure_stats()
        elif choice == "3":
            company_id = input("Enter company ID to reset: ").strip()
            try:
                reset_circuit(int(company_id))
            except ValueError:
                print("❌ Invalid company ID")
        elif choice == "4":
            print("\nGoodbye!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
