"""The licence index (THIRD_PARTY_NOTICES.md) and the licence texts it points to (issue #89)."""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX = REPO_ROOT / "THIRD_PARTY_NOTICES.md"

# Every licence text committed beside shipped third-party files. Adding one means listing it here
# and linking it from the index.
SHIPPED_LICENCE_FILES = {
    "app/static/fonts/lexend/OFL.txt": ["The Lexend Project Authors", "SIL Open Font License, Version 1.1"],
    "app/static/vendor/govuk/LICENSE.txt": ["The MIT License", "Crown Copyright (Government Digital Service)"],
}


def _local_links(markdown):
    links = re.findall(r"\]\(([^)]+)\)", markdown)
    return [link for link in links if not re.match(r"^[a-z]+:", link) and not link.startswith("#")]


@pytest.mark.functional
def test_every_local_link_in_the_licence_index_exists():
    links = _local_links(INDEX.read_text(encoding="utf-8"))

    assert links, "the index should link to the licence files"
    for link in links:
        assert (REPO_ROOT / link).is_file(), link


@pytest.mark.functional
@pytest.mark.parametrize("relative_path", sorted(SHIPPED_LICENCE_FILES))
def test_shipped_licence_texts_exist_and_are_indexed(relative_path):
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    for expected in SHIPPED_LICENCE_FILES[relative_path]:
        assert expected in text, (relative_path, expected)

    assert relative_path in _local_links(INDEX.read_text(encoding="utf-8"))


@pytest.mark.functional
def test_no_unindexed_licence_files_under_static():
    found = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "app" / "static").rglob("*")
        if path.is_file() and re.match(r"(?i)^(licen[cs]e|copying|notice|ofl)\b", path.name)
    }

    assert found == set(SHIPPED_LICENCE_FILES)


@pytest.mark.functional
def test_project_licence_and_index_ship_in_the_container_image():
    allowlist = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    for required in ("!LICENSE", "!THIRD_PARTY_NOTICES.md", "!app/"):
        assert required in allowlist, required


@pytest.mark.functional
def test_shipped_licence_texts_are_served(client):
    for relative_path in SHIPPED_LICENCE_FILES:
        response = client.get("/" + relative_path.removeprefix("app/"))
        assert response.status_code == 200, relative_path
