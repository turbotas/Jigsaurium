#!/usr/bin/env python
"""Complete a scanned container-image SBOM and write a report people can read (issue #107).

The prod promotion workflow scans the image it has just promoted with Syft (CycloneDX JSON). Syft
finds what package managers installed: Debian packages and Python packages. This script adds what
they did not install (listed in scripts/sbom_extra_components.json: GOV.UK Frontend, the Lexend
font, the CLIP model) and Jigsaurium itself, then writes:

- the completed CycloneDX JSON, for tools (for example `trivy sbom <file>`), and
- a Markdown report: every component with its version and declared licence, a licence summary,
  and the components the scanner found no licence for.

Standard library only, so it runs on a CI runner's own Python.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EXTRA_COMPONENTS_FILE = Path(__file__).resolve().parent / "sbom_extra_components.json"
APP_LICENCE = "AGPL-3.0-only"
NO_LICENCE = "(not found)"

KIND_BY_PURL_TYPE = {
    "deb": "Debian package",
    "pypi": "Python package",
    "npm": "Static files (from npm)",
    "huggingface": "Machine-learning model",
    "github": "Application",
    # Syft names software it recognises from files alone (the Python interpreter) pkg:generic.
    "generic": "Other software (found in files)",
}
KIND_ORDER = [
    "Application",
    "Operating system",
    "Debian package",
    "Python package",
    "Other software (found in files)",
    "Static files (from npm)",
    "Machine-learning model",
]


def load_extra_components(path: Path = EXTRA_COMPONENTS_FILE) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["components"]


def app_component(version: str, repository: str) -> dict:
    return {
        "type": "application",
        "name": "jigsaurium",
        "version": version,
        "description": "Jigsaurium itself: the code in /app",
        "purl": f"pkg:github/{repository.lower()}@{version}",
        "licenses": [{"license": {"id": APP_LICENCE}}],
        "externalReferences": [{"type": "vcs", "url": f"https://github.com/{repository}"}],
    }


def complete_sbom(sbom: dict, extras: list[dict], app: dict) -> dict:
    """Add Jigsaurium and the extra components, skipping any the scan already found (same purl)."""
    components = sbom.setdefault("components", [])
    known = {component.get("purl") for component in components if component.get("purl")}
    for component in [app, *extras]:
        if component["purl"] in known:
            continue
        added = {key: value for key, value in component.items() if not key.startswith("_")}
        added.setdefault("bom-ref", component["purl"])
        components.append(added)
        known.add(component["purl"])
    return sbom


def licences_of(component: dict) -> list[str]:
    found = []
    for entry in component.get("licenses") or []:
        if "expression" in entry:
            found.append(entry["expression"])
        else:
            licence = entry.get("license") or {}
            name = licence.get("id") or licence.get("name")
            if name:
                found.append(name)
    return sorted(set(found))


def kind_of(component: dict) -> str:
    if component.get("type") == "operating-system":
        return "Operating system"
    purl = component.get("purl") or ""
    if purl.startswith("pkg:"):
        return KIND_BY_PURL_TYPE.get(purl[4:].split("/", 1)[0], purl[4:].split("/", 1)[0])
    return component.get("type") or "unknown"


def report_rows(sbom: dict) -> list[dict]:
    """One row per distinct component; files and components without a purl are left out."""
    rows = {}
    for component in sbom.get("components") or []:
        if component.get("type") != "operating-system" and not component.get("purl"):
            continue
        row = {
            "kind": kind_of(component),
            "name": component.get("name", ""),
            "version": component.get("version", ""),
            "licences": licences_of(component),
        }
        key = (row["kind"], row["name"].lower(), row["version"])
        if key in rows:
            rows[key]["licences"] = sorted(set(rows[key]["licences"]) | set(row["licences"]))
        else:
            rows[key] = row

    def order(row):
        kind_rank = KIND_ORDER.index(row["kind"]) if row["kind"] in KIND_ORDER else len(KIND_ORDER)
        return (kind_rank, row["kind"], row["name"].lower(), row["version"])

    return sorted(rows.values(), key=order)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_report(
    rows: list[dict], *, image: str, digest: str, version: str, repository: str, scanner: str, generated: str
) -> str:
    kinds = Counter(row["kind"] for row in rows)
    licence_counts = Counter(licence for row in rows for licence in (row["licences"] or [NO_LICENCE]))
    unlicensed = [row for row in rows if not row["licences"]]

    lines = [
        f"# Jigsaurium {version}: software bill of materials",
        "",
        f"- Image: `{image}@{digest}`",
        f"- Generated: {generated}, when this image was promoted to prod",
        f"- Scanner: {scanner}, plus the components listed in `scripts/sbom_extra_components.json`",
        "",
        "This covers the Jigsaurium container image only. The database, the reverse proxy and the "
        "host it runs on are separate and not listed. Licences are as each package declares them, "
        f"not a legal review; [`THIRD_PARTY_NOTICES.md`](https://github.com/{repository}/blob/{version}/THIRD_PARTY_NOTICES.md) "
        "is the reviewed licence index. The machine-readable SBOM (CycloneDX JSON) is attached beside "
        "this report.",
        "",
        "## Summary",
        "",
        "| What | Count |",
        "| --- | --- |",
    ]
    lines += [f"| {_cell(kind)} | {kinds[kind]} |" for kind in sorted(kinds, key=lambda k: (KIND_ORDER.index(k) if k in KIND_ORDER else 99, k))]
    lines += [f"| **Total** | **{len(rows)}** |", "", "## Licences", "", "| Licence | Components |", "| --- | --- |"]
    lines += [f"| {_cell(licence)} | {count} |" for licence, count in sorted(licence_counts.items(), key=lambda item: (-item[1], item[0].lower()))]
    lines += [
        "",
        "## Components with no licence found",
        "",
        "The scanner found no licence for these. That does not mean they have none: some Python "
        "packages state theirs only as a PyPI classifier or in a licence file, which the scanner "
        "does not read, and the operating system entry stands for the Debian packages listed "
        "separately. Check each one by hand.",
        "",
    ]
    if unlicensed:
        lines += [f"- {_cell(row['name'])} {_cell(row['version'])} ({_cell(row['kind'])})" for row in unlicensed]
    else:
        lines.append("None.")
    lines += ["", "## All components", "", "| Type | Name | Version | Licence |", "| --- | --- | --- | --- |"]
    lines += [
        f"| {_cell(row['kind'])} | {_cell(row['name'])} | {_cell(row['version'])} | {_cell('; '.join(row['licences']) or NO_LICENCE)} |"
        for row in rows
    ]
    return "\n".join(lines) + "\n"


def scanner_name(sbom: dict) -> str:
    tools = (sbom.get("metadata") or {}).get("tools") or {}
    entries = tools.get("components", []) if isinstance(tools, dict) else tools
    names = [" ".join(part for part in (tool.get("name"), tool.get("version")) if part) for tool in entries]
    return ", ".join(name for name in names if name) or "unknown scanner"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sbom", required=True, type=Path, help="CycloneDX JSON from the image scan")
    parser.add_argument("--image", required=True, help="image name, for example ghcr.io/owner/jigsaurium")
    parser.add_argument("--digest", required=True, help="the promoted image digest (sha256:...)")
    parser.add_argument("--version", required=True, help="the image's release version (vX.Y.Z)")
    parser.add_argument("--repository", required=True, help="GitHub owner/name, for Jigsaurium's own entry")
    parser.add_argument("--extra", type=Path, default=EXTRA_COMPONENTS_FILE)
    parser.add_argument("--out-sbom", required=True, type=Path)
    parser.add_argument("--out-report", required=True, type=Path)
    args = parser.parse_args(argv)

    sbom = json.loads(args.sbom.read_text(encoding="utf-8"))
    scanner = scanner_name(sbom)
    complete_sbom(sbom, load_extra_components(args.extra), app_component(args.version, args.repository))
    args.out_sbom.write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report = render_report(
        report_rows(sbom),
        image=args.image,
        digest=args.digest,
        version=args.version,
        repository=args.repository,
        scanner=scanner,
        generated=generated,
    )
    args.out_report.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
