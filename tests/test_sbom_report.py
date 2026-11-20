"""scripts/sbom_report.py: the SBOM and report attached to each prod release (issue #107)."""

import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


@pytest.fixture()
def sbom_report():
    spec = importlib.util.spec_from_file_location("sbom_report_under_test", SCRIPTS_DIR / "sbom_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scanned_sbom():
    """The shape Syft writes for this image: an OS entry, Debian and Python packages, and files."""
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "metadata": {"tools": {"components": [{"type": "application", "name": "syft", "version": "1.56.0"}]}},
        "components": [
            {"type": "operating-system", "name": "debian", "version": "13"},
            {
                "type": "library",
                "name": "libc6",
                "version": "2.41-12",
                "purl": "pkg:deb/debian/libc6@2.41-12?arch=amd64",
                "licenses": [{"license": {"id": "GPL-2.0-only"}}, {"license": {"id": "LGPL-2.1-only"}}],
            },
            {
                "type": "library",
                "name": "Flask",
                "version": "3.1.2",
                "purl": "pkg:pypi/flask@3.1.2",
                "licenses": [{"expression": "BSD-3-Clause"}],
            },
            {"type": "library", "name": "mystery", "version": "1.0", "purl": "pkg:pypi/mystery@1.0"},
            {"type": "application", "name": "python", "version": "3.12.16", "purl": "pkg:generic/python@3.12.16"},
            {"type": "file", "name": "/usr/lib/x.so"},
        ],
    }


def _extras(sbom_report):
    return sbom_report.load_extra_components()


@pytest.mark.functional
def test_complete_sbom_adds_jigsaurium_and_the_extra_components(sbom_report):
    app = sbom_report.app_component("v1.2.3", "Owner/Jigsaurium")
    sbom = sbom_report.complete_sbom(_scanned_sbom(), _extras(sbom_report), app)

    purls = [component.get("purl") for component in sbom["components"]]
    assert "pkg:github/owner/jigsaurium@v1.2.3" in purls
    assert _extra(sbom_report, "pkg:npm/govuk-frontend@")["purl"] in purls
    assert any(purl and purl.startswith("pkg:huggingface/openai/clip-vit-base-patch32@") for purl in purls)
    added = [component for component in sbom["components"] if component.get("purl") == "pkg:github/owner/jigsaurium@v1.2.3"]
    assert added[0]["licenses"] == [{"license": {"id": "AGPL-3.0-only"}}]
    assert added[0]["bom-ref"] == "pkg:github/owner/jigsaurium@v1.2.3"


@pytest.mark.functional
def test_complete_sbom_does_not_duplicate_what_the_scan_found(sbom_report):
    scanned = _scanned_sbom()
    govuk = _extra(sbom_report, "pkg:npm/govuk-frontend@")
    scanned["components"].append({"type": "library", "name": "govuk-frontend", "version": govuk["version"], "purl": govuk["purl"]})
    sbom = sbom_report.complete_sbom(scanned, _extras(sbom_report), sbom_report.app_component("v1", "o/r"))

    assert [c.get("purl") for c in sbom["components"]].count(govuk["purl"]) == 1


@pytest.mark.functional
def test_report_lists_every_component_with_its_licence(sbom_report):
    sbom = sbom_report.complete_sbom(_scanned_sbom(), _extras(sbom_report), sbom_report.app_component("v1.2.3", "owner/jigsaurium"))
    rows = sbom_report.report_rows(sbom)
    report = sbom_report.render_report(
        rows,
        image="ghcr.io/owner/jigsaurium",
        digest="sha256:abc",
        version="v1.2.3",
        repository="owner/jigsaurium",
        scanner=sbom_report.scanner_name(sbom),
        generated="2026-11-19 10:00 UTC",
    )

    assert "`ghcr.io/owner/jigsaurium@sha256:abc`" in report
    assert "syft 1.56.0" in report
    assert "| Debian package | libc6 | 2.41-12 | GPL-2.0-only; LGPL-2.1-only |" in report
    assert "| Python package | Flask | 3.1.2 | BSD-3-Clause |" in report
    assert "| Application | jigsaurium | v1.2.3 | AGPL-3.0-only |" in report
    assert "| Operating system | debian | 13 | (not found) |" in report
    assert "| Other software (found in files) | python | 3.12.16 | (not found) |" in report
    assert "/usr/lib/x.so" not in report  # files are in the JSON, not the report
    assert "https://github.com/owner/jigsaurium/blob/v1.2.3/THIRD_PARTY_NOTICES.md" in report

    no_licence = report.split("## Components with no licence found")[1].split("## All components")[0]
    assert "mystery 1.0 (Python package)" in no_licence
    assert "openai/clip-vit-base-patch32" in no_licence
    assert "Flask" not in no_licence
    assert "| **Total** | **9** |" in report


