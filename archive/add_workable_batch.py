import sys
import os

# Add the project directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "us_ats_jobs")))

import db.database as database

workable_companies = [
    "ryanair", "huggingface", "employment-hero", "virgin", "bandlabtechnologies",
    "jobgether", "rentokil-initial", "winnow", "zinc-work", "toloka-ai",
    "tyme", "kaleyra", "junglee-games", "shippabo", "devsquad", "wp-media",
    "mitti-labs", "dof", "alpheya", "navro", "credence", "intellecthq",
    "flatgigs", "venturefriendsvc", "plum-inc", "gocompare", "evisit",
    "threatconnect", "moviepass", "qiddiya", "joey", "valsoft", "advisacare",
    "supportyourapp", "1kosmos", "leonardo", "activatetalent"
]

def add_workable_companies():
    print(f"Adding {len(workable_companies)} Workable companies to database...")
    added_count = 0
    skipped_count = 0

    for name in workable_companies:
        # Construct a standard workable URL
        ats_url = f"https://apply.workable.com/{name}/"
        
        # add_company returns True if added, False if duplicate
        success = database.add_company(
            name=name,
            ats_url=ats_url,
            ats_provider="workable"
        )
        
        if success:
            added_count += 1
        else:
            skipped_count += 1

    print(f"\n✅ Finished!")
    print(f"  - Added: {added_count}")
    print(f"  - Skipped (already exists): {skipped_count}")

if __name__ == "__main__":
    add_workable_companies()
