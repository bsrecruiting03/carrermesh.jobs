#!/usr/bin/env python3
"""
Multi-Worker Launcher
Spawns multiple instances of the worker_enrichment.py script
to process the job queue in parallel.
"""

import subprocess
import sys
import os
import time
import signal

# Configuration
NUM_WORKERS = 5
WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), "worker_enrichment.py")
PYTHON_EXE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "venv", "Scripts", "python.exe")

processes = []

def signal_handler(sig, frame):
    print(f"\nTerminating all {len(processes)} workers...")
    for p in processes:
        p.terminate()
    sys.exit(0)

def main():
    print(f"🚀 Launching {NUM_WORKERS} workers...")
    print(f"Script: {WORKER_SCRIPT}")
    
    # Register Ctrl+C handler
    signal.signal(signal.SIGINT, signal_handler)

    for i in range(NUM_WORKERS):
        print(f"  Starting Worker #{i+1}...")
        p = subprocess.Popen([PYTHON_EXE, WORKER_SCRIPT], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.STDOUT)
        processes.append(p)
        time.sleep(0.5)  # Stagger starts slightly

    print(f"\n✅ All {NUM_WORKERS} workers are running in the background.")
    print(f"Check the monitoring dashboard to see the increased processing rate!")
    print(f"Press Ctrl+C to stop all workers.")

    # Keep the main process alive
    while True:
        # Check if processes are still running
        for i, p in enumerate(processes):
            if p.poll() is not None:
                print(f"⚠️  Worker #{i+1} died. Restarting...")
                new_p = subprocess.Popen([PYTHON_EXE, WORKER_SCRIPT], 
                                         stdout=subprocess.DEVNULL, 
                                         stderr=subprocess.STDOUT)
                processes[i] = new_p
        
        time.sleep(10)

if __name__ == "__main__":
    main()
