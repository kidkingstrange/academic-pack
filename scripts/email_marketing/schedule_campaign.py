#!/usr/bin/env python3
"""
Automated Weekly Campaign Scheduler
Enforces a 7-day campaign frequency cap and runs the campaign sender.
"""
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta

LAST_RUN_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".last_campaign_run"))
CAMPAIGN_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "send_campaign.py"))

def is_eligible_to_run(min_days=7):
    if not os.path.exists(LAST_RUN_FILE):
        return True
    try:
        with open(LAST_RUN_FILE, "r", encoding="utf-8") as f:
            last_run_str = f.read().strip()
        last_run_dt = datetime.fromisoformat(last_run_str)
        if datetime.now() - last_run_dt < timedelta(days=min_days):
            days_left = min_days - (datetime.now() - last_run_dt).days
            print(f"[Scheduler] Frequency cap active. Last run: {last_run_str}. Next allowed run in ~{days_left} day(s).")
            return False
    except Exception:
        return True
    return True

def record_run():
    with open(LAST_RUN_FILE, "w", encoding="utf-8") as f:
        f.write(datetime.now().isoformat())

def run_scheduled_job(force=False):
    if not force and not is_eligible_to_run():
        return

    print("[Scheduler] Campaign is eligible to run. Launching send_campaign.py...")
    
    cmd = [sys.executable, CAMPAIGN_SCRIPT]
    res = subprocess.run(cmd)
    if res.returncode == 0:
        record_run()
        print("[Scheduler] Campaign run logged successfully.")
    else:
        print(f"[Scheduler] Campaign run finished with exit code {res.returncode}.")

if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    run_scheduled_job(force=force_flag)
