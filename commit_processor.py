#!/usr/bin/env python3
"""
Simple script that processes the last git commit to raw files
and creates info files in /info directory
"""

import os
import json
import subprocess
import shutil
import uuid
from pathlib import Path


def run_cmd(cmd):
    """Run a command and return the result."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        print(result.stderr)
        return None
    return result


def process_last_commit():
    """Process the last commit that modified raw files."""
    print("Processing last commit to raw files...")

    # Get the last commit hash
    result = run_cmd(["git", "rev-parse", "HEAD"])
    if not result:
        print("Could not get current commit")
        return

    commit_hash = result.stdout.strip()

    # Get diff for raw files in this commit
    # Use --root flag to handle root commits (commits with no parent)
    result = run_cmd(
        [
            "git",
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "--root",
            commit_hash,
        ]
    )
    if not result or not result.stdout.strip():
        print("No file changes found in last commit")
        return

    # Filter for only raw/ files
    all_files = result.stdout.strip().split("\n")
    changed_files = [f for f in all_files if f.strip().startswith("raw/")]

    if not changed_files:
        print("No raw file changes found in last commit")
        return

    # Process each changed file
    for filename in changed_files:
        if filename.strip() and filename.startswith("raw/"):
            print(f"Processing {filename}")

            # Create info JSON file
            info_dir = Path("info")
            info_dir.mkdir(exist_ok=True)

            unique_id = str(uuid.uuid4())
            info_file = info_dir / f"{unique_id}.json"

            # Get diff for this specific file
            result = run_cmd(["git", "show", f"{commit_hash}:{filename}"])
            if result:
                original_content = result.stdout
                line_count = len(original_content.split("\n"))
            else:
                original_content = ""
                line_count = 1000

            # For simplicity, we'll just put the whole file info
            data = {
                "id": unique_id,
                "commit_id": commit_hash,
                "filename": filename,
                "start_line": 1,
                "end_line": line_count,
                "content": original_content,
            }

            with open(info_file, "w") as f:
                json.dump(data, f, indent=2)

            print(f"Created info file: {info_file}")


def main():
    """Main function."""
    print("Raw file commit processor")

    # Create necessary directories
    Path("info").mkdir(exist_ok=True)
    Path("to_process").mkdir(exist_ok=True)
    Path("processed").mkdir(exist_ok=True)

    # Process last commit
    process_last_commit()

    print("Done!")


if __name__ == "__main__":
    main()
