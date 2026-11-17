"""Browser tests for the Progress slot on the guided capture page (issue #95).

A Progress photo is stored with the `In progress` tag: on the new jigsaw when the capture creates
one, otherwise unassigned like a Completed-only capture.
"""

import pytest

from tests.image_fixtures import png_bytes
from tests.test_ui_admin_panel import playwright_sync_api, ui_server  # noqa: F401


def _launch(playwright):
    try:
        return playwright.chromium.launch(headless=True)
    except Exception as error:  # pragma: no cover
        pytest.skip(f"Playwright browser unavailable: {error}")


def _sign_in_to_capture_page(page, base_url):
    page.goto(f"{base_url}/mobile-capture", wait_until="networkidle")
    page.fill("#mobile-capture-login-email", "admin@example.com")
    page.fill("#mobile-capture-login-password", "AdminPassword123!")
    page.click("#mobile-capture-login-form button[type='submit']")
    page.wait_for_selector("#mobile-capture-workflow:not([hidden])")


def _add_photo(page, slot_key, seed):
    page.set_input_files(
        f"[data-slot-file='{slot_key}'][data-slot-source='gallery']",
        {"name": f"{slot_key}.png", "mimeType": "image/png", "buffer": png_bytes(seed)},
    )
    page.wait_for_selector(f"[data-slot-preview='{slot_key}'] img")


def _library_images(page, base_url):
    response = page.request.get(f"{base_url}/api/v1/image-library/images?page=1&page_size=500")
    assert response.ok, response.text()
    return response.json()["data"]


@pytest.mark.functional
@pytest.mark.ui
def test_capture_page_has_six_slots_with_progress_before_completed(ui_server):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        page = browser.new_page()
        _sign_in_to_capture_page(page, ui_server)

        slots = page.eval_on_selector_all(".app-mobile-intake-slot", "nodes => nodes.map(n => n.dataset.slotKey)")
        assert slots == ["box_front", "box_side", "box_back", "in_progress", "completed", "reference"]
        progress = page.locator(".app-mobile-intake-slot[data-slot-key='in_progress']")
        assert progress.locator("h3").inner_text() == "Progress"
        assert progress.locator("[data-slot-action='gallery']").count() == 1
        assert progress.locator("[data-slot-action='camera']").count() == 1
        assert progress.locator("input[data-slot-source='camera'][capture='environment']").count() == 1
        browser.close()


@pytest.mark.functional
@pytest.mark.ui
def test_progress_photo_is_stored_on_the_new_jigsaw(ui_server):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        page = browser.new_page()
        _sign_in_to_capture_page(page, ui_server)

        page.fill("#mobile-intake-title", "Progress Slot Puzzle")
        _add_photo(page, "reference", b"issue95-reference")
        _add_photo(page, "in_progress", b"issue95-progress")
        page.click("#mobile-intake-submit")
        page.wait_for_selector("#mobile-intake-status-text:has-text('Mobile capture complete. Created jigsaw #')")

        images = _library_images(page, ui_server)
        browser.close()

    by_tag = {image["tag"]: image for image in images}
    assert set(by_tag) == {"Reference", "In progress"}, images
    jigsaw_id = by_tag["Reference"]["jigsaw_id"]
    assert jigsaw_id
    assert by_tag["In progress"]["jigsaw_id"] == jigsaw_id


@pytest.mark.functional
@pytest.mark.ui
def test_progress_and_completed_without_box_photos_are_stored_unassigned(ui_server):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        page = browser.new_page()
        _sign_in_to_capture_page(page, ui_server)

        _add_photo(page, "in_progress", b"issue95-progress-only")
        _add_photo(page, "completed", b"issue95-completed-only")
        page.fill("#mobile-intake-comment", "Halfway there")
        page.click("#mobile-intake-submit")
        page.wait_for_selector("#mobile-intake-status-text:has-text('stored as unassigned')")
        status = page.inner_text("#mobile-intake-status-text")

        images = _library_images(page, ui_server)
        browser.close()

    assert status.startswith("In progress and Completed stored as unassigned. Added 2 image(s)"), status
    assert sorted(image["tag"] for image in images) == ["Completed", "In progress"], images
    assert all(not image["jigsaw_id"] for image in images), images
