#!/usr/bin/env python3
"""Set the GOV.UK Frontend version in scripts/sbom_extra_components.json and
THIRD_PARTY_NOTICES.md to the one in package.json.

Run after updating the vendored files (scripts/ci_refresh_frontend.sh does). The same versions
are checked by tests/test_sbom_report.py. Files are edited as text so they keep their layout.
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXTRA = ROOT / "scripts" / "sbom_extra_components.json"
NOTICES = ROOT / "THIRD_PARTY_NOTICES.md"
NAME = "govuk-frontend"


def main() -> int:
    new = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["devDependencies"][NAME]
    text = EXTRA.read_text(encoding="utf-8")
    old = next(c["version"] for c in json.loads(text)["components"] if c["name"] == NAME)
    if old == new:
        print(f"SBOM extra components already list {NAME} {new}.")
        return 0
    text, count = re.subn(rf'("name": "{NAME}",\s*"version": ")[^"]+(")', rf"\g<1>{new}\g<2>", text)
    if count != 1:
        raise SystemExit(f"Could not update {NAME} in {EXTRA}")
    EXTRA.write_text(text.replace(f"pkg:npm/{NAME}@{old}", f"pkg:npm/{NAME}@{new}"), encoding="utf-8")
    notices = NOTICES.read_text(encoding="utf-8")
    NOTICES.write_text(notices.replace(f"GOV.UK Frontend {old}", f"GOV.UK Frontend {new}"), encoding="utf-8")
    print(f"SBOM extra components and THIRD_PARTY_NOTICES.md: {NAME} {old} -> {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
