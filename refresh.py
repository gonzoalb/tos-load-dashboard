#!/usr/bin/env python3
"""
TOS Dashboard - Automated Data Refresh
Queries Redshift for TransfersOutsideServices loads and pushes to GitHub.
Runs hourly via cron.
"""

import redshift_connector
import pandas as pd
import subprocess
import os
from datetime import datetime

# --- CONFIGURATION ---
REDSHIFT_HOST = "ats-linehaul-dw.cwfqj3baiwdp.us-east-1.redshift.amazonaws.com"
REDSHIFT_PORT = 8192
REDSHIFT_DB = "atslinehauldb"

REPO_DIR = os.path.expanduser("~/tos-automation/repo")
CSV_PATH = os.path.join(REPO_DIR, "data", "fmc_export.csv")
LOG_FILE = os.path.expanduser("~/tos-automation/refresh.log")

QUERY = """
SELECT
    vrid,
    scac AS carrier,
    subcarrier,
    lane,
    account_id,
    origin_scheduled_depart,
    dest_scheduled_arrival,
    first_dock_arrival,
    first_dock_departure,
    last_dock_arrival,
    trailer_id,
    canceled_load,
    trailer_ready_time
FROM oss.v_load_summary
WHERE account_id = 'TransfersOutsideServices'
  AND dest_country = 'US'
  AND trailer_ready_time >= DATEADD(day, -14, GETDATE())
ORDER BY trailer_ready_time DESC
"""


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_redshift_connection():
    """Connect to Redshift using IAM auth (Midway-backed)."""
    import boto3
    session = boto3.Session(region_name='us-east-1')
    client = session.client('redshift')

    creds = client.get_cluster_credentials(
        DbUser='gonzoalb',
        DbName=REDSHIFT_DB,
        ClusterIdentifier='ats-linehaul-dw',
        AutoCreate=False,
    )

    conn = redshift_connector.connect(
        host=REDSHIFT_HOST,
        port=REDSHIFT_PORT,
        database=REDSHIFT_DB,
        user=creds['DbUser'],
        password=creds['DbPassword'],
    )
    return conn


def run_query():
    """Execute query and return DataFrame."""
    log("Connecting to Redshift...")
    conn = get_redshift_connection()

    log("Running query (14-day rolling window)...")
    df = pd.read_sql(QUERY, conn)
    conn.close()

    log(f"Query returned {len(df)} rows")
    return df


def transform_data(df):
    """Transform column names to match dashboard expectations."""
    col_map = {
        'vrid': 'Load #',
        'carrier': 'Carrier',
        'subcarrier': 'Subcarrier',
        'lane': 'Lane',
        'account_id': 'Shipper Accounts',
        'first_dock_arrival': 'First Dock Arrival',
        'first_dock_departure': 'First Dock Departure',
        'last_dock_arrival': 'Last Dock Arrival',
        'dest_scheduled_arrival': 'Scheduled Truck Arrival - 2 date',
        'origin_scheduled_depart': 'Scheduled Truck Arrival - 1 date',
        'trailer_id': 'Trailer Id',
        'canceled_load': 'Canceled Load',
        'trailer_ready_time': 'Trailer Ready Time',
    }
    df = df.rename(columns=col_map)
    return df


def push_to_github():
    """Commit and push updated CSV to GitHub."""
    os.chdir(REPO_DIR)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    subprocess.run(["git", "add", "data/fmc_export.csv"], capture_output=True, text=True)

    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)

    if not status.stdout.strip():
        log("No data changes detected - skipping push")
        return False

    subprocess.run(
        ["git", "commit", "-m", f"Auto-refresh: {timestamp}"],
        capture_output=True, text=True
    )

    result = subprocess.run(
        ["git", "push", "origin", "main"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        log("Successfully pushed to GitHub")
        return True
    else:
        log(f"Git push failed: {result.stderr}")
        return False


def main():
    log("=" * 50)
    log("TOS Dashboard Refresh - Starting")

    try:
        df = run_query()

        if df.empty:
            log("WARNING: Query returned no data!")
            return

        df = transform_data(df)

        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        df.to_csv(CSV_PATH, index=False)
        log(f"Saved {len(df)} rows to {CSV_PATH}")

        push_to_github()

    except Exception as e:
        log(f"ERROR: {str(e)}")
        raise

    log("TOS Dashboard Refresh - Complete")
    log("=" * 50)


if __name__ == "__main__":
    main()
