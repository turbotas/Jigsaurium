#!/usr/bin/env python
"""Keep this checkout's virtualenv in line with the reviewed dependency lock file.

The weekly Dependency Refresh keeps requirements/known-good-<profile>.txt current, and CI and the
images install exactly those versions. A local .venv is only installed once (scripts/setup_venv),
so after a git pull it can quietly fall behind. This compares the venv with the lock and, with
--sync, brings it back in line using the same pip command as setup_venv.

Run it with the venv's own Python. Exit code 0 means the venv matches the lock; 1 means it does
not (or the sync failed), so launchers can warn and carry on.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES = ("dev", "prod")
PIN_PATTERN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*==\s*([^\s;]+)")


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirements_file(profile: str) -> Path:
    return REPO_ROOT / "requirements" / f"{profile}.txt"


def lock_file(profile: str) -> Path:
    return REPO_ROOT / "requirements" / f"known-good-{profile}.txt"


def read_lock(path: Path) -> dict[str, tuple[str, str]]:
    """Return {canonical name: (name as written, pinned version)} for every `name==version` line."""
    pins: dict[str, tuple[str, str]] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = PIN_PATTERN.match(line)
        if match:
            pins[canonical_name(match.group(1))] = (match.group(1), match.group(2))
    return pins


def installed_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution in metadata.distributions():
        name = distribution.metadata["Name"]
        if name:
            versions[canonical_name(name)] = distribution.version
    return versions


def same_version(installed: str, pinned: str) -> bool:
    if installed == pinned:
        return True
    try:
        from packaging.version import Version

        return Version(installed) == Version(pinned)
    except Exception:
        return False


def differences(pins: dict[str, tuple[str, str]], installed: dict[str, str]) -> list[tuple[str, str | None, str]]:
    """Locked packages that are missing or at another version: [(name, installed or None, pinned)]."""
    found = []
    for key, (name, pinned) in sorted(pins.items()):
        current = installed.get(key)
        if current is None or not same_version(current, pinned):
            found.append((name, current, pinned))
    return found


def print_differences(found: list[tuple[str, str | None, str]]) -> None:
    width = max(len(name) for name, _current, _pinned in found)
    for name, current, pinned in found:
        print(f"    {name.ljust(width)}  {current or 'not installed'} -> {pinned}")


def sync(profile: str, playwright_changed: bool) -> bool:
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--disable-pip-version-check",
        "-r",
        str(requirements_file(profile)),
        "-c",
        str(lock_file(profile)),
    ]
    if subprocess.run(command, cwd=REPO_ROOT, check=False).returncode != 0:
        print("  pip could not install the locked versions; see the output above.")
        return False
    if playwright_changed:
        # A new Playwright release drives a new browser build, which pip does not install.
        print("  Playwright changed: installing its Chromium build.")
        browser = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], cwd=REPO_ROOT, check=False)
        if browser.returncode != 0:
            print("  Could not install Chromium for Playwright; UI tests may be skipped until it is.")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", choices=PROFILES, default="dev")
    parser.add_argument("--sync", action="store_true", help="install the locked versions when the venv differs")
    args = parser.parse_args(argv)

    lock = lock_file(args.profile)
    print(f"Python packages compared with {lock.relative_to(REPO_ROOT).as_posix()}:")
    if not lock.exists():
        print("  No lock file for this profile; nothing to compare.")
        return 0
    pins = read_lock(lock)

    found = differences(pins, installed_versions())
    if not found:
        print(f"  In line with the lock ({len(pins)} packages).")
        return 0

    print(f"  {len(found)} of {len(pins)} locked packages differ:")
    print_differences(found)
    if not args.sync:
        print(f"  Run scripts/sync_dev_venv.py --sync --profile {args.profile} (or scripts/setup_venv) to update.")
        return 1

    print("  Installing the locked versions...")
    playwright_changed = any(canonical_name(name) == "playwright" for name, _current, _pinned in found)
    if not sync(args.profile, playwright_changed):
        return 1

    remaining = differences(pins, installed_versions())
    if remaining:
        print(f"  Still {len(remaining)} different after installing:")
        print_differences(remaining)
        return 1
    print(f"  Done: in line with the lock ({len(pins)} packages).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
