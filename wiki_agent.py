#!/usr/bin/env python3
"""
Wiki agent processor - processes info files and calls OpenCode to update wiki
"""

import os
import json
import subprocess
import shutil
from pathlib import Path


def run_cmd(cmd, cwd=None):
    """Run a command and return the result."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result


def get_current_branch():
    """Get the current git branch name."""
    result = run_cmd(["git", "branch", "--show-current"])
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def create_branch(branch_name):
    """Create and checkout a new branch."""
    result = run_cmd(["git", "checkout", "-b", branch_name])
    if result.returncode != 0:
        print(f"Failed to create branch {branch_name}: {result.stderr}")
        return False
    return True


def checkout_branch(branch_name):
    """Checkout an existing branch."""
    result = run_cmd(["git", "checkout", branch_name])
    if result.returncode != 0:
        print(f"Failed to checkout branch {branch_name}: {result.stderr}")
        return False
    return True


def call_agent_to_fix(branch_name, feedback, original_content, filename):
    """Call OpenCode agent to fix issues based on reviewer feedback."""
    print(f"\n{'!' * 60}")
    print(f"FIXING ISSUES: {branch_name}")
    print(f"{'!' * 60}\n")

    # Make sure we're on the branch
    checkout_branch(branch_name)

    fix_prompt = f"""You are fixing wiki documentation that was rejected by a reviewer.

Original source file: {filename}

Reviewer feedback:
{feedback}

Your task:
1. Read the current wiki files in the /wiki directory
2. Fix the issues mentioned by the reviewer
3. ONLY modify markdown files in /wiki directory
4. Ensure all links are properly formatted as [Text](./page.md)
5. Make the content well-organized and clear
6. Commit your fixes with a clear message

After fixing, commit your changes.
"""

    print("Calling OpenCode agent to fix issues...")
    print(f"Fix prompt preview: {fix_prompt[:200]}...\n")

    # Call OpenCode with fix prompt
    result = run_cmd(["opencode", "run", fix_prompt])

    if result.returncode != 0:
        print(f"Fix agent failed: {result.stderr}")
        return False

    print(f"\nFix agent output:\n{result.stdout}\n")

    # Check if there are changes
    result = run_cmd(["git", "status", "--porcelain", "wiki/"])

    if result.stdout.strip():
        print("Changes detected after fixes")
        # Add and commit
        run_cmd(["git", "add", "wiki/"])
        result = run_cmd(
            ["git", "commit", "-m", "Fix wiki issues based on reviewer feedback"]
        )

        if result.returncode == 0:
            print("✓ Committed fixes")
            return True
        else:
            print(f"Failed to commit fixes: {result.stderr}")
            return False
    else:
        print("No changes made by fix agent")
        return False


def review_and_merge_loop(
    branch_name, original_branch, info_id, filename, content, max_iterations=5
):
    """Review and fix loop - keeps trying until accepted or max iterations reached."""

    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'~' * 60}")
        print(f"REVIEW CYCLE {iteration}/{max_iterations}: {branch_name}")
        print(f"{'~' * 60}\n")

        # Make sure we're on the branch
        checkout_branch(branch_name)

        # Get the diff between original branch and current branch
        result = run_cmd(["git", "diff", original_branch, branch_name, "--", "wiki/"])
        diff_output = result.stdout

        if not diff_output.strip():
            print("⚠ No diff detected between branches")
            # Check if wiki files exist on this branch
            result = run_cmd(
                ["git", "ls-tree", "-r", "--name-only", branch_name, "wiki/"]
            )
            if result.stdout.strip():
                print("Wiki files exist but match original - merging anyway")
            else:
                print("No wiki files found on branch")

            # Merge and cleanup
            checkout_branch(original_branch)
            result = run_cmd(
                [
                    "git",
                    "merge",
                    "--no-ff",
                    branch_name,
                    "-m",
                    f"Merge wiki updates from {info_id[:8]}",
                ]
            )
            if result.returncode == 0:
                run_cmd(["git", "branch", "-d", branch_name])
            return True

        print(f"Changes detected ({len(diff_output)} chars of diff)\n")

        # Create review prompt
        review_prompt = f"""You are a code reviewer for a wiki documentation project.

Your task is to review the changes made to the wiki in branch '{branch_name}'.

Here is the diff of changes:

{diff_output}

Please review these changes and determine if they should be merged.

Criteria for acceptance:
1. All files are markdown (.md) files in the /wiki directory
2. Content is well-organized and clear
3. Links between pages are properly formatted as [Text](./page.md)
4. No errors or malformed markdown
5. Content accurately reflects the source material

