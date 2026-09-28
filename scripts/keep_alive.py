#!/usr/bin/env python3
"""
Always-On Keep-Alive Monitor & Cron Job
Pings target websites on a regular cadence (every 10 minutes by default)
to prevent free hosting services (Render, Railway, Fly.io, etc.) from spinning down into sleep mode.

Usage:
  python scripts/keep_alive.py                   # Run one-off check right now
  python scripts/keep_alive.py --daemon          # Run continuously in background (default every 10 mins)
  python scripts/keep_alive.py --daemon --interval 300  # Run every 5 minutes
  python scripts/keep_alive.py --install-task    # Register as Windows Scheduled Task (runs every 10 mins)
  python scripts/keep_alive.py --uninstall-task  # Remove Windows Scheduled Task
"""

import sys
import os
import time
import argparse
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Default target websites to keep awake
DEFAULT_TARGET_URLS = [
    "https://academic-pack.onrender.com/api/health",
    "https://academic-pack.onrender.com/",
    "https://edgepack.thescaleconference.com/api/health",
    "https://edgepack.thescaleconference.com/",
    "https://thescaleconference.com/",
]

LOG_DIR = Path(__file__).resolve().parent.parent / "backend" / "data"
LOG_FILE = LOG_DIR / "keep_alive.log"


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def log_message(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        safe_line = line.encode("ascii", errors="replace").decode("ascii")
        print(safe_line)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def ping_url(url: str, timeout: int = 15) -> tuple[int, float, str]:
    """Pings a single URL and returns (status_code, duration_seconds, error_or_body)."""
    t0 = time.time()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KeepAliveCron/2.0 (Always-On Site Monitor; +https://academic-pack.onrender.com)",
            "Accept": "text/html,application/json,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            dur = time.time() - t0
            code = response.status
            return code, dur, "OK"
    except urllib.error.HTTPError as e:
        dur = time.time() - t0
        return e.code, dur, f"HTTPError: {e.reason}"
    except urllib.error.URLError as e:
        dur = time.time() - t0
        return 0, dur, f"URLError: {e.reason}"
    except Exception as e:
        dur = time.time() - t0
        return 0, dur, f"Error: {str(e)}"


def run_ping_cycle(urls: list[str]) -> dict:
    """Executes a full ping cycle across all target URLs."""
    log_message(f"--- Starting Keep-Alive Ping Cycle ({len(urls)} targets) ---")
    results = {}
    success_count = 0

    for url in urls:
        code, dur, note = ping_url(url)
        status_tag = "[ONLINE]" if (code in [200, 301, 302]) else "[FAILED]"
        results[url] = {"status": code, "duration": dur, "note": note}
        if code in [200, 301, 302]:
            success_count += 1
            log_message(f"{status_tag} [{code}] {url} ({dur:.2f}s)")
        else:
            log_message(f"{status_tag} [{code}] {url} ({dur:.2f}s) - {note}")

    summary = f"Cycle finished: {success_count}/{len(urls)} sites healthy."
    log_message(summary)
    return results


def run_daemon(urls: list[str], interval_seconds: int = 600):
    """Runs ping cycles indefinitely at the given interval."""
    log_message(f"Starting Keep-Alive Daemon (Interval: {interval_seconds}s / {interval_seconds // 60}m)...")
    try:
        while True:
            run_ping_cycle(urls)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        log_message("Keep-Alive Daemon stopped by user.")


def install_windows_task():
    """Installs a Windows Scheduled Task using schtasks to run this script every 10 minutes."""
    python_exe = sys.executable
    script_path = Path(__file__).resolve()
    task_name = "KeepAliveWebsites"

    # Command that executes the one-off check
    cmd = f'"{python_exe}" "{script_path}"'

    log_message(f"Installing Windows Scheduled Task '{task_name}' to run every 10 minutes...")
    schtasks_cmd = [
        "schtasks",
        "/create",
        "/tn", task_name,
        "/tr", cmd,
        "/sc", "MINUTE",
        "/mo", "10",
        "/f"
    ]
    try:
        res = subprocess.run(schtasks_cmd, capture_output=True, text=True, check=True)
        log_message(f"✅ Successfully installed Windows Scheduled Task '{task_name}'.")
        print(res.stdout)
    except subprocess.CalledProcessError as e:
        log_message(f"❌ Failed to install task: {e.stderr}")


def uninstall_windows_task():
    """Removes the Windows Scheduled Task."""
    task_name = "KeepAliveWebsites"
    log_message(f"Removing Windows Scheduled Task '{task_name}'...")
    schtasks_cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
    try:
        res = subprocess.run(schtasks_cmd, capture_output=True, text=True, check=True)
        log_message(f"✅ Successfully removed task '{task_name}'.")
        print(res.stdout)
    except subprocess.CalledProcessError as e:
        log_message(f"Task remove status: {e.stderr.strip() or e.stdout.strip()}")


def main():
    parser = argparse.ArgumentParser(description="Always-On Website Keep-Alive Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background")
    parser.add_argument("--interval", type=int, default=600, help="Interval between pings in seconds (default: 600 = 10m)")
    parser.add_argument("--install-task", action="store_true", help="Install Windows Scheduled Task to run every 10 mins")
    parser.add_argument("--uninstall-task", action="store_true", help="Uninstall Windows Scheduled Task")
    parser.add_argument("--urls", nargs="+", default=DEFAULT_TARGET_URLS, help="List of URLs to ping")
    args = parser.parse_args()

    if args.install_task:
        install_windows_task()
        return

    if args.uninstall_task:
        uninstall_windows_task()
        return

    if args.daemon:
        run_daemon(args.urls, args.interval)
    else:
        run_ping_cycle(args.urls)


if __name__ == "__main__":
    main()
