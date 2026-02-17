
import sys
import os
import logging

# Add root dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import search_jobs

# Configure logging to see SQL queries if possible, or just print results
logging.basicConfig(level=logging.INFO)

def test_filters():
    print("\n--- TEST: VISA SPONSORSHIP ---")
    jobs, total = search_jobs(visa_sponsorship="true", limit=3)
    print(f"Found {total} jobs.")
    for j in jobs:
        print(f"- {j['title']} (Visa: {j.get('visa_sponsorship')})")

    print("\n--- TEST: SOFT SKILLS (Communication) ---")
    # Note: Soft skills are in 'job_search' denormalized column or 'job_enrichment'
    # Our code filters on job_enrichment e.soft_skills && ['Communication']
    jobs, total = search_jobs(soft_skills="Communication", limit=3)
    print(f"Found {total} jobs.")
    for j in jobs: 
        # API doesn't return soft_skills in list dict by default unless we requested full details?
        # The search_jobs returns columns from 'jobs' table mostly.
        # But we can verify by checking title/company against what we saw earlier.
        print(f"- {j['title']} @ {j['company']}")

    print("\n--- TEST: COMBINED (Visa + Communication) ---")
    jobs, total = search_jobs(visa_sponsorship="true", soft_skills="Communication", limit=3)
    print(f"Found {total} jobs.")
    for j in jobs:
        print(f"- {j['title']} (Visa: {j.get('visa_sponsorship')})")

if __name__ == "__main__":
    test_filters()
