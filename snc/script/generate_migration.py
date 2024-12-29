"""Generate a migration from main to a remote feature branch."""

import argparse
import subprocess
import sys

"""
You do not need to make use of this script for development/staging purposes,
because we always reset the database to a common starting point during dev.

This script is only needed when generating a migration for production to the
innovation-club primary deployment database.

Usage: python3 -m snc.script.generate_migration [remote] [branch]
"""

__authors__ = ["Kris Jordan"]
__copyright__ = "Copyright 2023"
__license__ = "MIT"


def main() -> None:
    """Execute the migration generation process."""
    # Create the parser
    parser = argparse.ArgumentParser(
        description=(
            "Generate a migration from main to a remote feature branch."
        )
    )

    # Add the required argument for the branch name
    parser.add_argument("remote", help="Name of the git remote", type=str)
    parser.add_argument("branch", help="Name of the git branch", type=str)

    # Parse the arguments
    args = parser.parse_args()

    # Use the branch name from the arguments
    remote_name = args.remote
    branch_name = args.branch

    if can_switch_branch():
        print("✅ No uncommitted work")
    else:
        print("❌ Uncommitted files, ensure all changes are committed.")
        sys.exit(1)

    if git_fetch_all():
        print("✅ Fetched all git branches")
    else:
        print("❌ Failed to fetch all git branches.")
        sys.exit(1)

    if branch_exists(branch_name):
        print("✅ Branch {} exists".format(branch_name))
    else:
        print("❌ Branch {} does not exist.".format(branch_name))
        sys.exit(1)

    if switch_branch("main"):
        print("✅ Switched to main branch")
    else:
        print("❌ Failed to switch to main branch.")
        sys.exit(1)

    if pull_remote_branch(remote_name, "main"):
        print("✅ Pulled from {}/main".format(remote_name))
    else:
        print("❌ Failed to pull from {}/main.".format(remote_name))
        sys.exit(1)

    if run_backend_script("reset_testing"):
        print("✅ Reset database to production schema")
    else:
        print("❌ Failed to reset database.")
        sys.exit(1)

    if alembic_stamp_head():
        print("✅ alembic stamp head - migration at production")
    else:
        print("❌ Failed to alembic stamp head.")
        sys.exit(1)

    if switch_branch(branch_name):
        print("✅ Switched to branch {}".format(branch_name))
    else:
        print("❌ Failed to switch to branch {}.".format(branch_name))
        sys.exit(1)

    if pull_remote_branch(remote_name, branch_name):
        msg = "✅ Pulled from {}/{}".format(remote_name, branch_name)
        print(msg)
    else:
        msg = "❌ Failed to pull from {}/{}."
        print(msg.format(remote_name, branch_name))
        sys.exit(1)

    if alembic_generate_migration(branch_name):
        print("✅ alembic revision generated")
    else:
        print("❌ Failed to generate alembic revision")
        sys.exit(1)


def can_switch_branch() -> bool:
    """Check if there are uncommitted changes preventing branch switching.

    Returns:
        True if safe to switch branches, False otherwise
    """
    # Command to check the status of the repository, ignoring untracked files
    command = "git status --porcelain -uno"

    # Run the command
    result = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Check the output
    if result.stdout.strip():
        # Changes are present, cannot switch branches safely
        return False
    else:
        # No changes, safe to switch branches
        return True


def git_fetch_all() -> bool:
    """Fetch all remote branches.

    Returns:
        True if fetch successful, False otherwise
    """
    result = subprocess.run(
        ["git", "fetch", "--all"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0


def branch_exists(branch: str) -> bool:
    """Check if a branch exists locally or remotely.

    Args:
        branch: Name of branch to check

    Returns:
        True if branch exists, False otherwise
    """
    result = subprocess.run(
        ["git", "branch", "-a"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return branch in result.stdout


def switch_branch(branch: str) -> bool:
    """Switch to specified git branch.

    Args:
        branch: Name of branch to switch to

    Returns:
        True if switch successful, False otherwise
    """
    result = subprocess.run(
        ["git", "checkout", branch],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0


def pull_remote_branch(remote: str, branch: str) -> bool:
    """Pull latest changes from remote branch.

    Args:
        remote: Name of git remote
        branch: Name of branch to pull

    Returns:
        True if pull successful, False otherwise
    """
    result = subprocess.run(
        ["git", "pull", "--ff-only", remote, branch],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0


def run_backend_script(script_name: str) -> bool:
    """Run a backend script module.

    Args:
        script_name: Name of script to run

    Returns:
        True if script ran successfully, False otherwise
    """
    result = subprocess.run(
        ["python3", "-m", f"backend.script.{script_name}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0


def alembic_stamp_head() -> bool:
    """Mark the current database version as head in Alembic.

    Returns:
        True if stamp successful, False otherwise
    """
    result = subprocess.run(
        ["alembic", "stamp", "head"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0


def alembic_generate_migration(branch_name: str) -> bool:
    """Generate an Alembic migration for the current schema changes.

    Args:
        branch_name: Name of branch to include in migration message

    Returns:
        True if generation successful, False otherwise
    """
    msg = "Migration for {}".format(branch_name)
    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", msg],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0


if __name__ == "__main__":
    main()
