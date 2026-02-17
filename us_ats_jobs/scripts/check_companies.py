"""
Quick script to check what companies are in the database
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db.database as database

# Get all active companies
companies = database.get_active_companies()

print(f"\n{'='*70}")
print(f"TOTAL ACTIVE COMPANIES IN DATABASE: {len(companies)}")
print(f"{'='*70}\n")

# Group by provider
by_provider = {}
for company in companies:
    provider = company['ats_provider']
    if provider not in by_provider:
        by_provider[provider] = []
    by_provider[provider].append(company['name'])

# Show counts
for provider, names in sorted(by_provider.items()):
    print(f"\n{provider.upper()}: {len(names)} companies")
    print("-" * 70)
    for name in sorted(names)[:10]:  # Show first 10
        print(f"  - {name}")
    if len(names) > 10:
        print(f"  ... and {len(names) - 10} more")
