"""
Script to push Shacl checker report to Metadata-quality-dashboard
"""
import os
import shutil
import subprocess

# Detect latest shacl log folder
base_log_dir = "/home/liip/ogdch_checker/logs"
results_dir = "/home/liip/metadata-quality-dashboard/shacl-checker-results"

# Get only SHACL-related folders in logs/
shacl_dirs = [
    os.path.join(base_log_dir, d)
    for d in os.listdir(base_log_dir)
    if os.path.isdir(os.path.join(base_log_dir, d)) and "-shacl" in d
]

# Sort by modification time (latest last)
shacl_dirs.sort(key=os.path.getmtime)

# Pick the latest one
latest_shacl_dir = shacl_dirs[-1]
print(f"Latest SHACL folder: {latest_shacl_dir}")

# Extract just the folder name
folder_name = os.path.basename(latest_shacl_dir)

source_csv_dir = os.path.join(base_log_dir, folder_name, "csv")
dest_csv_dir = os.path.join(results_dir, folder_name, "csv")

# Ensure repo is up to date before copying
os.chdir("/home/liip/metadata-quality-dashboard")
subprocess.run(["git", "pull"], check=True)

# Copy CSV files
os.makedirs(dest_csv_dir, exist_ok=True)

for filename in os.listdir(source_csv_dir):
    src = os.path.join(source_csv_dir, filename)
    dst = os.path.join(dest_csv_dir, filename)
    if os.path.isfile(src):
        shutil.copy2(src, dst)

# Git add/commit/push
subprocess.run(["git", "add", f"shacl-checker-results/{folder_name}"], check=True)
subprocess.run(["git", "commit", "-m", f"Add SHACL report {folder_name}"], check=True)
subprocess.run(["git", "push"], check=True)
