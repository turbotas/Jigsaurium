"""Browser tests for the STFD 2FA hop-up (issue 87): one hop-up, no burst of status messages."""

import time
from html import escape
from threading import Thread
from urllib.parse import urlsplit

import pytest
from flask import request
from werkzeug.serving import make_server

from app import create_app
from tests.migration_utils import upgrade_database_to_head
from tests.test_api_v1_authz import _build_stfd_token

playwright_sync_api = pytest.importorskip("playwright.sync_api")

# Records every text the status box shows, across page loads.
FEEDBACK_LOG_SCRIPT = """
document.addEventListener("DOMContentLoaded", () => {
  const target = document.getElementById("app-feedback-text");
  if (!target || !window.__feedbackLog) return;
  new MutationObserver(() => window.__feedbackLog(target.textContent)).observe(
    target, { childList: true, characterData: true, subtree: true }
  );
});
"""


@pytest.fixture()
def ui_server_fake_stfd(tmp_path):
    """The app with STFD on, plus a stand-in STFD served by the same test server.

    The stand-in already has the password factor (SSO). A hop-up returns a 2FA-verified token
    with the administrator role, unless `hold_step_up` is set, when it stays on its prompt page.
    """
    db_path = tmp_path / "ui_fake_stfd.db"

    class UITestFakeStfdConfig:
        APP_ENV = "test"
        SECRET_KEY = "ui-test-secret-0123456789abcdefghij"
        TESTING = True
        DATABASE_URL = f"sqlite+pysqlite:///{db_path.as_posix()}"
        LOG_LEVEL = "INFO"
        CANONICAL_HOST = "localhost"
        CANONICAL_HOST_ENFORCEMENT = "off"
        TRUSTED_PROXY_CIDRS = []
        TRUSTED_PROXY_HOPS = None
        SESSION_COOKIE_SECURE = False
        REMEMBER_COOKIE_SECURE = False
        PREFERRED_URL_SCHEME = "http"
        STFD_ENABLED = True
        STFD_ALLOW_LOCAL_LOGIN = False
        STFD_APP_UNI = "jigsaurium-test-app-uni"
        STFD_SHARED_KEY = "test-shared-key-0123456789abcdef0123456789abcdef"
        STFD_ASSERT_BASE_URL = "https://stfd.example.test/stfd/assert"
        STFD_REDIRECT_URI = "http://127.0.0.1/"
        STFD_ROLE_UNI_ADMINISTRATOR = "role-uni-admin"
        STFD_ROLE_UNI_MEMBER = "role-uni-member"
        STFD_ROLE_UNI_BORROWER = "role-uni-borrower"

    app = create_app(UITestFakeStfdConfig)
    upgrade_database_to_head(UITestFakeStfdConfig.DATABASE_URL)
    fake = {"visits": [], "hold_step_up": False}

    def fake_stfd_assert(app_uni):
        step_up = request.args.get("step_up") == "1"
        fake["visits"].append("step_up" if step_up else "plain")
        if step_up and fake["hold_step_up"]:
            return "<!doctype html><title>STFD</title><p>Enter your 2FA code</p>"
        state = request.args["state"]
        token = _build_stfd_token(
            sub="stfd-admin-1",
            email="stfd.admin@example.com",
            role_unis=["role-uni-member", "role-uni-admin"] if step_up else ["role-uni-member"],
            step_up_role_unis=["role-uni-admin"],
            elevated=step_up,
            nonce=state,
        )
        target = f"{app.config['FAKE_STFD_APP_BASE']}/#token={token}&state={state}"
        # A meta refresh, because the app's Content-Security-Policy blocks inline scripts.
        return f'<!doctype html><title>STFD</title><meta http-equiv="refresh" content="0;url={escape(target)}">'

    app.add_url_rule("/__fake_stfd/<app_uni>", "fake_stfd_assert", fake_stfd_assert)

    server = make_server("127.0.0.1", 0, app, threaded=True)
    base_url = f"http://127.0.0.1:{server.server_port}"
    app.config["FAKE_STFD_APP_BASE"] = base_url
    app.config["STFD_ASSERT_BASE_URL"] = f"{base_url}/__fake_stfd"
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        yield base_url, fake
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def _open_logged_page(playwright, base_url):
    try:
        browser = playwright.chromium.launch(headless=True)
    except Exception as error:  # pragma: no cover
        pytest.skip(f"Playwright browser unavailable: {error}")
    context = browser.new_context()
    feedback = []
    responses = []
    context.expose_function("__feedbackLog", lambda text: feedback.append(text))
    context.add_init_script(FEEDBACK_LOG_SCRIPT)
    page = context.new_page()
    page.on("response", lambda r: responses.append((r.status, urlsplit(r.url).path)) if "/api/v1/" in r.url else None)
    return browser, page, feedback, responses


@pytest.mark.functional
@pytest.mark.ui
def test_stfd_sign_in_goes_straight_to_one_hop_up(ui_server_fake_stfd):
    base_url, fake = ui_server_fake_stfd
    with playwright_sync_api.sync_playwright() as playwright:
        browser, page, feedback, responses = _open_logged_page(playwright, base_url)
        page.goto(base_url, wait_until="networkidle")
        page.click("#login-open-button")
        page.click("#login-form button[type='submit']")

        page.wait_for_selector("#admin-sections:not([hidden])")
        page.wait_for_load_state("networkidle")
        browser.close()

    # A plain sign-in, then exactly one hop-up: no extra round trips to STFD.
    assert fake["visits"] == ["plain", "step_up"]
    # The held-back admin role is not used before the hop-up, so nothing fails on the way.
    assert [entry for entry in responses if entry[0] == 403] == []
    # One steady status per step, never a flicker of repeated or error messages.
    assert feedback == [
        "Signed in successfully.",
        "Two-factor verification is needed. Redirecting to STFD...",
        "Signed in successfully.",
    ]


@pytest.mark.functional
@pytest.mark.ui
def test_reads_needing_two_factor_start_a_single_hop_up(ui_server_fake_stfd):
    base_url, fake = ui_server_fake_stfd
    fake["hold_step_up"] = True
    with playwright_sync_api.sync_playwright() as playwright:
        browser, page, feedback, responses = _open_logged_page(playwright, base_url)
        page.goto(base_url, wait_until="networkidle")
        page.click("#login-open-button")
        page.click("#login-form button[type='submit']")
        page.wait_for_url("**/__fake_stfd/**")
        page.wait_for_selector("text=Enter your 2FA code")

        # Leave the 2FA prompt and come back: the session is signed in without 2FA, so several
        # admin reads need the hop-up at once. Only one of them may start it.
        visits_before = len(fake["visits"])
        feedback.clear()
        responses.clear()
        page.goto(base_url)
        page.wait_for_url("**/__fake_stfd/**")
        page.wait_for_selector("text=Enter your 2FA code")
        browser.close()

    assert fake["visits"][visits_before:] == ["step_up"]
    assert len([entry for entry in responses if entry[1] == "/api/v1/auth/stfd/start"]) == 1
    assert len([entry for entry in responses if entry[0] == 403]) >= 2
    assert feedback == ["Two-factor verification is needed. Redirecting to STFD..."]
