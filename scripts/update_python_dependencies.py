#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


KNOWN_GOOD_FILES = {
    "dev": Path("requirements/known-good-dev.txt"),
    "prod": Path("requirements/known-good-prod.txt"),
}

PROFILE_FILES = {
    "dev": [Path("requirements/base.txt"), Path("requirements/dev.txt")],
    "prod": [Path("requirements/base.txt")],
}

PROFILE_REQUIREMENTS = {
    "dev": Path("requirements/dev.txt"),
    "prod": Path("requirements/prod.txt"),
}

TARGET_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*==\s*([A-Za-z0-9_.!+:-]+)\s*$")


@dataclass(frozen=True)
class TargetPackage:
    raw_spec: str
    name: str
    version: str
    canonical_name: str


def canonicalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_target_spec(raw_spec: str) -> TargetPackage:
    match = TARGET_PATTERN.match(raw_spec)
    if not match:
        raise SystemExit(f"Invalid target '{raw_spec}'. Use PACKAGE==VERSION.")
    name = match.group(1)
    version = match.group(2)
    return TargetPackage(raw_spec=raw_spec, name=name, version=version, canonical_name=canonicalize_name(name))


def run_command(command: list[str], repo_root: Path) -> None:
    command_text = " ".join(command)
    print(f"+ {command_text}")
    completed = subprocess.run(command, cwd=repo_root, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def run_pip_integrity_check(repo_root: Path) -> None:
    command = [sys.executable, "-m", "pip", "check"]
    command_text = " ".join(command)
    print(f"+ {command_text}")
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, check=False)

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)

    invalid_distribution_seen = "Ignoring invalid distribution" in stderr
    if invalid_distribution_seen or completed.returncode != 0:
        print(
            "Dependency integrity check failed. "
            "A package install may have been interrupted; rerun the updater after closing any running Python processes.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def split_inline_comment(line: str) -> tuple[str, str]:
    hash_index = line.find("#")
    if hash_index == -1:
        return line, ""
    return line[:hash_index], line[hash_index:]


def parse_requirement_name(requirement: str) -> str | None:
    package_match = re.match(r"^([A-Za-z0-9_.-]+)(.*)$", requirement)
    if not package_match:
        return None
    return package_match.group(1)


def update_requirement_line_with_version(line: str, installed_versions: dict[str, str]) -> tuple[str, bool]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or stripped.startswith("-r") or stripped.startswith("-c"):
        return line, False

    body, comment = split_inline_comment(line)
    requirement = body.strip()
    if not requirement:
        return line, False

    package_name = parse_requirement_name(requirement)
    if not package_name:
        return line, False

    installed_version = installed_versions.get(canonicalize_name(package_name))
    if not installed_version:
        return line, False

    specifiers = requirement[len(package_name) :].strip()
    tokens = [token.strip() for token in specifiers.split(",") if token.strip()]
    updated_tokens: list[str] = []
    lower_or_pin_updated = False

    for token in tokens:
        if token.startswith("=="):
            updated_tokens.append(f"=={installed_version}")
            lower_or_pin_updated = True
            continue
        if token.startswith(">=") or token.startswith(">"):
            updated_tokens.append(f">={installed_version}")
            lower_or_pin_updated = True
            continue
        updated_tokens.append(token)

    if not tokens:
        updated_tokens = [f">={installed_version}"]
    elif not lower_or_pin_updated:
        updated_tokens.insert(0, f">={installed_version}")

    updated_requirement = f"{package_name}{','.join(updated_tokens)}"
    updated_line = updated_requirement
    if comment:
        separator = " " if not comment.startswith(" ") else ""
        updated_line = f"{updated_line}{separator}{comment}"

    return updated_line, updated_line != line


def read_installed_versions(repo_root: Path) -> dict[str, str]:
    output = subprocess.check_output(
        [sys.executable, "-m", "pip", "list", "--format", "json"],
        cwd=repo_root,
        text=True,
    )
    packages = json.loads(output)
    result: dict[str, str] = {}
    for package in packages:
        name = package.get("name")
        version = package.get("version")
        if not name or not version:
            continue
        result[canonicalize_name(name)] = version
    return result


def sync_requirement_mins_to_installed(repo_root: Path, profile: str, installed_versions: dict[str, str]) -> list[str]:
    changed_files: list[str] = []
    for relative_path in PROFILE_FILES[profile]:
        file_path = repo_root / relative_path
        if not file_path.exists():
            continue

        source_lines = file_path.read_text(encoding="utf-8").splitlines()
        updated_lines: list[str] = []
        file_changed = False

        for source_line in source_lines:
            updated_line, changed = update_requirement_line_with_version(source_line, installed_versions)
            updated_lines.append(updated_line)
            if changed:
                file_changed = True

        if file_changed:
            file_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
            changed_files.append(str(relative_path))

    return changed_files


def write_known_good_lock(repo_root: Path, profile: str) -> str:
    known_good_path = repo_root / KNOWN_GOOD_FILES[profile]
    known_good_path.parent.mkdir(parents=True, exist_ok=True)
    freeze_output = subprocess.check_output(
        [sys.executable, "-m", "pip", "freeze", "--exclude-editable"],
        cwd=repo_root,
        text=True,
    )
    header = (
        "# Auto-generated known-good dependency lock.\n"
        "# Refresh with scripts/update_python_dependencies.(bat|sh).\n"
    )
    known_good_path.write_text(header + freeze_output, encoding="utf-8")
    return str(KNOWN_GOOD_FILES[profile])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Update Python dependencies and promote tested versions. "
            "Default mode (no targets): upgrade the whole profile and then sync minimum versions."
        )
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Optional explicit package targets using PACKAGE==VERSION (for example Flask==3.1.1).",
    )
    parser.add_argument(
        "--profile",
        choices=("dev", "prod"),
        default="dev",
        help="Dependency profile to update (default: dev).",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pytest run (tests are run by default for dev profile).",
    )
    parser.add_argument(
        "--skip-sync-requirements",
        action="store_true",
        help="Do not rewrite minimum versions in requirements files.",
    )
    parser.add_argument(
        "--skip-lock",
        action="store_true",
        help="Do not rewrite requirements/known-good-<profile>.txt.",
    )
    parser.add_argument(
        "--test-cmd",
        default="",
        help=(
            "Optional custom test command, for example: \"-m pytest -p no:cacheprovider\". "
            "If omitted, dev profile runs the full pytest suite: -m pytest -p no:cacheprovider."
        ),
    )
    parser.add_argument(
        "--skip-playwright-install",
        action="store_true",
        help="Skip Playwright browser install before dev tests.",
    )
    return parser.parse_args()


