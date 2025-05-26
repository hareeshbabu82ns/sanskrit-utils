#!/usr/bin/env python3
"""
Version tagging script for the Sanskrit Utils project.
This script helps manage Git tags using semantic versioning (major.minor.patch).
"""

import argparse
import subprocess
import re
import sys
from pathlib import Path


def get_current_version():
    """
    Get the current version from the latest Git tag.
    Returns (0, 0, 0) if no version tag exists.
    """
    try:
        # Get the latest tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print("No existing version tags found. Starting with 0.0.0")
            return (0, 0, 0)
        
        latest_tag = result.stdout.strip()
        
        # Parse the version numbers using regex
        match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", latest_tag)
        if match:
            major, minor, patch = map(int, match.groups())
            return (major, minor, patch)
        else:
            print(f"Latest tag '{latest_tag}' is not in semantic versioning format. Starting with 0.0.0")
            return (0, 0, 0)
    
    except Exception as e:
        print(f"Error retrieving current version: {e}")
        return (0, 0, 0)


def bump_version(current_version, version_type):
    """
    Bump the version number according to semantic versioning rules.
    """
    major, minor, patch = current_version
    
    if version_type == "patch":
        patch += 1
    elif version_type == "minor":
        minor += 1
        patch = 0
    elif version_type == "major":
        major += 1
        minor = 0
        patch = 0
    
    return (major, minor, patch)


def create_tag(version, message=None):
    """
    Create a new Git tag with the given version and push it to the remote repository.
    """
    major, minor, patch = version
    tag_name = f"v{major}.{minor}.{patch}"
    
    # Make sure we're in a git repository
    try:
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], 
                      check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Error: Not in a git repository")
        return False
    
    # Check if tag already exists
    result = subprocess.run(
        ["git", "tag", "-l", tag_name],
        capture_output=True,
        text=True,
        check=True
    )
    
    if tag_name in result.stdout:
        print(f"Error: Tag {tag_name} already exists")
        return False
    
    # Create the tag
    tag_command = ["git", "tag", "-a", tag_name]
    if message:
        tag_command.extend(["-m", message])
    else:
        tag_command.extend(["-m", f"Version {tag_name}"])
    
    try:
        subprocess.run(tag_command, check=True)
        print(f"Created tag: {tag_name}")
        
        # Ask if user wants to push the tag
        push_tag = input("Do you want to push this tag to the remote repository? (y/n): ")
        if push_tag.lower() in ["y", "yes"]:
            subprocess.run(["git", "push", "origin", tag_name], check=True)
            print(f"Pushed tag {tag_name} to remote repository")
        
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"Error creating tag: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create a Git tag with semantic versioning (major.minor.patch)"
    )
    
    parser.add_argument(
        "version_type",
        choices=["patch", "minor", "major"],
        help="The type of version increment to make"
    )
    
    parser.add_argument(
        "-m", "--message", 
        help="The tag message (optional)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without creating a tag"
    )
    
    args = parser.parse_args()
    
    # Get current version from Git tags
    current_version = get_current_version()
    print(f"Current version: {'.'.join(map(str, current_version))}")
    
    # Calculate the new version
    new_version = bump_version(current_version, args.version_type)
    print(f"New version: {'.'.join(map(str, new_version))}")
    
    if args.dry_run:
        print("Dry run - no tag created")
        return
    
    # Create the tag
    success = create_tag(new_version, args.message)
    if success:
        print(f"Successfully created new {args.version_type} version tag")
    

if __name__ == "__main__":
    main()
