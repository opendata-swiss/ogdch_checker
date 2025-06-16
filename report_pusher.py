"""
Script to push Shacl checker report to Metadata-quality-dashboard
"""
import os
import shutil
import subprocess
from datetime import datetime

# Detect latest shacl log folder
base_log_dir = "/home/liip/ogdch_checker/logs"
results_dir = "/home/liip/metadata-quality-dashboard/shacl-checker-results"

log_folders = [f for f in os.listdir(base_log_dir) if f.endswith("-shacl")]
log_folders.sort(reverse=True)
latest_log = log_folders[0]

source_csv_dir = os.path.join(base_log_dir, latest_log, "csv")
dest_csv_dir = os.path.join(results_dir, latest_log, "csv")

os.makedirs(dest_csv_dir, exist_ok=True)

# Copy CSV files
for filename in os.listdir(source_csv_dir):
    src = os.path.join(source_csv_dir, filename)
    dst = os.path.join(dest_csv_dir, filename)
    if os.path.isfile(src):
        shutil.copy2(src, dst)

# Git add/commit/push
os.chdir("/home/liip/metadata-quality-dashboard")
subprocess.run(["git", "add", f"shacl-checker-results/{latest_log}"], check=True)
subprocess.run(["git", "commit", "-m", f"Add SHACL report {latest_log}"], check=True)
subprocess.run(["git", "push"], check=True)