Respond with EXACTLY one of:
- ACCEPT: if the changes are good and should be merged
- REJECT: <explanation of what needs to be fixed>

Be specific about what needs to be fixed if you reject.
"""

        print("Calling OpenCode reviewer agent...")

        # Call OpenCode with review prompt
        result = run_cmd(["opencode", "run", review_prompt])

        if result.returncode != 0:
            print(f"Review agent failed: {result.stderr}")
            # Force merge to clean up
            checkout_branch(original_branch)
            result = run_cmd(
                [
                    "git",
                    "merge",
                    "--no-ff",
                    branch_name,
                    "-m",
                    f"Force merge wiki updates from {info_id[:8]} (review failed)",
                ]
            )
            if result.returncode == 0:
                run_cmd(["git", "branch", "-d", branch_name])
            return False

        review_output = result.stdout.strip()
        print(f"\nReview output:\n{review_output}\n")

        # Check if accepted or rejected
        if "ACCEPT" in review_output.upper():
            print("✓ Changes ACCEPTED by reviewer")
            print(f"Merging {branch_name} into {original_branch}...")

            # Checkout original branch
            if not checkout_branch(original_branch):
                return False

            # Merge the branch
            result = run_cmd(
                [
                    "git",
                    "merge",
                    "--no-ff",
                    branch_name,
                    "-m",
                    f"Merge wiki updates from {info_id[:8]}",
                ]
            )

            if result.returncode == 0:
                print(f"✓ Successfully merged {branch_name}")

                # Delete the branch
                result = run_cmd(["git", "branch", "-d", branch_name])
                if result.returncode == 0:
                    print(f"✓ Deleted branch {branch_name}")

                return True
            else:
                print(f"✗ Merge failed: {result.stderr}")
                # Try force delete
                run_cmd(["git", "branch", "-D", branch_name])
                return False

        else:
            # Rejected - extract feedback and call fix agent
            print(f"✗ Changes REJECTED by reviewer (iteration {iteration})")

            if iteration >= max_iterations:
                print(f"⚠ Max iterations ({max_iterations}) reached without acceptance")
                # Force merge anyway to avoid leaving branches
                print("Force merging to avoid leaving dangling branches...")
                checkout_branch(original_branch)
                result = run_cmd(
                    [
                        "git",
                        "merge",
                        "--no-ff",
                        branch_name,
                        "-m",
                        f"Force merge wiki updates from {info_id[:8]} (max iterations)",
                    ]
                )
                if result.returncode == 0:
                    run_cmd(["git", "branch", "-d", branch_name])
                return False

            # Call fix agent - this stays on the branch and commits fixes
            if not call_agent_to_fix(branch_name, review_output, content, filename):
                print("Fix agent failed to make changes")
                # Force merge to avoid leaving branches
                checkout_branch(original_branch)
                result = run_cmd(
                    [
                        "git",
                        "merge",
                        "--no-ff",
                        branch_name,
                        "-m",
                        f"Force merge wiki updates from {info_id[:8]} (fix failed)",
                    ]
                )
                if result.returncode == 0:
                    run_cmd(["git", "branch", "-d", branch_name])
                return False

            # Loop continues to review again
            print("\nRetrying review with fixes...\n")

    # Should never reach here but just in case
    print("⚠ Exited loop unexpectedly, force merging...")
    checkout_branch(original_branch)
    result = run_cmd(
        [
            "git",
            "merge",
            "--no-ff",
            branch_name,
            "-m",
            f"Force merge wiki updates from {info_id[:8]} (unexpected exit)",
        ]
    )
    if result.returncode == 0:
        run_cmd(["git", "branch", "-d", branch_name])
    return False


def process_info_file(info_path):
    """Process a single info file and call OpenCode."""
    print(f"\n{'=' * 60}")
    print(f"Processing: {info_path.name}")
    print(f"{'=' * 60}\n")

    # Read the info file
    with open(info_path, "r") as f:
        info_data = json.load(f)

    info_id = info_data["id"]
    filename = info_data["filename"]
    content = info_data["content"]
    commit_id = info_data["commit_id"]

    print(f"ID: {info_id}")
    print(f"File: {filename}")
    print(f"Commit: {commit_id}")
    print(f"Content length: {len(content)} chars\n")

    # Save the original branch
    original_branch = get_current_branch()
    if not original_branch:
        print("Could not determine current branch")
        return False

    # Create a branch for this info file
    branch_name = f"wiki-update-{info_id}"

    # Check if branch already exists
    result = run_cmd(["git", "branch", "--list", branch_name])
    if result.stdout.strip():
        print(f"Branch {branch_name} already exists, deleting it first...")
        # Force delete the old branch
        run_cmd(["git", "branch", "-D", branch_name])

    print(f"Creating branch: {branch_name}")
    if not create_branch(branch_name):
        return False

    # Create the prompt for OpenCode
    prompt = f"""You are updating a wiki based on source documentation.

