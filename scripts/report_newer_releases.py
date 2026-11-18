#!/usr/bin/env python
"""List installed packages that have a newer release on PyPI, and how each one would arrive.

scripts/sync_dev_venv.py keeps the venv on the reviewed lock; this shows what is newer than that,
so updates can be checked before the weekly Dependency Refresh (or a manual cap change) brings
them in. Notes per package:

- "weekly refresh": a direct requirement whose range allows the release.
- "weekly refresh, if what needs it allows": a locked indirect dependency; the packages that
  depend on it can hold it back (mpmath, held by sympy for torch, is an example).
- "outside <file> range ...": a direct requirement capped below the release, usually a new major
  version. It needs a manual change to requirements/*.txt.
- "needed on <platform>; not pinned in the lock": something the app needs only on this machine's
  platform or Python (colorama, which pytest, tqdm and typer need on Windows). The weekly refresh
  builds the lock on Linux, so it never pins these, and pip keeps them at whatever it installs.
- "not in the lock (local tool)": a tool installed by hand (for example pip-audit) that nothing in
  the lock needs.

Run it with the venv's own Python. It needs network access to PyPI; if pip cannot reach it the
report says so and exits 0, so launchers carry on.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync_dev_venv import PROFILES, REPO_ROOT, canonical_name, lock_file, read_lock  # noqa: E402

PLATFORM_LABELS = {"win32": "Windows", "darwin": "macOS", "linux": "Linux"}


def platform_label() -> str:
    return PLATFORM_LABELS.get(sys.platform, sys.platform)


def needed_here(locked: set[str]) -> set[str]:
    """Installed packages that the locked ones need on this machine, followed through every level.

    Each requirement's environment marker (for example `sys_platform == "win32"` or
    `python_version < "3.11"`) is evaluated for this interpreter; optional extras are ignored.
    """
    from importlib import metadata

    from packaging.requirements import InvalidRequirement, Requirement

    requirements_by_name: dict[str, list[str]] = {}
    for distribution in metadata.distributions():
        name = distribution.metadata["Name"]
        if name:
            requirements_by_name[canonical_name(name)] = list(distribution.requires or [])

    needed: set[str] = set()
    pending = [key for key in locked if key in requirements_by_name]
    seen = set(pending)
    while pending:
        for line in requirements_by_name.get(pending.pop(), []):
            try:
                requirement = Requirement(line)
            except InvalidRequirement:
                continue
            if requirement.marker is not None and not requirement.marker.evaluate({"extra": ""}):
                continue
            key = canonical_name(requirement.name)
            needed.add(key)
            if key not in seen and key in requirements_by_name:
                seen.add(key)
                pending.append(key)
    return needed

REQUIREMENT_FILES = {
    "dev": ("base.txt", "embeddings.txt", "dev.txt"),
    "prod": ("base.txt", "embeddings.txt", "prod.txt"),
}


def read_direct_requirements(profile: str) -> dict[str, tuple[str, str]]:
    """Return {canonical name: (requirements file, specifier)} for the profile's direct requirements."""
    from packaging.requirements import InvalidRequirement, Requirement

    direct: dict[str, tuple[str, str]] = {}
    for filename in REQUIREMENT_FILES[profile]:
        path = REPO_ROOT / "requirements" / filename
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            try:
                requirement = Requirement(line)
            except InvalidRequirement:
                continue
            direct[canonical_name(requirement.name)] = (f"requirements/{filename}", str(requirement.specifier))
    return direct


def outdated_packages() -> list[dict] | None:
    """pip's view of installed packages with a newer release, or None when pip cannot check."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--outdated", "--format=json", "--disable-pip-version-check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return None


def note_for(
    name: str,
    latest: str,
    locked: set[str],
    direct: dict[str, tuple[str, str]],
    platform_needed: set[str] = frozenset(),
) -> str:
    key = canonical_name(name)
    if key in direct:
        filename, specifier = direct[key]
        from packaging.specifiers import SpecifierSet

        if specifier and not SpecifierSet(specifier).contains(latest, prereleases=True):
            return f"outside {filename} range {specifier}: needs a manual change"
        return "weekly refresh"
    if key in locked:
        # Pulled in by another package, whose own requirements can hold it back.
        return "weekly refresh, if what needs it allows"
    if key in platform_needed:
        return f"needed on {platform_label()}; not pinned in the lock"
    return "not in the lock (local tool)"


def build_rows(
    packages: list[dict],
    locked: set[str],
    direct: dict[str, tuple[str, str]],
    platform_needed: set[str] = frozenset(),
) -> list[tuple[str, str, str, str]]:
    rows = [
        (
            package["name"],
            package["version"],
            package["latest_version"],
            note_for(package["name"], package["latest_version"], locked, direct, platform_needed),
        )
        for package in packages
    ]
    # App dependencies first, then local tools; alphabetical within each.
    return sorted(rows, key=lambda row: (row[3].startswith("not in the lock"), row[0].lower()))


def print_rows(rows: list[tuple[str, str, str, str]]) -> None:
    headings = ("Package", "Installed", "Latest", "How it arrives")
    widths = [max(len(heading), *(len(row[index]) for row in rows)) for index, heading in enumerate(headings[:3])]
    print("  " + "  ".join(heading.ljust(width) for heading, width in zip(headings, widths + [0])).rstrip())
    for row in rows:
        print("  " + "  ".join(value.ljust(width) for value, width in zip(row, widths + [0])).rstrip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", choices=PROFILES, default="dev")
    args = parser.parse_args(argv)

    print("Newer releases on PyPI:")
    packages = outdated_packages()
    if packages is None:
        print("  Could not check PyPI (offline?); skipped.")
        return 0
    if not packages:
        print("  None: every installed package is on its latest release.")
        return 0

    lock = lock_file(args.profile)
    locked = set(read_lock(lock)) if lock.exists() else set()
    platform_needed = needed_here(locked) - locked
    print_rows(build_rows(packages, locked, read_direct_requirements(args.profile), platform_needed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
