
import sys
import os
import threading
import time

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

import api.database as db
from api.database import init_db_pool, get_db

def worker(id):
    """Simulate a worker using the DB."""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT pg_backend_pid()")
            pid = cur.fetchone()[0]
            print(f"Worker {id}: Got connection (PID: {pid})")
            time.sleep(0.5) # Simulate work
    except Exception as e:
        print(f"Worker {id}: Error {e}")

if __name__ == "__main__":
    print("Initializing Pool...")
    # init_db_pool() # Should happen automatically in get_db
    
    threads = []
    print("Starting 5 parallel workers...")
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    print("Pool verification complete.")
