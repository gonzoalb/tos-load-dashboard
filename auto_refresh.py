"""
TOS Dashboard Auto-Refresh Script
==================================
Finds the latest Hubble CSV download, pushes to GitHub.
Designed to run via Windows Task Scheduler daily.

Usage:
  1. Download CSV from Hubble (manually or via bookmark)
  2. Run this script - it finds the newest CSV and pushes it

Or set up Task Scheduler to run after your Hubble download.
"""

import os
import sys
import glob
import shutil
import subprocess
from datetime import datetime, timedelta
import json

# --- CONFIG ---
REPO_DIR = r"C:\Users\gonzoalb\Orcha\ct_1782594304_6294"
DATA_FILE = os.path.join(REPO_DIR, "data", "fmc_export.csv")
TIMESTAMP_FILE = os.path.join(REPO_DIR, "data", "last_refreshed.json")
DOWNLOADS_DIR = r"C:\Users\gonzoalb\Downloads"
GIT_PATH = r"C:\Users\gonzoalb\AppData\Local\Programs\Git\cmd\git.exe"
GITHUB_TOKEN = os.environ.get("TOS_GITHUB_TOKEN", "").strip()
if not GITHUB_TOKEN:
    # Fallback: read from .token file if env var not set
    token_file = os.path.join(REPO_DIR, ".token")
    if os.path.exists(token_file):
        GITHUB_TOKEN = open(token_file).read().strip()
REPO_URL = f"https://gonzoalb:{GITHUB_TOKEN}@github.com/gonzoalb/tos-load-dashboard.git"

# How recent must the CSV be (in hours) to be considered "fresh"
MAX_AGE_HOURS = 24


def find_latest_hubble_csv():
    """Find the most recent CSV in Downloads that looks like Hubble output."""
    csv_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*.csv"))
    if not csv_files:
        return None

    # Filter to files modified in the last MAX_AGE_HOURS
    cutoff = datetime.now().timestamp() - (MAX_AGE_HOURS * 3600)
    recent_csvs = [f for f in csv_files if os.path.getmtime(f) > cutoff]

    if not recent_csvs:
        return None

    # Sort by modification time, newest first
    recent_csvs.sort(key=os.path.getmtime, reverse=True)

    # Check if the newest one looks like our Hubble export (has expected columns)
    REQUIRED_COLS = ['lane', 'origin scheduled depart', 'carrier']
    REJECT_COLS = ['business types', 'pull time', 'copycount']  # FMC format - wrong file

    # Check both CSV and TSV files
    tsv_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*.tsv"))
    all_files = recent_csvs + [f for f in tsv_files if os.path.getmtime(f) > cutoff]
    all_files.sort(key=os.path.getmtime, reverse=True)

    for file_path in all_files:
        try:
            sep = '\t' if file_path.endswith('.tsv') else ','
            with open(file_path, 'r', encoding='utf-8') as f:
                header = f.readline().lower()
                # Reject FMC scheduling files
                if any(col in header for col in REJECT_COLS):
                    continue
                # Must have required Hubble columns (check with tab or comma sep)
                if all(col in header for col in REQUIRED_COLS):
                    return file_path
        except:
            continue

    return None


def update_timestamp():
    """Write current time to last_refreshed.json."""
    os.makedirs(os.path.dirname(TIMESTAMP_FILE), exist_ok=True)
    with open(TIMESTAMP_FILE, "w") as f:
        json.dump({"timestamp": datetime.now().strftime("%b %d, %Y at %I:%M %p")}, f)


def git_push():
    """Commit and push data to GitHub."""
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(GIT_PATH) + ";" + env.get("PATH", "")

    cmds = [
        [GIT_PATH, "remote", "set-url", "origin", REPO_URL],
        [GIT_PATH, "add", "data/fmc_export.csv", "data/last_refreshed.json"],
        [GIT_PATH, "commit", "-m", f"Auto-refresh data {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
        [GIT_PATH, "push"],
        [GIT_PATH, "remote", "set-url", "origin", "https://github.com/gonzoalb/tos-load-dashboard.git"],
    ]

    for cmd in cmds:
        result = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True, env=env)
        if result.returncode != 0 and "nothing to commit" not in result.stdout:
            if "push" in cmd and result.returncode != 0:
                print(f"ERROR: {' '.join(cmd)}")
                print(f"  stdout: {result.stdout}")
                print(f"  stderr: {result.stderr}")
                return False
    return True


def main():
    print("=" * 50)
    print("TOS Dashboard Auto-Refresh")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # Step 1: Find latest CSV
    csv_path = find_latest_hubble_csv()
    if not csv_path:
        print(f"\n❌ No fresh CSV found in Downloads (last {MAX_AGE_HOURS}h)")
        print("   Run your Hubble query and download results first.")
        sys.exit(1)

    file_time = datetime.fromtimestamp(os.path.getmtime(csv_path))
    file_size = os.path.getsize(csv_path) / 1024

    print(f"\n✅ Found: {os.path.basename(csv_path)}")
    print(f"   Modified: {file_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Size: {file_size:.1f} KB")

    # Step 2: Copy to repo (convert TSV to CSV if needed)
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if csv_path.endswith('.tsv'):
        import pandas as pd
        df = pd.read_csv(csv_path, sep='\t', low_memory=False)
        df.to_csv(DATA_FILE, index=False)
        print(f"\n✅ Converted TSV → CSV and saved to: {DATA_FILE}")
    else:
        shutil.copy2(csv_path, DATA_FILE)
        print(f"\n✅ Copied to: {DATA_FILE}")

    # Step 3: Update timestamp
    update_timestamp()
    print("✅ Timestamp updated")

    # Step 4: Push to GitHub
    print("\n⬆️  Pushing to GitHub...")
    if git_push():
        print("✅ Push successful! Dashboard will update in ~1 minute.")
    else:
        print("❌ Push failed. Check your GitHub token.")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("DONE! Dashboard is refreshed.")
    print("=" * 50)


if __name__ == "__main__":
    main()
