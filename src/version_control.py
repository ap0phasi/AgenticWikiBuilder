import subprocess
import sys
from pathlib import Path

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
