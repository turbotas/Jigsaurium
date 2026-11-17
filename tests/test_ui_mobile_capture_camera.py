"""Browser tests for "Capture with camera" on the guided capture page (issue #10).

Computers get a live webcam preview; phones and tablets keep their own camera app (the `capture`
file input); and a camera that cannot be used is explained instead of silently showing a picker.
"""

import pytest

from tests.test_ui_admin_panel import playwright_sync_api, ui_server  # noqa: F401

FAKE_CAMERA_ARGS = ["--use-fake-device-for-media-stream"]


def _sign_in_to_capture_page(page, base_url):
    page.goto(f"{base_url}/mobile-capture", wait_until="networkidle")
    page.fill("#mobile-capture-login-email", "admin@example.com")
    page.fill("#mobile-capture-login-password", "AdminPassword123!")
    page.click("#mobile-capture-login-form button[type='submit']")
    page.wait_for_selector("#mobile-capture-workflow:not([hidden])")


def _launch(playwright, args):
    try:
        return playwright.chromium.launch(headless=True, args=args)
    except Exception as error:  # pragma: no cover
        pytest.skip(f"Playwright browser unavailable: {error}")


CAMERA_BUTTON = "[data-slot-key='box_front'][data-slot-action='camera']"


@pytest.mark.functional
@pytest.mark.ui
def test_desktop_camera_button_opens_a_live_webcam_and_captures_a_photo(ui_server):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright, FAKE_CAMERA_ARGS + ["--use-fake-ui-for-media-stream"])
        context = browser.new_context(permissions=["camera"])
        page = context.new_page()
        file_choosers = []
        page.on("filechooser", lambda chooser: file_choosers.append(chooser))
        _sign_in_to_capture_page(page, ui_server)

        page.click(CAMERA_BUTTON)
        page.wait_for_selector(".app-mobile-camera-capture:not([hidden])")
        page.wait_for_function("document.querySelector('.app-mobile-camera-capture__video').videoWidth > 0")
        page.click(".app-mobile-camera-capture button:has-text('Capture photo')")

        page.wait_for_selector(".app-mobile-camera-capture", state="hidden")
        preview = page.locator("[data-slot-preview='box_front']")
        assert "No photo selected." not in preview.inner_text()
        assert file_choosers == []
        browser.close()


@pytest.mark.functional
@pytest.mark.ui
@pytest.mark.parametrize(
    ("error_name", "expected_message"),
    [
        ("NotAllowedError", "Camera access is blocked."),
        ("NotFoundError", "No camera was found."),
        ("NotReadableError", "The camera could not be started."),
        ("NotSupportedError", "This browser cannot use a camera here."),
    ],
)
def test_desktop_camera_failure_is_explained_not_replaced_by_a_file_picker(
    ui_server, error_name, expected_message  # noqa: F811
):
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright, [])
        context = browser.new_context()
        # The browser's answer when the camera is refused, missing or busy.
        context.add_init_script(
            "navigator.mediaDevices.getUserMedia = () => "
            f"Promise.reject(new DOMException('Simulated', '{error_name}'));"
        )
        page = context.new_page()
        file_choosers = []
        page.on("filechooser", lambda chooser: file_choosers.append(chooser))
        _sign_in_to_capture_page(page, ui_server)

        page.click(CAMERA_BUTTON)

        page.wait_for_selector("#mobile-intake-status-text:has-text('camera')")
        status = page.inner_text("#mobile-intake-status-text")
        assert status.startswith(expected_message), status
        assert "Choose file from gallery" in status
        assert page.locator(".app-mobile-camera-capture:not([hidden])").count() == 0
        assert file_choosers == []
        browser.close()


@pytest.mark.functional
@pytest.mark.ui
@pytest.mark.parametrize(
    ("action", "expects_capture_attribute"),
    [("camera", True), ("gallery", False)],
)
def test_touch_devices_keep_the_native_camera_and_gallery_buttons(ui_server, action, expects_capture_attribute):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright, FAKE_CAMERA_ARGS + ["--use-fake-ui-for-media-stream"])
        context = browser.new_context(
            permissions=["camera"], has_touch=True, is_mobile=True, viewport={"width": 390, "height": 844}
        )
        page = context.new_page()
        _sign_in_to_capture_page(page, ui_server)
        assert page.evaluate("matchMedia('(pointer: coarse)').matches")

        with page.expect_file_chooser() as chooser_info:
            page.click(f"[data-slot-key='box_front'][data-slot-action='{action}']")
        chooser = chooser_info.value

        has_capture = chooser.element.get_attribute("capture") is not None
        assert has_capture is expects_capture_attribute
        assert page.locator(".app-mobile-camera-capture:not([hidden])").count() == 0
        browser.close()
