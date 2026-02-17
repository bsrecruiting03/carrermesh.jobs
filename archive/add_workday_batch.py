import sys
import os

# Add the project directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "us_ats_jobs")))

import db.database as database
from config import WORKDAY_COMPANIES

def add_workday_companies():
    print(f"Adding {len(WORKDAY_COMPANIES)} Workday companies to database...")
    added_count = 0
    skipped_count = 0

    for company in WORKDAY_COMPANIES:
        name = company["name"]
        slug = company["slug"]
        
        # Construct a standard workday URL (guessing wd5 as default)
        ats_url = f"https://{slug}.wd5.myworkdayjobs.com/en-US/Careers"
        
        # add_company returns True if added, False if duplicate
        # We use the slug as the name for the fetcher logic in main.py
        success = database.add_company(
            name=slug, 
            ats_url=ats_url,
            ats_provider="workday"
        )
        
        if success:
            added_count += 1
            print(f"  + Added {name} (slug: {slug})")
        else:
            skipped_count += 1

    print(f"\n✅ Finished!")
    print(f"  - Added: {added_count}")
    print(f"  - Skipped: {skipped_count}")

if __name__ == "__main__":
    add_workday_companies()
