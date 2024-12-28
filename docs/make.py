#!/usr/bin/env python3
"""
Script to build Multifact documentation.
"""

import os
import shutil
import subprocess
from pathlib import Path


def clean_build():
    """Clean the build directory."""
    build_dir = Path("build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    print("Cleaned build directory")


def create_dirs():
    """Create necessary directories."""
    dirs = ["source/_static", "source/_templates", "build"]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    print("Created documentation directories")


def copy_readme():
    """Copy README.md to docs directory."""
    shutil.copy("../README.md", "source/")
    print("Copied README.md")


def build_html():
    """Build HTML documentation."""
    result = subprocess.run(
        ["sphinx-build", "-b", "html", "source", "build/html"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("Error building documentation:")
        print(result.stderr)
        return False

    print("Successfully built HTML documentation")
    print(f"Documentation available at: {os.path.abspath('build/html/index.html')}")
    return True


def main():
    """Main build process."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    clean_build()
    create_dirs()
    copy_readme()

    if build_html():
        print("\nBuild completed successfully!")
    else:
        print("\nBuild failed!")
        exit(1)


if __name__ == "__main__":
    main()
