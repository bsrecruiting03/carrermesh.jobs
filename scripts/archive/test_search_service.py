import os
import sys

# Add parent directory to path to import api modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from api.services.search_service import search_service
    print("Search service imported")
    
    hits, total = search_service.search_jobs(limit=1)
    print(f"Success: Found {total} jobs")
    print(f"First hit: {hits[0] if hits else 'None'}")
except Exception as e:
    import traceback
    traceback.print_exc()
