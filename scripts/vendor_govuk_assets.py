#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


FILES_TO_COPY = [
    "govuk-frontend.min.css",
    "govuk-frontend.min.css.map",
    "govuk-frontend.min.js",
    "govuk-frontend.min.js.map",
]
DIRECTORIES_TO_COPY = ["assets"]


def run_command(command: list[str], repo_root: Path) -> None:
    completed = subprocess.run(command, cwd=repo_root, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def install_govuk(version: str, repo_root: Path) -> None:
    requested = "latest" if version == "latest" else version
    run_command(
        [
            "npm",
            "install",
            "--save-dev",
            "--save-exact",
            f"govuk-frontend@{requested}",
        ],
        repo_root,
    )


def read_installed_version(repo_root: Path) -> str:
    package_file = repo_root / "node_modules" / "govuk-frontend" / "package.json"
    if not package_file.exists():
        raise SystemExit(
            "govuk-frontend is not installed. Run 'npm install --save-dev --save-exact govuk-frontend@<version>' first."
        )
    payload = json.loads(package_file.read_text(encoding="utf-8"))
    return payload["version"]


def vendor_assets(repo_root: Path, version: str) -> None:
    source_root = repo_root / "node_modules" / "govuk-frontend" / "dist" / "govuk"
    if not source_root.exists():
        raise SystemExit(f"Missing GOV.UK distribution assets at {source_root}")

    destination_root = repo_root / "app" / "static" / "vendor" / "govuk"
    destination_root.mkdir(parents=True, exist_ok=True)

    for file_name in FILES_TO_COPY:
        shutil.copy2(source_root / file_name, destination_root / file_name)

    for directory_name in DIRECTORIES_TO_COPY:
        source_dir = source_root / directory_name
        destination_dir = destination_root / directory_name
        shutil.rmtree(destination_dir, ignore_errors=True)
        shutil.copytree(source_dir, destination_dir)

    (destination_root / "VERSION").write_text(f"{version}\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vendor GOV.UK frontend assets into app/static/vendor/govuk")
    parser.add_argument(
        "--update",
        metavar="VERSION",
        help="Install and pin a GOV.UK frontend version before vendoring (use 'latest' or a semver like 6.2.0).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    if args.update:
        install_govuk(args.update, repo_root)

    version = read_installed_version(repo_root)
    vendor_assets(repo_root, version)
    print(f"Vendored GOV.UK Frontend {version} assets to app/static/vendor/govuk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