@pytest.mark.functional
def test_report_rows_merge_duplicates_and_escape_pipes(sbom_report):
    sbom = {
        "components": [
            {"type": "library", "name": "a", "version": "1", "purl": "pkg:pypi/a@1", "licenses": [{"license": {"name": "X | Y"}}]},
            {"type": "library", "name": "A", "version": "1", "purl": "pkg:pypi/a@1?x=1", "licenses": [{"license": {"id": "MIT"}}]},
        ]
    }
    rows = sbom_report.report_rows(sbom)

    assert len(rows) == 1
    assert rows[0]["licences"] == ["MIT", "X | Y"]
    report = sbom_report.render_report(rows, image="i", digest="d", version="v", repository="o/r", scanner="s", generated="g")
    assert "MIT; X \\| Y" in report


@pytest.mark.functional
def test_main_writes_both_files(sbom_report, tmp_path):
    scanned = tmp_path / "scan.cdx.json"
    scanned.write_text(json.dumps(_scanned_sbom()), encoding="utf-8")
    out_sbom, out_report = tmp_path / "out.cdx.json", tmp_path / "out.md"

    code = sbom_report.main(
        [
            "--sbom", str(scanned), "--image", "ghcr.io/o/jigsaurium", "--digest", "sha256:abc",
            "--version", "v1.2.3", "--repository", "o/jigsaurium",
            "--out-sbom", str(out_sbom), "--out-report", str(out_report),
        ]
    )  # fmt: skip

    assert code == 0
    assert json.loads(out_sbom.read_text(encoding="utf-8"))["bomFormat"] == "CycloneDX"
    assert out_report.read_text(encoding="utf-8").startswith("# Jigsaurium v1.2.3: software bill of materials")


# The extra components file is kept by hand, so check it against where each version really comes from.


def _extra(sbom_report, purl_prefix):
    matches = [c for c in _extras(sbom_report) if c["purl"].startswith(purl_prefix)]
    assert len(matches) == 1, purl_prefix
    return matches[0]


@pytest.mark.functional
def test_extra_npm_components_match_package_json(sbom_report):
    dependencies = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))["devDependencies"]

    assert _extra(sbom_report, "pkg:npm/govuk-frontend@")["version"] == dependencies["govuk-frontend"]
    assert _extra(sbom_report, "pkg:npm/%40fontsource/lexend@")["version"] == dependencies["@fontsource/lexend"]


@pytest.mark.functional
def test_extra_model_matches_the_dockerfile(sbom_report):
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    name = re.search(r"^ARG IMAGE_EMBEDDING_MODEL_NAME=(\S+)$", dockerfile, re.M).group(1)
    revision = re.search(r"^ARG IMAGE_EMBEDDING_MODEL_REVISION=(\S+)$", dockerfile, re.M).group(1)

    model = _extra(sbom_report, "pkg:huggingface/")
    assert (model["name"], model["version"]) == (name, revision)
    assert model["purl"] == f"pkg:huggingface/{name}@{revision}"


@pytest.mark.functional
def test_extra_components_are_in_the_licence_index(sbom_report):
    notices = (REPO_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    assert f"GOV.UK Frontend {_extra(sbom_report, 'pkg:npm/govuk-frontend@')['version']}" in notices
    assert "Lexend typeface" in notices
    model = _extra(sbom_report, "pkg:huggingface/")
    assert model["name"] in notices and model["version"] in notices
