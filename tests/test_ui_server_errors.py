"""Browser tests: server and network failures read as plain language, never raw HTML (issue #93)."""

import pytest

from tests.test_ui_admin_panel import playwright_sync_api, ui_server  # noqa: F401

# What the reverse proxy (OpenResty / Nginx Proxy Manager) sends when the app is down.
PROXY_504_PAGE = (
    "<html>\r\n<head><title>504 Gateway Time-out</title></head>\r\n<body>\r\n"
    "<center><h1>504 Gateway Time-out</h1></center>\r\n<hr><center>openresty</center>\r\n"
    "</body>\r\n</html>\r\n<!-- a padding to disable MSIE and Chrome friendly error page -->\r\n"
)


def _launch(playwright):
    try:
        return playwright.chromium.launch(headless=True)
    except Exception as error:  # pragma: no cover
        pytest.skip(f"Playwright browser unavailable: {error}")


def _sign_in(page, base_url):
    page.goto(base_url, wait_until="networkidle")
    page.click("#login-open-button")
    page.fill("#login-email", "admin@example.com")
    page.fill("#login-password", "AdminPassword123!")
    page.click("#login-form button[type='submit']")
    page.wait_for_selector("text=Signed in successfully.")


def _assert_no_markup(text):
    for fragment in ("<html", "<head", "<center", "openresty", "padding to disable"):
        assert fragment not in text, text


@pytest.mark.functional
@pytest.mark.ui
def test_spa_shows_a_plain_message_for_a_proxy_504(ui_server):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        page = browser.new_page()
        console = []
        page.on("console", lambda message: console.append(message.text))
        _sign_in(page, ui_server)

        page.route(
            "**/api/v1/jigsaws",
            lambda route: route.fulfill(status=504, content_type="text/html", body=PROXY_504_PAGE),
        )
        page.reload(wait_until="networkidle")
        page.wait_for_selector("#app-feedback-text:has-text('error 504')")

        message = page.inner_text("#app-feedback-text")
        _assert_no_markup(message)
        assert "not responding right now (error 504)" in message
        assert "try again" in message
        # The raw response is kept for diagnosis in the browser console.
        assert any("HTTP 504" in line and "openresty" in line for line in console), console
        browser.close()


@pytest.mark.functional
@pytest.mark.ui
def test_spa_explains_an_unreachable_server(ui_server):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        page = browser.new_page()
        _sign_in(page, ui_server)

        page.route("**/api/v1/jigsaws", lambda route: route.abort("connectionrefused"))
        page.reload(wait_until="networkidle")
        page.wait_for_selector("#app-feedback-text:has-text('Cannot reach')")

        message = page.inner_text("#app-feedback-text")
        assert message.startswith("Cannot reach the Jigsaurium server."), message
        assert "Failed to fetch" not in message
        browser.close()


@pytest.mark.functional
@pytest.mark.ui
def test_spa_keeps_api_error_messages_as_they_are(ui_server):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        page = browser.new_page()
        page.goto(ui_server, wait_until="networkidle")
        page.click("#login-open-button")
        page.fill("#login-email", "admin@example.com")
        page.fill("#login-password", "wrong-password")
        page.click("#login-form button[type='submit']")

        page.wait_for_selector("#app-feedback:not([hidden])")
        message = page.inner_text("#app-feedback-text")
        assert "error 4" not in message, message
        assert "Cannot reach" not in message, message
        browser.close()


@pytest.mark.functional
@pytest.mark.ui
@pytest.mark.parametrize(
    ("respond", "expected"),
    [
        (lambda route: route.fulfill(status=504, content_type="text/html", body=PROXY_504_PAGE), "error 504"),
        (lambda route: route.abort("connectionrefused"), "Cannot reach the Jigsaurium server."),
    ],
    ids=["proxy-504", "unreachable"],
)
def test_capture_page_sign_in_failures_read_plainly(ui_server, respond, expected):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        page = browser.new_page()
        page.goto(f"{ui_server}/mobile-capture", wait_until="networkidle")
        page.route("**/api/v1/auth/login", respond)
        page.fill("#mobile-capture-login-email", "admin@example.com")
        page.fill("#mobile-capture-login-password", "AdminPassword123!")
        page.click("#mobile-capture-login-form button[type='submit']")

        page.wait_for_selector(f"#mobile-intake-status-text:has-text('{expected}')")
        message = page.inner_text("#mobile-intake-status-text")
        _assert_no_markup(message)
        assert "Failed to fetch" not in message
        browser.close()
