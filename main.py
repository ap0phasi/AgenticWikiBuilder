"""
Agentic Wiki Builder

Creates isolated sessions for processing raw data into wiki articles.
Each agent gets their own workspace but contributes to a shared wiki.
"""

import uuid
import os
from pathlib import Path
import subprocess
import shutil
import sys
import argparse

from src.agents.writer import writer_prompt
from src.agents.runner import call_agent
from src.version_control import git_commit_and_merge_session, initialize_git_repo, git_create_session_branch
  

def create_session(source_path):
    """Create a new session directory and copy raw data."""
    session_name = str(uuid.uuid4())
    session_path = Path("sessions", session_name)
    
    print(f"Creating session: {session_name}")
    
    try:
        # Create session directories
        session_path.mkdir(parents=True, exist_ok=False)
        (session_path / "raw").mkdir()
        (session_path / "processed").mkdir()
        (session_path / "docs").mkdir()
        
        # Copy source file to raw
        if not Path(source_path).exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        dest_path = session_path / "raw" / "info.md"
        shutil.copyfile(source_path, dest_path)
        print(f"✓ Copied {source_path} to {dest_path}")
        
        return session_name
        
    except Exception as e:
        print(f"Error creating session: {e}", file=sys.stderr)
        # Cleanup on failure
        if session_path.exists():
            shutil.rmtree(session_path)
        return None

# Args

parser = argparse.ArgumentParser(
    description='Agentic Wiki Builder',
    epilog="Takes some file and updates a knowledge base wiki in the working directory")
parser.add_argument("file_path")
parser.add_argument("--additional_prompt","-a")

def main(source_path, additional_prompt):
    """Main entry point."""
    # Create base directories
    os.makedirs("wiki", exist_ok=True)
    os.makedirs("helpers", exist_ok=True)
    os.makedirs("sessions", exist_ok=True)
    
    # Initialize git if needed
    initialize_git_repo()
    
    session_name = create_session(source_path)
    
    if not session_name:
        print("Failed to create session. Exiting.")
        sys.exit(1)
    
    # Create session branch
    print("\nCreating session branch...")
    if not git_create_session_branch(session_name):
        print("Failed to create session branch. Exiting.")
        sys.exit(1)
    
    # Call the doer agent
    print("\nCalling doer agent...")
    success = call_agent(writer_prompt(session_name, additional_prompt))
    
    if not success:
        print("Agent execution failed.")
        print("Switching back to main and cleaning up...")
        subprocess.run(["git", "checkout", "main"], check=False)
        subprocess.run(["git", "branch", "-D", f"session-{session_name}"], check=False)
        sys.exit(1)
    
    # Commit and merge changes
    print("\nCommitting and merging changes...")
    if git_commit_and_merge_session(session_name):
        print(f"\n✓ Session {session_name} completed successfully!")
        print(f"  - Raw data: sessions/{session_name}/raw/")
        print(f"  - Documentation: sessions/{session_name}/docs/")
        print(f"  - Wiki updated: wiki/")
        print(f"\nTo see this session's changes: git log --oneline --graph")
    else:
        print("\n⚠ Session completed but git merge failed. Check for conflicts.")
        sys.exit(1)


if __name__ == "__main__":
    # Create session and copy raw data
    args = parser.parse_args()
    main(args.file_path, args.additional_prompt)
