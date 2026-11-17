#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


FILES_TO_COPY = [
    "govuk-frontend.min.js",
    "govuk-frontend.min.js.map",
]
DIRECTORIES_TO_COPY = ["assets"]
# GDS Transport is for GOV.UK services only; Jigsaurium uses Lexend instead (see the Sass entry point).
ASSET_PATTERNS_TO_SKIP = ["fonts"]

# The CSS is compiled from GOV.UK Frontend's Sass with Jigsaurium's settings, not copied prebuilt.
SASS_ENTRY_POINT = Path("app/static/scss/govuk-frontend.scss")
COMPILED_CSS_NAME = "govuk-frontend.min.css"
STALE_FILES = ["govuk-frontend.min.css.map"]

# Lexend (SIL Open Font License 1.1) from the pinned @fontsource/lexend package. OFL.txt in the
# destination is the upstream licence text and is kept as it is.
LEXEND_SOURCE = Path("node_modules/@fontsource/lexend/files")
LEXEND_DESTINATION = Path("app/static/fonts/lexend")
LEXEND_FILES = [
    f"lexend-{subset}-{weight}-normal.{extension}"
    for subset in ("latin", "latin-ext")
    for weight in (400, 700)
    for extension in ("woff2", "woff")
]


def run_command(command: list[str], repo_root: Path) -> None:
    completed = subprocess.run(command, cwd=repo_root, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def resolve_npm_command_prefix() -> list[str]:
    npm_cmd = shutil.which("npm") or shutil.which("npm.cmd") or shutil.which("npm.exe")
    if not npm_cmd:
        raise SystemExit("npm is required to update GOV.UK frontend assets.")

    npm_path = Path(npm_cmd)
    if npm_path.suffix.lower() == ".cmd":
        node_executable = shutil.which("node") or shutil.which("node.exe")
        npm_cli = npm_path.parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
        if node_executable and npm_cli.exists():
            return [node_executable, str(npm_cli)]

    for candidate in ("npm", "npm.cmd", "npm.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return [resolved]
    raise SystemExit("npm is required to update GOV.UK frontend assets.")


def install_govuk(version: str, repo_root: Path) -> None:
    requested = "latest" if version == "latest" else version
    npm_command_prefix = resolve_npm_command_prefix()
    run_command(
        npm_command_prefix
        + [
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
        shutil.copytree(source_dir, destination_dir, ignore=shutil.ignore_patterns(*ASSET_PATTERNS_TO_SKIP))

    for file_name in STALE_FILES:
        (destination_root / file_name).unlink(missing_ok=True)

    compile_govuk_css(repo_root, destination_root / COMPILED_CSS_NAME)
    copy_lexend_fonts(repo_root)

    (destination_root / "VERSION").write_text(f"{version}\n", encoding="utf-8")


def compile_govuk_css(repo_root: Path, destination: Path) -> None:
    node_executable = shutil.which("node") or shutil.which("node.exe")
    sass_cli = repo_root / "node_modules" / "sass" / "sass.js"
    if not node_executable or not sass_cli.exists():
        raise SystemExit("Node.js and the pinned 'sass' dev dependency are required. Run 'npm ci' first.")
    run_command(
        [
            node_executable,
            str(sass_cli),
            "--load-path=node_modules",
            "--style=compressed",
            "--no-source-map",
            "--quiet-deps",
            str(SASS_ENTRY_POINT),
            str(destination.relative_to(repo_root)),
        ],
        repo_root,
    )


def copy_lexend_fonts(repo_root: Path) -> None:
    source_dir = repo_root / LEXEND_SOURCE
    if not source_dir.exists():
        raise SystemExit(f"Missing Lexend font files at {source_dir}. Run 'npm ci' first.")
    destination_dir = repo_root / LEXEND_DESTINATION
    destination_dir.mkdir(parents=True, exist_ok=True)
    for file_name in LEXEND_FILES:
        shutil.copy2(source_dir / file_name, destination_dir / file_name)


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
