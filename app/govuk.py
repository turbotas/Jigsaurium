import os
import re
import subprocess
from pathlib import Path


def _parse_semver(version):
    if not version:
        return None
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _read_vendored_version(app):
    version_file = Path(app.root_path) / "static" / "vendor" / "govuk" / "VERSION"
    if not version_file.exists():
        return None
    return version_file.read_text(encoding="utf-8").strip()


def _fetch_latest_version(timeout_seconds=3):
    command = ["npm", "view", "govuk-frontend", "version", "--silent"]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    latest = completed.stdout.strip().splitlines()
    return latest[-1].strip() if latest else None


def check_govuk_version_freshness(app):
    if app.config.get("APP_ENV") != "dev":
        return

    enabled = os.getenv("GOVUK_VERSION_CHECK", "1").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return

    vendored = _read_vendored_version(app)
    if not vendored:
        app.logger.warning(
            "GOV.UK assets are not vendored. Run scripts/update_govuk_assets.bat or ./scripts/update_govuk_assets.sh."
        )
        return

    vendored_tuple = _parse_semver(vendored)
    latest = _fetch_latest_version()
    if not latest:
        app.logger.info("Unable to check latest GOV.UK Frontend version from npm.")
        return

    latest_tuple = _parse_semver(latest)
    if not vendored_tuple or not latest_tuple:
        app.logger.info(
            "GOV.UK Frontend version check skipped due to unparsable version values (vendored=%s, latest=%s).",
            vendored,
            latest,
        )
        return

    if vendored_tuple < latest_tuple:
        app.logger.warning(
            "GOV.UK Frontend is out of date (vendored=%s, latest=%s). Run update script to vendor the latest assets.",
            vendored,
            latest,
        )