def upgrade_dependencies(repo_root: Path, profile: str, targets: list[str]) -> None:
    if targets:
        target_specs = [parse_target_spec(target).raw_spec for target in targets]
        run_command([sys.executable, "-m", "pip", "install", "--upgrade", *target_specs], repo_root)
        return

    profile_file = PROFILE_REQUIREMENTS[profile]
    run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--upgrade-strategy",
            "eager",
            "-r",
            str(profile_file),
        ],
        repo_root,
    )


def run_tests_if_enabled(args: argparse.Namespace, repo_root: Path) -> None:
    if args.profile != "dev" or args.skip_tests:
        return

    if args.test_cmd.strip():
        run_command([sys.executable, *shlex.split(args.test_cmd.strip(), posix=False)], repo_root)
        return

    run_command([sys.executable, "-m", "pytest", "-p", "no:cacheprovider"], repo_root)


def ensure_playwright_browser_if_needed(args: argparse.Namespace, repo_root: Path, installed_versions: dict[str, str]) -> None:
    if args.profile != "dev" or args.skip_tests or args.skip_playwright_install:
        return
    if "playwright" not in installed_versions:
        return
    run_command([sys.executable, "-m", "playwright", "install", "chromium"], repo_root)


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    upgrade_dependencies(repo_root, args.profile, args.targets)
    run_pip_integrity_check(repo_root)
    installed_versions = read_installed_versions(repo_root)
    ensure_playwright_browser_if_needed(args, repo_root, installed_versions)
    run_tests_if_enabled(args, repo_root)

    changed_files: list[str] = []
    if not args.skip_sync_requirements:
        changed_files = sync_requirement_mins_to_installed(repo_root, args.profile, installed_versions)

    lock_file = ""
    if not args.skip_lock:
        lock_file = write_known_good_lock(repo_root, args.profile)

    print("Dependency update workflow completed.")
    if args.targets:
        print(f"Mode: targeted update ({len(args.targets)} package(s))")
    else:
        print(f"Mode: full profile update ({args.profile})")
    if changed_files:
        print("Updated requirement files:")
        for file_name in changed_files:
            print(f"  - {file_name}")
    if lock_file:
        print(f"Updated known-good lock: {lock_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
