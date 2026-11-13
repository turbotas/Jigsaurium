import subprocess

import pytest

from app.build_info import apply_git_build_info, describe_git_checkout


class _FakeApp:
    def __init__(self, **config):
        self.config = {"APP_VERSION": "0.0.0-dev", "APP_BUILD_SHA": "local", **config}
        self.root_path = "unused"


def _git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "file.txt").write_text("one", encoding="utf-8")
    _git(tmp_path, "add", "file.txt")
    _git(tmp_path, "commit", "-q", "-m", "first")
    _git(tmp_path, "tag", "v1.2.3")
    return tmp_path


@pytest.mark.functional
def test_checkout_on_release_tag_shows_that_version(repo):
    app = _FakeApp()
    apply_git_build_info(app, repo)

    assert app.config["APP_VERSION"] == "v1.2.3"
    assert len(app.config["APP_BUILD_SHA"]) == 40


@pytest.mark.functional
def test_checkout_ahead_of_tag_or_with_local_changes_says_so(repo):
    (repo / "file.txt").write_text("two", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "second")
    assert describe_git_checkout(repo)["version"].startswith("v1.2.3-1-g")

    (repo / "file.txt").write_text("three", encoding="utf-8")
    assert describe_git_checkout(repo)["version"].endswith("-dirty")


@pytest.mark.functional
def test_supplied_version_and_sha_are_kept(repo):
    app = _FakeApp(APP_VERSION="v9.9.9", APP_BUILD_SHA="abc123")
    apply_git_build_info(app, repo)

    assert app.config["APP_VERSION"] == "v9.9.9"
    assert app.config["APP_BUILD_SHA"] == "abc123"


@pytest.mark.functional
def test_no_git_checkout_keeps_defaults(tmp_path):
    app = _FakeApp()
    apply_git_build_info(app, tmp_path)

    assert app.config["APP_VERSION"] == "0.0.0-dev"
    assert app.config["APP_BUILD_SHA"] == "local"
