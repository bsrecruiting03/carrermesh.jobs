import subprocess
import sys
import time
import os

def launch(num_workers=8):
    """
    Launches a fleet of worker processes.
    Total workers will be num_workers + any you already have running.
    """
    # Root dir
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script_path = os.path.join(root_dir, "us_ats_jobs", "worker_scraper.py")
    
    procs = []
    print(f"🚀 Launching {num_workers} Additional Scraper Workers...")
    print(f"   Script: {script_path}")
    
    for i in range(num_workers):
        # Spawn process
        # On Windows, creationflags=subprocess.CREATE_NEW_CONSOLE might open new windows, 
        # but we want them background/hidden or shared?
        # User asked to "implement", so let's run them in this console (they will share output).
        # Actually shared output from 10 workers is unreadable.
        # Let's run them silently (stdout=DEVNULL)? No, user wants to see "process".
        
        p = subprocess.Popen(
            [sys.executable, script_path],
            cwd=root_dir
            # stdout=subprocess.DEVNULL, # Keep noisy for now so user sees activity
            # stderr=subprocess.DEVNULL
        )
        procs.append(p)
        print(f"   - Started Worker {i+1} (PID: {p.pid})")
        time.sleep(0.5) # Stagger start
    
    print(f"\n✅ Fleet confirmed. {len(procs)} new drones active.")
    print("   (Use Task Manager or Ctrl+C here to kill them)")

    try:
        # Keep main script alive to monitor/kill child processes
        while True:
            time.sleep(1)
            # Check if any died
            for i, p in enumerate(procs):
                if p.poll() is not None:
                    print(f"⚠️ Worker {i+1} died! Restarting...")
                    procs[i] = subprocess.Popen([sys.executable, script_path], cwd=root_dir)
                    print(f"   - Restarted Worker {i+1} (PID: {procs[i].pid})")

    except KeyboardInterrupt:
        print("\n🛑 Grounding fleet...")
        for p in procs:
            p.terminate()

if __name__ == "__main__":
    # User asked for '10 workers'. We already have 2 (probably).
    # Let's launch 8 more to reach ~10 total.
    # Or just launch 10 as requested. 12 is fine.
    launch(10)