Source file: {filename}
Commit ID: {commit_id}

Content:
{content}

Your task:
1. Create or update markdown files in the /wiki directory based on this content
2. ONLY create markdown files - no other file types
3. The markdown files must contain links to other relevant wiki pages
4. Use relative links like [Page Name](./page_name.md)
5. Organize the content logically - you can create multiple wiki pages if needed
6. Extract key concepts, create index pages, cross-reference related topics
7. Make the wiki navigable and well-structured

After you create/update the wiki files, commit your changes with a clear message.

Do NOT touch any files outside of the /wiki directory.
"""

    print("Calling OpenCode agent...")
    print(f"Prompt preview: {prompt[:200]}...\n")

    # Call OpenCode with the prompt by passing it as input
    result = run_cmd(["opencode", "run", prompt])

    if result.returncode != 0:
        print(f"OpenCode execution failed: {result.stderr}")
        checkout_branch(original_branch)
        run_cmd(["git", "branch", "-D", branch_name])
        return False

    print(f"\nOpenCode output:\n{result.stdout}\n")

    # Check if wiki files exist on this branch (OpenCode may have already committed)
    result = run_cmd(["git", "ls-tree", "-r", "--name-only", branch_name, "wiki/"])

    if not result.stdout.strip():
        print("✗ No wiki files found on branch - OpenCode agent failed to create files")
        checkout_branch(original_branch)
        run_cmd(["git", "branch", "-D", branch_name])

        # Still move to processed to mark as attempted
        processed_dir = Path("processed")
        processed_dir.mkdir(exist_ok=True)
        dest_path = processed_dir / info_path.name
        shutil.move(str(info_path), str(dest_path))
        print(f"⚠ Moved {info_path.name} to processed/ (no wiki files created)")
        return False

    print(f"✓ Wiki files found on branch: {len(result.stdout.strip().split())} files")

    # Check if there are uncommitted changes
    result = run_cmd(["git", "status", "--porcelain", "wiki/"])

    if result.stdout.strip():
        print("Uncommitted changes detected, committing...")
        # Add and commit the changes
        run_cmd(["git", "add", "wiki/"])
        commit_msg = f"Update wiki based on {filename} (commit {commit_id[:8]})"
        result = run_cmd(["git", "commit", "-m", commit_msg])

        if result.returncode != 0:
            print(f"Failed to commit: {result.stderr}")
        else:
            print(f"✓ Committed changes: {commit_msg}")
    else:
        print("✓ All changes already committed by OpenCode")

    # REVIEW AND MERGE PHASE - Loop until accepted or max iterations
    review_accepted = review_and_merge_loop(
        branch_name, original_branch, info_id, filename, content
    )

    # Always move to processed since we always merge (even if not accepted after max iterations)
    processed_dir = Path("processed")
    processed_dir.mkdir(exist_ok=True)

    dest_path = processed_dir / info_path.name
    shutil.move(str(info_path), str(dest_path))

    if review_accepted:
        print(f"✓ Moved {info_path.name} to processed/ (accepted)")
        return True
    else:
        print(
            f"⚠ Moved {info_path.name} to processed/ (merged after max iterations or issues)"
        )
        return False


def main():
    """Main function to process all info files."""
    print("Wiki Agent Processor")
    print("=" * 60)

    # Ensure we're in a git repo
    result = run_cmd(["git", "rev-parse", "--git-dir"])
    if result.returncode != 0:
        print("Not in a git repository!")
        return

    # Create necessary directories
    Path("wiki").mkdir(exist_ok=True)
    Path("to_process").mkdir(exist_ok=True)
    Path("processed").mkdir(exist_ok=True)

    # Get all info files
    info_dir = Path("info")
    if not info_dir.exists():
        print("No info directory found")
        return

    info_files = list(info_dir.glob("*.json"))

    if not info_files:
        print("No info files to process")
        return

    print(f"\nFound {len(info_files)} info file(s) to process\n")

    # Process each info file
    for info_file in info_files:
        success = process_info_file(info_file)
        if success:
            print(f"✓ Successfully processed {info_file.name}\n")
        else:
            print(f"✗ Failed to process {info_file.name}\n")

    print("\n" + "=" * 60)
    print("Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
