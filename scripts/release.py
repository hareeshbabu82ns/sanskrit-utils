#!/usr/bin/env python3
"""
Cut a release by creating and pushing a semantic version tag (vMAJOR.MINOR.PATCH).

Pushing the tag triggers .github/workflows/docker-publish.yml, which builds and
pushes the Docker image to GHCR and creates a GitHub Release with generated notes.

    scripts/release.py patch            # v1.2.3 -> v1.2.4
    scripts/release.py minor -m "..."   # v1.2.3 -> v1.3.0
    scripts/release.py major --dry-run  # v1.2.3 -> v2.0.0 (show only)
    scripts/release.py patch --yes      # push without prompting
"""
import argparse
import re
import subprocess
import sys

RELEASE_BRANCHES = ("master", "main")
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def git(*args, check=True):
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          check=check).stdout.strip()


def fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def latest_version():
    """Highest vX.Y.Z tag in the repo (not just the nearest reachable one)."""
    versions = [tuple(map(int, m.groups()))
                for t in git("tag", "--list", "v*").splitlines()
                if (m := TAG_RE.match(t))]
    return max(versions, default=(0, 0, 0))


def bump(version, part):
    major, minor, patch = version
    if part == "major":
        return (major + 1, 0, 0)
    if part == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def preflight(allow_any_branch):
    if git("status", "--porcelain"):
        fail("working tree has uncommitted changes; commit or stash first")

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch not in RELEASE_BRANCHES and not allow_any_branch:
        fail(f"on branch '{branch}'; releases are cut from {'/'.join(RELEASE_BRANCHES)} "
             "(use --allow-any-branch to override)")

    git("fetch", "--tags", "--quiet", "origin")
    upstream = git("rev-parse", "--abbrev-ref", "@{u}", check=False)
    if upstream:
        behind = git("rev-list", "--count", f"HEAD..{upstream}")
        ahead = git("rev-list", "--count", f"{upstream}..HEAD")
        if behind != "0":
            fail(f"branch is {behind} commit(s) behind {upstream}; pull first")
        if ahead != "0":
            print(f"note: {ahead} unpushed commit(s) on {branch} will be pushed with the tag")
    return branch


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("part", choices=["patch", "minor", "major"])
    ap.add_argument("-m", "--message", help="tag annotation (default: 'Release vX.Y.Z')")
    ap.add_argument("-y", "--yes", action="store_true", help="push without prompting")
    ap.add_argument("--dry-run", action="store_true", help="show the next version and exit")
    ap.add_argument("--allow-any-branch", action="store_true")
    args = ap.parse_args()

    branch = preflight(args.allow_any_branch) if not args.dry_run else None
    current = latest_version()
    new_tag = "v%d.%d.%d" % bump(current, args.part)
    print("current: v%d.%d.%d  ->  new: %s" % (*current, new_tag))

    if args.dry_run:
        return

    git("tag", "-a", new_tag, "-m", args.message or f"Release {new_tag}")
    print(f"created tag {new_tag}")

    if not args.yes and input("push branch and tag to origin? [y/N] ").lower() not in ("y", "yes"):
        print(f"not pushed; push later with: git push origin {branch} {new_tag}")
        return

    subprocess.run(["git", "push", "origin", branch], check=True)
    subprocess.run(["git", "push", "origin", new_tag], check=True)
    print(f"pushed {new_tag}; CI will build the image and publish the GitHub Release")


if __name__ == "__main__":
    main()
