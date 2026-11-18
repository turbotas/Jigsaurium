"""scripts/sync_dev_venv.py: compare the venv with the dependency lock and sync it (issue #104)."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "sync_dev_venv.py"


@pytest.fixture()
def sync_script():
    spec = importlib.util.spec_from_file_location("sync_dev_venv_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def lock(tmp_path, monkeypatch, sync_script):
    path = tmp_path / "known-good-dev.txt"
    path.write_text(
        "# Auto-generated known-good dependency lock.\n"
        "--extra-index-url https://example.invalid/simple\n"
        "Flask==3.1.3\n"
        "pydantic_core==2.50.4  # trailing comment\n"
        "uvicorn[standard]==0.40.0\n"
        "playwright==1.65.2\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sync_script, "lock_file", lambda profile: path)
    monkeypatch.setattr(sync_script, "REPO_ROOT", tmp_path)
    return path


@pytest.mark.functional
def test_read_lock_keeps_only_pins(sync_script, lock):
    pins = sync_script.read_lock(lock)

    assert pins == {
        "flask": ("Flask", "3.1.3"),
        "pydantic-core": ("pydantic_core", "2.50.4"),
        "uvicorn": ("uvicorn", "0.40.0"),
        "playwright": ("playwright", "1.65.2"),
    }


@pytest.mark.functional
def test_differences_lists_missing_and_other_versions(sync_script, lock):
    installed = {"flask": "3.1.3", "pydantic-core": "2.50.3", "playwright": "1.65.2"}

    found = sync_script.differences(sync_script.read_lock(lock), installed)

    assert found == [("pydantic_core", "2.50.3", "2.50.4"), ("uvicorn", None, "0.40.0")]


@pytest.mark.functional
def test_equivalent_version_spellings_match(sync_script):
    assert sync_script.same_version("2.0", "2.0.0")
    assert not sync_script.same_version("2.0.1", "2.0.0")


@pytest.mark.functional
def test_check_reports_and_never_installs(sync_script, lock, monkeypatch, capsys):
    monkeypatch.setattr(sync_script, "installed_versions", lambda: {"flask": "3.1.2"})
    monkeypatch.setattr(sync_script.subprocess, "run", lambda *a, **k: pytest.fail("--check must not install"))

    assert sync_script.main(["--profile", "dev"]) == 1
    output = capsys.readouterr().out
    assert "4 of 4 locked packages differ" in output
    assert "Flask" in output and "3.1.2 -> 3.1.3" in output
    assert "not installed -> 0.40.0" in output


@pytest.mark.functional
def test_in_line_with_the_lock(sync_script, lock, monkeypatch, capsys):
    monkeypatch.setattr(
        sync_script,
        "installed_versions",
        lambda: {"flask": "3.1.3", "pydantic-core": "2.50.4", "uvicorn": "0.40.0", "playwright": "1.65.2", "pip-audit": "2.9"},
    )

    assert sync_script.main(["--sync"]) == 0
    assert "In line with the lock (4 packages)" in capsys.readouterr().out


def _fake_install(sync_script, monkeypatch, after_install):
    """Record commands; once pip has run, report the venv as `after_install`."""
    commands = []
    state = {"installed": {"flask": "3.1.2", "pydantic-core": "2.50.4", "uvicorn": "0.40.0", "playwright": "1.64.1"}}

    def run(command, **_kwargs):
        commands.append(command)
        if command[1:4] == ["-m", "pip", "install"]:
            state["installed"] = after_install
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(sync_script.subprocess, "run", run)
    monkeypatch.setattr(sync_script, "installed_versions", lambda: dict(state["installed"]))
    return commands


@pytest.mark.functional
def test_sync_installs_the_lock_and_the_playwright_browser(sync_script, lock, monkeypatch, capsys):
    in_line = {"flask": "3.1.3", "pydantic-core": "2.50.4", "uvicorn": "0.40.0", "playwright": "1.65.2"}
    commands = _fake_install(sync_script, monkeypatch, in_line)

    assert sync_script.main(["--sync"]) == 0

    pip_command, browser_command = commands
    assert pip_command[1:4] == ["-m", "pip", "install"]
    assert pip_command[-4:] == ["-r", str(sync_script.requirements_file("dev")), "-c", str(lock)]
    assert browser_command[1:] == ["-m", "playwright", "install", "chromium"]
    assert "Done: in line with the lock" in capsys.readouterr().out


@pytest.mark.functional
def test_sync_reports_what_is_still_different(sync_script, lock, monkeypatch, capsys):
    still_old = {"flask": "3.1.2", "pydantic-core": "2.50.4", "uvicorn": "0.40.0", "playwright": "1.65.2"}
    _fake_install(sync_script, monkeypatch, still_old)

    assert sync_script.main(["--sync"]) == 1
    assert "Still 1 different after installing" in capsys.readouterr().out


@pytest.mark.functional
def test_the_real_lock_files_parse(sync_script):
    for profile in ("dev", "prod"):
        pins = sync_script.read_lock(sync_script.lock_file(profile))
        assert "flask" in pins
