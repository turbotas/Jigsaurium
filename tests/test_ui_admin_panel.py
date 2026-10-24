from threading import Thread

import pytest
from werkzeug.serving import make_server

from app import create_app
from app.db import get_session
from app.models import Role, User, UserRole
from tests.migration_utils import upgrade_database_to_head


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
    upgrade_database_to_head(UITestConfig.DATABASE_URL)

    with app.app_context():
        db_session = get_session()
        admin_role = db_session.query(Role).filter_by(name="administrator").one()

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
        page.wait_for_selector("#sign-out-controls:not([hidden])")
        assert "Signed in as admin@example.com" in (page.locator("#session-summary").text_content() or "")
        assert page.locator("#admin-sections").is_visible()
        page.click("#account-nav-button")
        page.wait_for_selector("#account-section:not([hidden])")

        page.fill("#account-username", "Admin Renamed")
        page.click("#account-form button[type='submit']")
        page.wait_for_selector("text=Account updated.")

        page.fill("#account-current-password", "AdminPassword123!")
        page.fill("#account-new-password", "AdminPassword456!")
        page.fill("#account-confirm-password", "AdminPassword456!")
        page.click("#account-form button[type='submit']")
        page.wait_for_selector("text=Account updated.")

        page.click("#workspace-tab-admin")
        page.wait_for_selector("#users-section:not([hidden])")

        long_email = f"{'a' * 250}@example.com"
        page.fill("#user-email", long_email)
        page.fill("#user-display-name", "Too Long Email")
        page.fill("#user-password", "TooLongEmailPass123!")
        page.click("#user-create-form button[type='submit']")
        page.wait_for_selector("text=Invalid request payload. email: must be 255 characters or fewer")

        page.fill("#user-email", "ui.user@example.com")
        page.fill("#user-display-name", "UI User")
        page.fill("#user-password", "UiUserPassword123!")
        page.check("#user-role-administrator")
        with page.expect_response("**/api/v1/users") as create_user_response_info:
            page.click("#user-create-form button[type='submit']")

        create_user_response = create_user_response_info.value
        assert create_user_response.status == 201, create_user_response.text()

        page.wait_for_selector("text=User created.")
        page.wait_for_selector("text=ui.user@example.com")
        user_row = page.locator("#users-table-body tr", has_text="ui.user@example.com")
        assert user_row.count() >= 1
        assert "administrator" in (user_row.first.inner_text() or "")

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
        user_row = page.locator("#users-table-body tr", has_text="ui.user@example.com")
        assert user_row.count() >= 1
        assert "administrator" in (user_row.first.inner_text() or "")

        page.click("#workspace-tab-collection")
        page.wait_for_selector("#jigsaws-section:not([hidden])")
        page.click("#collection-tab-quick-create")
        page.wait_for_selector("#collection-quick-create-panel:not([hidden])")

        page.fill("#jigsaw-title", "UI Smoke Puzzle")
        page.evaluate("() => { document.querySelector('#jigsaw-title').value = 'T'.repeat(256); }")
        page.fill("#jigsaw-piece-count", "500")
        page.click("#jigsaw-create-form button[type='submit']")
        page.wait_for_selector("text=Invalid request payload. title: must be 255 characters or fewer")

        page.fill("#jigsaw-title", "UI Smoke Puzzle")
        page.click("#jigsaw-create-form button[type='submit']")

        page.wait_for_selector("text=Jigsaw created.")

        page.click("#collection-tab-jigsaws")
        page.wait_for_selector("#collection-jigsaws-panel:not([hidden])")

        page.fill("#jigsaw-search-input", "ui smoke")
        page.wait_for_selector("#jigsaws-table-body tr:has-text('UI Smoke Puzzle')")
        page.fill("#jigsaw-search-input", "definitely-not-present")
        page.wait_for_selector("#jigsaws-table-body td:has-text('No matching jigsaws found.')")
        page.fill("#jigsaw-search-input", "")
        page.wait_for_selector("#jigsaws-table-body tr:has-text('UI Smoke Puzzle')")

        page.click("#workspace-tab-loans")
        page.wait_for_selector("#loans-section:not([hidden])")

        borrower_options = page.locator("#loan-borrower-user-id option")
        assert borrower_options.filter(has_text="admin@example.com").count() >= 1

        borrower_option_value = borrower_options.filter(has_text="admin@example.com").first.get_attribute("value")
        jigsaw_option_value = page.locator("#loan-jigsaw-id option").nth(1).get_attribute("value")
        assert borrower_option_value
        assert jigsaw_option_value

        page.select_option("#loan-borrower-user-id", borrower_option_value)
        page.select_option("#loan-jigsaw-id", jigsaw_option_value)
        page.click("#loan-create-form button[type='submit']")

        page.wait_for_selector("text=Loan created.")
        page.wait_for_selector("#loans-table-body tr button[data-loan-return]")

        page.locator("#loans-table-body tr", has_text="active").locator("button[data-loan-return]").first.click()
        page.wait_for_selector("text=Loan returned.")

        page.click("#workspace-tab-collection")
        page.wait_for_selector("#jigsaws-section:not([hidden])")
        page.click("#collection-tab-images")
        page.wait_for_selector("#collection-images-panel:not([hidden])")

        page.select_option("#jigsaw-image-jigsaw-id", jigsaw_option_value)
        page.fill("#jigsaw-image-tag", "completed puzzle")
        page.set_input_files(
            "#jigsaw-image-file",
            {
                "name": "notes.txt",
                "mimeType": "text/plain",
                "buffer": b"this-is-not-an-image",
            },
        )
        page.click("#jigsaw-image-form button[type='submit']")
        page.wait_for_selector("text=Invalid request payload. image: must be a supported raster image type")

        page.fill("#jigsaw-image-tag", "")
        page.set_input_files(
            "#jigsaw-image-file",
            {
                "name": "completed.png",
                "mimeType": "image/png",
                "buffer": b"\x89PNG\r\n\x1a\n" + (b"x" * 120_000),
            },
        )
        page.click("#jigsaw-image-form button[type='submit']")
        page.wait_for_selector("text=Jigsaw image uploaded.")
        page.wait_for_selector("#jigsaw-images-table-body tr")
        assert page.locator("#jigsaw-images-table-body tr", has_text="untagged").count() >= 1

        page.set_input_files(
            "#image-library-files",
            [
                {
                    "name": "bulk-one.png",
                    "mimeType": "image/png",
                    "buffer": b"\x89PNG\r\n\x1a\n" + (b"a" * 4096),
                },
                {
                    "name": "bulk-two.png",
                    "mimeType": "image/png",
                    "buffer": b"\x89PNG\r\n\x1a\n" + (b"b" * 4096),
                },
            ],
        )
        page.select_option("#image-library-tag", "Completed")
        page.click("#image-library-upload-form button[type='submit']")
        page.wait_for_selector("text=Image library upload complete. Added 2 image(s), skipped 0.")

        completed_filter = page.locator(
            "#image-library-tag-filters .govuk-checkboxes__item", has_text="Completed"
        ).locator("input")
        completed_filter.check()
        page.wait_for_selector("#image-library-table-body tr")
        assert page.locator("#image-library-table-body tr", has_text="bulk-one.png").count() >= 1
        assert page.locator("#image-library-table-body tr", has_text="bulk-two.png").count() >= 1
        assert page.locator("#image-library-table-body tr", has_text="Completed").count() >= 2

        bulk_two_row = page.locator("#image-library-table-body tr", has_text="bulk-two.png")
        bulk_two_row.locator("select[data-image-tag-select]").select_option("Box side")
        bulk_two_row.locator("button[data-image-tag-set]").click()
        page.wait_for_selector("text=Image tagged as Box side.")

        box_side_filter = page.locator(
            "#image-library-tag-filters .govuk-checkboxes__item", has_text="Box side"
        ).locator("input")
        box_side_filter.check()
        page.wait_for_selector("#image-library-table-body tr:has-text('bulk-two.png'):has-text('Box side')")

        bulk_one_row = page.locator("#image-library-table-body tr", has_text="bulk-one.png")
        bulk_one_row.locator("select[data-image-assign-select]").select_option(jigsaw_option_value)
        bulk_one_row.locator("button[data-image-assign]").click()
        page.wait_for_selector("text=Image assigned to jigsaw.")
        page.wait_for_selector("#image-library-table-body tr:has-text('bulk-one.png'):has-text('UI Smoke Puzzle')")

        page.uncheck("#image-library-filter-assigned")
        page.wait_for_selector("#image-library-table-body tr:has-text('bulk-two.png')")
        assert page.locator("#image-library-table-body tr", has_text="bulk-one.png").count() == 0

        page.check("#image-library-filter-assigned")
        page.uncheck("#image-library-filter-unassigned")
        page.evaluate(
            """() => {
                document
                  .querySelectorAll('#image-library-tag-filters input[type="checkbox"]')
                  .forEach((checkbox) => {
                    if (!checkbox.checked) {
                      checkbox.checked = true;
                      checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                  });
            }"""
        )
        page.wait_for_selector("#image-library-table-body tr:has-text('bulk-one.png')")
        assert page.locator("#image-library-table-body tr", has_text="bulk-two.png").count() == 0

        page.check("#image-library-filter-unassigned")
        page.wait_for_selector("#image-library-table-body tr:has-text('bulk-one.png')")

        box_side_filter.uncheck()
        page.wait_for_selector("#image-library-table-body tr:has-text('bulk-one.png')")
        assert page.locator("#image-library-table-body tr", has_text="bulk-two.png").count() == 0
        box_side_filter.check()
        page.wait_for_selector("#image-library-table-body tr:has-text('bulk-two.png')")

        page.click("#collection-tab-jigsaws")
        page.wait_for_selector("#collection-jigsaws-panel:not([hidden])")

        jigsaw_row = page.locator("#jigsaws-table-body tr", has_text="UI Smoke Puzzle")
        jigsaw_row.locator("button[data-jigsaw-images-toggle]").click()
        page.wait_for_selector("#jigsaws-table-body tr.app-jigsaw-images-row button[data-jigsaw-image-detach]")
        page.locator("#jigsaws-table-body tr.app-jigsaw-images-row button[data-jigsaw-image-detach]").first.click()
        page.wait_for_selector("text=Image detached from jigsaw.")

        jigsaw_row.locator("button[data-jigsaw-image-detach]").click()
        page.wait_for_selector("text=Image detached from jigsaw.")
        page.click("#collection-tab-images")
        page.wait_for_selector("#collection-images-panel:not([hidden])")
        page.wait_for_selector("#image-library-table-body tr:has-text('bulk-one.png'):has-text('unassigned')")

        page.evaluate(
            """() => {
                const unassigned = document.querySelector('#image-browser-filter-unassigned');
                if (unassigned) {
                    unassigned.checked = false;
                    unassigned.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }"""
        )

        page.click("#collection-tab-image-browser")
        page.wait_for_selector("#collection-image-browser-panel:not([hidden])")
        page.wait_for_selector("#image-browser-modal:not([hidden])")
        assert page.locator("#image-browser-assign-previous").is_visible()
        assert page.locator("#image-browser-assign-next").is_visible()
        assert page.locator("#image-browser-create-jigsaw").is_visible()
        assert page.locator("#image-browser-delete").is_visible()

        page.once("dialog", lambda dialog: dialog.accept())
        page.click("#image-browser-delete")
        page.wait_for_selector("text=Image deleted.")
        page.keyboard.press("Escape")
        page.wait_for_selector("#image-browser-modal", state="hidden")

        page.click("#collection-tab-diary")
        page.wait_for_selector("#collection-diary-panel:not([hidden])")
        page.select_option("#diary-jigsaw-id", jigsaw_option_value)
        page.select_option("#diary-difficulty", "4")
        page.fill("#diary-notes", "UI diary entry")
        page.click("#diary-entry-form button[type='submit']")
        page.wait_for_selector("text=Diary entry added.")
        page.wait_for_selector("#diary-entries-table-body tr:has-text('UI diary entry')")
        diary_row = page.locator("#diary-entries-table-body tr", has_text="UI diary entry")
        diary_row.locator("button[data-diary-edit]").click()
        page.fill("#diary-notes", "UI diary entry edited")
        page.select_option("#diary-difficulty", "5")
        page.click("#diary-entry-submit")
        page.wait_for_selector("text=Diary entry updated.")
        page.wait_for_selector("#diary-entries-table-body tr:has-text('UI diary entry edited'):has-text('5')")

        page.click("#diary-view-calendar")
        page.wait_for_selector("#diary-calendar-region:not([hidden])")
        assert page.locator("#diary-calendar-grid .app-diary-calendar-day").count() == 42
        assert page.locator("#diary-calendar-grid .app-diary-calendar-day--has-entry").count() >= 1
        initial_month_label = (page.locator("#diary-calendar-month-label").text_content() or "").strip()
        page.click("#diary-calendar-next")
        next_month_label = (page.locator("#diary-calendar-month-label").text_content() or "").strip()
        assert next_month_label and next_month_label != initial_month_label
        page.click("#diary-calendar-today")
        assert (page.locator("#diary-calendar-month-label").text_content() or "").strip() == initial_month_label
        page.click("#diary-view-list")
        page.wait_for_selector("#diary-list-region:not([hidden])")

        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#diary-entries-table-body tr", has_text="UI diary entry edited").locator("button[data-diary-delete]").click()
        page.wait_for_selector("text=Diary entry deleted.")
        assert page.locator("#diary-entries-table-body tr", has_text="UI diary entry edited").count() == 0

        page.click("#collection-tab-jigsaws")
        page.wait_for_selector("#collection-jigsaws-panel:not([hidden])")
        assert page.locator("#jigsaws-table-body tr", has_text="UI Smoke Puzzle").locator("td").nth(3).inner_text() != "-"

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
        page.click("#workspace-tab-activity-log")
        page.wait_for_selector("#audit-section:not([hidden])")
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
