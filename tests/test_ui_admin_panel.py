from threading import Thread

import pytest
from werkzeug.serving import make_server

from app import create_app
from app.db import Base, get_engine, get_session
from app.models import Role, User, UserRole


playwright_sync_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture()
def ui_server(tmp_path):
    db_path = tmp_path / "ui_smoke.db"

    class UITestConfig:
        APP_ENV = "test"
        SECRET_KEY = "ui-test-secret"
        TESTING = True
        DATABASE_URL = f"sqlite+pysqlite:///{db_path.as_posix()}"
        LOG_LEVEL = "INFO"
        CANONICAL_HOST = "localhost"
        TRUSTED_PROXY_CIDRS = []
        TRUSTED_PROXY_HOPS = None
        SESSION_COOKIE_SECURE = False
        REMEMBER_COOKIE_SECURE = False
        PREFERRED_URL_SCHEME = "http"

    app = create_app(UITestConfig)

    with app.app_context():
        engine = get_engine()
        Base.metadata.create_all(bind=engine)

        db_session = get_session()
        admin_role = Role(name="administrator", description="Administrator")
        borrower_role = Role(name="borrower", description="Borrower")
        db_session.add_all([admin_role, borrower_role])
        db_session.flush()

        admin_user = User(email="admin@example.com", display_name="Admin User", is_active=True)
        admin_user.set_password("AdminPassword123!")
        db_session.add(admin_user)
        db_session.flush()

        db_session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
        db_session.commit()

    server = make_server("127.0.0.1", 0, app)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield base_url
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


@pytest.mark.functional
@pytest.mark.ui
def test_admin_ui_login_and_create_jigsaw(ui_server):
    with playwright_sync_api.sync_playwright() as playwright:
        browser = None
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as error:  # pragma: no cover
            pytest.skip(f"Playwright browser unavailable: {error}")

        page = browser.new_page()
        page.goto(ui_server, wait_until="networkidle")

        assert page.locator("#admin-sections").is_hidden()
        assert page.locator("#sign-in-controls").is_visible()
        assert page.locator("#sign-out-controls").is_hidden()
        assert page.locator("#auth-credentials-wrap").is_visible()

        page.fill("#login-email", "admin@example.com")
        page.fill("#login-password", "AdminPassword123!")
        page.click("#login-form button[type='submit']")

        page.wait_for_selector("text=Signed in successfully.")
        assert page.locator("#admin-sections").is_visible()
        assert page.locator("#sign-in-controls").is_hidden()
        assert page.locator("#sign-out-controls").is_visible()
        assert page.locator("#auth-credentials-wrap").is_hidden()

        page.reload(wait_until="networkidle")
        page.wait_for_selector("text=Signed in as admin@example.com")
        assert page.locator("#admin-sections").is_visible()

        page.fill("#account-username", "Admin Renamed")
        page.click("#account-form button[type='submit']")
        page.wait_for_selector("text=Account updated.")

        page.fill("#account-current-password", "AdminPassword123!")
        page.fill("#account-new-password", "AdminPassword456!")
        page.fill("#account-confirm-password", "AdminPassword456!")
        page.click("#account-form button[type='submit']")
        page.wait_for_selector("text=Account updated.")

        page.fill("#user-email", "ui.user@example.com")
        page.fill("#user-display-name", "UI User")
        page.fill("#user-password", "UiUserPassword123!")
        page.select_option("#user-role", "borrower")
        with page.expect_response("**/api/v1/users") as create_user_response_info:
            page.click("#user-create-form button[type='submit']")

        create_user_response = create_user_response_info.value
        assert create_user_response.status == 201, create_user_response.text()

        page.wait_for_selector("text=User created.")
        page.wait_for_selector("text=ui.user@example.com")

        page.locator("#users-table-body tr", has_text="ui.user@example.com").locator("button[data-user-edit]").click()
        assert page.locator("#user-edit-form").is_visible()
        page.click("#user-edit-cancel")
        assert page.locator("#user-edit-form").is_hidden()

        page.locator("#users-table-body tr", has_text="ui.user@example.com").locator("button[data-user-edit]").click()
        page.fill("#edit-user-display-name", "UI User Edited")
        page.fill("#edit-user-password", "UiUserPassword456!")
        page.click("#user-edit-form button[type='submit']")
        page.wait_for_selector("text=User updated.")
        page.wait_for_selector("text=UI User Edited")

        page.fill("#jigsaw-title", "UI Smoke Puzzle")
        page.fill("#jigsaw-piece-count", "500")
        page.select_option("#jigsaw-status", "available")
        page.click("#jigsaw-create-form button[type='submit']")

        page.wait_for_selector("text=Jigsaw created.")
        page.wait_for_selector("text=UI Smoke Puzzle")

        page.locator("#jigsaws-table-body tr", has_text="UI Smoke Puzzle").locator("button[data-jigsaw-edit]").click()
        assert page.locator("#jigsaw-edit-form").is_visible()
        page.click("#jigsaw-edit-cancel")
        assert page.locator("#jigsaw-edit-form").is_hidden()

        page.locator("#jigsaws-table-body tr", has_text="UI Smoke Puzzle").locator("button[data-jigsaw-edit]").click()
        page.fill("#edit-jigsaw-title", "UI Smoke Puzzle Updated")
        page.fill("#edit-jigsaw-piece-count", "650")
        page.fill("#edit-jigsaw-condition", "excellent")
        page.select_option("#edit-jigsaw-status", "maintenance")
        page.fill("#edit-jigsaw-tags", "ui,updated")
        page.click("#jigsaw-edit-form button[type='submit']")
        page.wait_for_selector("text=Jigsaw updated.")
        page.wait_for_selector("text=UI Smoke Puzzle Updated")
        page.wait_for_selector("#audit-table-body tr")

        page.click("#logout-button")
        page.wait_for_selector("text=Signed out.")
        assert page.locator("#admin-sections").is_hidden()
        assert page.locator("#sign-in-controls").is_visible()
        assert page.locator("#sign-out-controls").is_hidden()
        assert page.locator("#auth-credentials-wrap").is_visible()

        page.fill("#login-email", "admin@example.com")
        page.fill("#login-password", "AdminPassword456!")
        page.click("#login-form button[type='submit']")
        page.wait_for_selector("text=Signed in successfully.")

        browser.close()
