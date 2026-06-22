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
        db_session.add(admin_role)
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

        page.fill("#login-email", "admin@example.com")
        page.fill("#login-password", "AdminPassword123!")
        page.click("#login-form button[type='submit']")

        page.wait_for_selector("text=Signed in successfully.")
        assert page.locator("#admin-sections").is_visible()

        page.fill("#jigsaw-title", "UI Smoke Puzzle")
        page.fill("#jigsaw-piece-count", "500")
        page.select_option("#jigsaw-status", "available")
        page.click("#jigsaw-create-form button[type='submit']")

        page.wait_for_selector("text=Jigsaw created.")
        page.wait_for_selector("text=UI Smoke Puzzle")

        browser.close()
