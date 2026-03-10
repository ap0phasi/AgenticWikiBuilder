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


def initial_doer_prompt(session_name, focus_prompt=None):
    """Generate the initial prompt for the doer agent."""
    prompt = f"""
You are an agent responsible for extracting information from provided `raw` data and updating a wiki based on this information.

Please find the raw data in `sessions/{session_name}/raw`. You are encouraged to create working files in `sessions/{session_name}/processed`. Once you complete your wiki updates, create notes about what you did in `sessions/{session_name}/docs`.

You are encouraged to write Python scripts to help with your extraction of information and wiki population in `helpers`. Use `uv` for all Python package management and script execution. Before writing a script, scan this directory to see if another agent has already written a script that can be modified.

Rules for updating the wiki:
- Your goal is to help maintain an accurate, up-to-date wiki. Only populate the wiki based on information you read in `sessions/{session_name}/raw`.
- Use links in the [Some Name](./another_file.md) format.
- Err on the side of many small files: if too many topics are covered in one wiki file, break it out and link them.
- Do not create subfolders, everything must be a markdown in `/wiki`.
- Keep markdown file names readable and compact enough to be intuitive to navigate.
- Do not reference the session_name id in your wiki. Your job is to write a clean article.
- Do not cite your sources, another tool will be responsible for that.

When you're done:
1. Document your changes in `sessions/{session_name}/docs/changes.md` (what you changed and why)
2. Create a brief summary in `sessions/{session_name}/docs/summary.txt` (one line description)
"""
    
    if focus_prompt:
        prompt += f"""
Additionally, you have been requested to focus on the following when updating your wiki: `{focus_prompt}`
"""
    
    return prompt


def call_agent(prompt):
    """Call the agent with the given prompt."""
    print("\n" + "="*80)
    print("AGENT PROMPT:")
    print("="*80)
    print(prompt)
    print("="*80 + "\n")
    
    result = subprocess.run(["opencode", "run", prompt])
    
    if result.returncode != 0:
        print(f"Error calling agent: {result.stderr}", file=sys.stderr)
        return False
    
    return True


def git_create_session_branch(session_name):
    """Create and checkout a new branch for this session."""
    try:
        branch_name = f"session-{session_name}"
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        print(f"✓ Created and checked out branch: {branch_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating session branch: {e}", file=sys.stderr)
        return False


def git_commit_and_merge_session(session_name):
    """Commit changes on session branch and merge back to main."""
    try:
        branch_name = f"session-{session_name}"
        
        # Read summary if available
        summary_path = Path("sessions", session_name, "docs", "summary.txt")
        summary = "Wiki updates"
        if summary_path.exists():
            with open(summary_path, 'r') as f:
                summary = f.read().strip() or "Wiki updates"
        
        # Stage changes
        subprocess.run(["git", "add", "wiki/", "helpers/"], check=True)
        
        # Check if there are changes to commit
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if not status_result.stdout.strip():
            print("No changes to commit.")
            # Still switch back to main
            subprocess.run(["git", "checkout", "main"], check=True)
            subprocess.run(["git", "branch", "-d", branch_name], check=True)
            return True
        
        # Commit on session branch
        commit_msg = f"{summary}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            check=True
        )
        print(f"✓ Committed changes on branch {branch_name}")
        
        # Switch back to main
        subprocess.run(["git", "checkout", "main"], check=True)
        
        # Merge with no-ff to preserve session branch in history
        merge_msg = f"Merge session {session_name}: {summary}"
        merge_result = subprocess.run(
            ["git", "merge", "--no-ff", branch_name, "-m", merge_msg],
            capture_output=True,
            text=True,
            check=False
        )
        
        if merge_result.returncode != 0:
            print(f"⚠ Merge conflict detected!")
            print(f"Stderr: {merge_result.stderr}")
            print(f"You are on branch 'main' with unresolved conflicts.")
            print(f"Please resolve conflicts manually, then:")
            print(f"  git add <resolved-files>")
            print(f"  git commit")
            print(f"  git branch -d {branch_name}")
            return False
        
        print(f"✓ Merged {branch_name} into main")
        
        # Delete session branch
        subprocess.run(["git", "branch", "-d", branch_name], check=True)
        print(f"✓ Deleted branch {branch_name}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error during git operations: {e}", file=sys.stderr)
        return False


def initialize_git_repo():
    """Initialize git repo if it doesn't exist."""
    if not Path(".git").exists():
        print("Initializing git repository...")
        subprocess.run(["git", "init"], check=True)
        
        # Create .gitignore if it doesn't exist
        gitignore_path = Path(".gitignore")
        if not gitignore_path.exists():
            with open(gitignore_path, 'w') as f:
                f.write("# Python\n__pycache__/\n*.pyc\n.venv/\n\n")
                f.write("# Sessions (keep structure, not content)\nsessions/*/raw/*\nsessions/*/processed/*\n")
        
        # Set default branch to main
        subprocess.run(["git", "config", "init.defaultBranch", "main"], check=False)
        subprocess.run(["git", "checkout", "-b", "main"], check=False)
        
        # Initial commit
        subprocess.run(["git", "add", ".gitignore"], check=False)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit", "--allow-empty"],
            check=True
        )
        print("✓ Git repository initialized with main branch")
    else:
        # Ensure we're on main branch
        current_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        if current_branch != "main":
            print(f"Switching from {current_branch} to main...")
            subprocess.run(["git", "checkout", "main"], check=True)


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


def main(source_path):
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
    success = call_agent(initial_doer_prompt(session_name))
    
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
    source_path = "/mnt/c/Users/johnm/Documents/Learning/agentic_wiki_builder/raw/thought.md"
    main(source_path)
