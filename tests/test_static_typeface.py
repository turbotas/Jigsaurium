"""Jigsaurium's typeface (issue 85): Lexend, self-hosted, and no GOV.UK-only GDS Transport."""

import re
from pathlib import Path

import pytest

STATIC_ROOT = Path(__file__).resolve().parents[1] / "app" / "static"
LEXEND_FILES = [
    f"lexend-{subset}-{weight}-normal.{extension}"
    for subset in ("latin", "latin-ext")
    for weight in (400, 700)
    for extension in ("woff2", "woff")
]


@pytest.mark.functional
def test_compiled_govuk_css_uses_lexend_and_no_gds_transport():
    css = (STATIC_ROOT / "vendor" / "govuk" / "govuk-frontend.min.css").read_text(encoding="utf-8")

    assert "GDS Transport" not in css
    assert '"Lexend",arial,sans-serif' in css
    # GOV.UK's images are not shipped. The only one its CSS still names is the crown crest of the
    # footer copyright logo, a component no Jigsaurium template uses.
    assert set(re.findall(r"url\(\"?([^\")]+)\"?\)", css)) == {"/static/vendor/govuk/assets/images/govuk-crest.svg"}
    templates = Path(__file__).resolve().parents[1] / "app" / "templates"
    for template in templates.glob("*.html"):
        assert "govuk-footer" not in template.read_text(encoding="utf-8"), template.name


@pytest.mark.functional
def test_govuk_branding_assets_are_not_vendored():
    # GDS Transport and the crown crest / GOV.UK icons are GOV.UK branding (issues #85 and #89).
    assert not (STATIC_ROOT / "vendor" / "govuk" / "assets").exists()


@pytest.mark.functional
def test_custom_styles_use_the_app_font_variable():
    css = (STATIC_ROOT / "css" / "styles.css").read_text(encoding="utf-8")

    assert "GDS Transport" not in css
    assert '--app-font-family: "Lexend", arial, sans-serif;' in css
    for match in re.findall(r'url\("\.\./fonts/lexend/([^"]+)"\)', css):
        assert match in LEXEND_FILES


@pytest.mark.functional
def test_lexend_fonts_and_licence_are_served(client):
    for file_name in LEXEND_FILES:
        response = client.get(f"/static/fonts/lexend/{file_name}")
        assert response.status_code == 200, file_name
        assert response.data, file_name
        assert response.mimetype == ("font/woff2" if file_name.endswith(".woff2") else "font/woff"), file_name

    licence = client.get("/static/fonts/lexend/OFL.txt")
    assert licence.status_code == 200
    text = licence.get_data(as_text=True)
    assert "The Lexend Project Authors" in text
    assert "SIL Open Font License, Version 1.1" in text
