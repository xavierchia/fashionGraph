#!/usr/bin/env python3

import os
import subprocess
import sys

def main():
    phase = os.environ.get('PHASE', '1').lower()
    
    if phase == '1':
        print("Running Phase 1: Search posts", flush=True)
        # Run with unbuffered output and inherit stdout/stderr for real-time output
        subprocess.run([sys.executable, '-u', 'phase1_search.py'], 
                      stdout=sys.stdout, stderr=sys.stderr)
    elif phase == '2':
        print("Running Phase 2: Fetch full post details", flush=True)
        subprocess.run([sys.executable, '-u', 'phase2_details.py'],
                      stdout=sys.stdout, stderr=sys.stderr)
    else:
        print(f"Invalid PHASE value: {phase}")
        print("Valid options:")
        print("  PHASE=1  - Search and save post summaries")
        print("  PHASE=2  - Fetch full post details and comments")

if __name__ == "__main__":
    main()