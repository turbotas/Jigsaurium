"""scripts/report_newer_releases.py: newer PyPI releases and how each would arrive (follow-up to #104)."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


@pytest.fixture()
def report(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("report_newer_releases_under_test", SCRIPTS_DIR / "report_newer_releases.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DIRECT = {
    "sqlalchemy": ("requirements/base.txt", "<3.0,>=2.1.8"),
    "pyjwt": ("requirements/base.txt", "<3.0,>=2.15.1"),
}
LOCKED = {"sqlalchemy", "pyjwt", "mpmath"}


@pytest.mark.functional
@pytest.mark.parametrize(
    ("name", "latest", "expected"),
    [
        ("SQLAlchemy", "2.1.9", "weekly refresh"),
        ("PyJWT", "3.0.0", "outside requirements/base.txt range <3.0,>=2.15.1: needs a manual change"),
        ("mpmath", "1.4.1", "weekly refresh, if what needs it allows"),
        ("pip-audit", "2.10.0", "not in the lock (local tool)"),
    ],
    ids=["direct-in-range", "direct-new-major", "indirect", "local-tool"],
)
def test_note_says_how_the_release_would_arrive(report, name, latest, expected):
    assert report.note_for(name, latest, LOCKED, DIRECT) == expected


@pytest.mark.functional
def test_app_dependencies_come_before_local_tools(report):
    packages = [
        {"name": "pyee", "version": "14.0.0", "latest_version": "16.1.0"},
        {"name": "SQLAlchemy", "version": "2.1.8", "latest_version": "2.1.9"},
        {"name": "mpmath", "version": "1.3.0", "latest_version": "1.4.1"},
    ]

    rows = report.build_rows(packages, LOCKED, DIRECT)

    assert [row[0] for row in rows] == ["mpmath", "SQLAlchemy", "pyee"]


@pytest.mark.functional
def test_report_prints_the_table(report, monkeypatch, capsys):
    outdated = [{"name": "SQLAlchemy", "version": "2.1.8", "latest_version": "2.1.9"}]
    monkeypatch.setattr(
        report.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=json.dumps(outdated))
    )

    assert report.main([]) == 0
    output = capsys.readouterr().out
    assert "How it arrives" in output
    assert "SQLAlchemy" in output and "2.1.9" in output and "weekly refresh" in output


@pytest.mark.functional
@pytest.mark.parametrize(
    ("returncode", "stdout", "expected"),
    [(1, "", "Could not check PyPI"), (0, "[]", "every installed package is on its latest release")],
    ids=["offline", "nothing-newer"],
)
def test_report_never_fails_the_launcher(report, monkeypatch, capsys, returncode, stdout, expected):
    monkeypatch.setattr(report.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=returncode, stdout=stdout))

    assert report.main([]) == 0
    assert expected in capsys.readouterr().out


@pytest.mark.functional
def test_real_requirement_files_parse(report):
    direct = report.read_direct_requirements("dev")

    assert direct["flask"][0] == "requirements/base.txt"
    assert direct["playwright"][0] == "requirements/dev.txt"
    assert "torch" in direct
