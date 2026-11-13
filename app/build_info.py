"""Version and build details for a run straight from a git checkout (run.bat / run.sh).

Container images get APP_VERSION and APP_BUILD_SHA as build arguments. A checkout has neither,
so without this the banner shows the placeholder 0.0.0-dev. Here they are read from git instead:
a checkout on a release tag shows that tag (for example v0.2.14); one with commits after the tag
shows how far ahead it is (v0.2.14-3-gabc1234), and "-dirty" marks uncommitted changes.
"""

import subprocess
from pathlib import Path

DEFAULT_APP_VERSION = "0.0.0-dev"
DEFAULT_APP_BUILD_SHA = "local"
GIT_TIMEOUT_SECONDS = 3


def _run_git(repo_root, *args):
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def describe_git_checkout(repo_root):
    """Return {"version", "build_sha"} read from git, with None for anything git cannot tell."""
    return {
        "version": _run_git(repo_root, "describe", "--tags", "--match", "v*", "--dirty"),
        "build_sha": _run_git(repo_root, "rev-parse", "HEAD"),
    }


def apply_git_build_info(app, repo_root=None):
    """Fill APP_VERSION / APP_BUILD_SHA from git when they were not supplied.

    Values set in the environment or config (as in container images) always win.
    """
    version_is_default = app.config.get("APP_VERSION") in (None, "", DEFAULT_APP_VERSION)
    sha_is_default = app.config.get("APP_BUILD_SHA") in (None, "", DEFAULT_APP_BUILD_SHA)
    if not (version_is_default or sha_is_default):
        return

    root = Path(repo_root) if repo_root is not None else Path(app.root_path).parent
    if not (root / ".git").exists():
        return

    details = describe_git_checkout(root)
    if version_is_default and details["version"]:
        app.config["APP_VERSION"] = details["version"]
    if sha_is_default and details["build_sha"]:
        app.config["APP_BUILD_SHA"] = details["build_sha"]
