
import sys
import os
import logging

# Setup logging to see errors
logging.basicConfig(level=logging.INFO)

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

import api.database as db

print("Attempting to search jobs...")

try:
    # Simulate the call made by the frontend
    jobs, total = db.search_jobs(limit=20, page=1)
    print(f"Success! Found {total} jobs.")
    print(f"First job: {jobs[0]['title'] if jobs else 'None'}")
except Exception as e:
    print("CAUGHT EXCEPTION:")
    import traceback
    traceback.print_exc()
