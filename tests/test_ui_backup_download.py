"""Backup download links: only same-site paths are followed (CodeQL js/xss-through-dom)."""

import json

import pytest

from tests.test_ui_admin_panel import playwright_sync_api, ui_server  # noqa: F401

BACKUPS_PATTERN = "**/api/v1/system/database-backups"


def _backup(backup_id, download_url):
    return {
        "id": backup_id,
        "filename": f"backup-{backup_id}.sql.gz",
        "status": "completed",
        "app_environment": "dev",
        "app_environment_label": "Dev",
        "app_version": "0.0.0-dev",
        "file_size_bytes": 1024,
        "created_at": "2026-11-18T09:00:00+00:00",
        "completed_at": "2026-11-18T09:01:00+00:00",
        "download_url": download_url,
        "delete_url": f"/api/v1/system/database-backups/{backup_id}",
    }


@pytest.mark.functional
@pytest.mark.ui
def test_only_same_site_backup_links_get_a_download_button(ui_server):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as error:  # pragma: no cover
            pytest.skip(f"Playwright browser unavailable: {error}")
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        backups = [
            _backup(1, "/api/v1/system/database-backups/1/download"),
            _backup(2, "javascript:window.__backupXss=1"),
            _backup(3, "https://elsewhere.example/backup.sql.gz"),
        ]
        page.route(
            BACKUPS_PATTERN,
            lambda route: route.fulfill(
                status=200, content_type="application/json", body=json.dumps({"data": backups, "meta": {}})
            )
            if route.request.method == "GET"
            else route.continue_(),
        )
        downloads = []
        page.route(
            "**/api/v1/system/database-backups/*/download",
            lambda route: downloads.append(route.request.url) or route.fulfill(status=204, body=""),
        )

        page.goto(ui_server, wait_until="networkidle")
        page.click("#login-open-button")
        page.fill("#login-email", "admin@example.com")
        page.fill("#login-password", "AdminPassword123!")
        page.click("#login-form button[type='submit']")
        page.wait_for_selector("text=Signed in successfully.")
        page.click("#workspace-tab-admin")
        page.click("#admin-tab-backups")
        page.wait_for_selector("#database-backups-table-body tr:has-text('backup-3.sql.gz')")

        buttons = page.locator("#database-backups-table-body [data-backup-download]")
        assert buttons.count() == 1
        assert buttons.first.get_attribute("data-backup-download") == "1"
        # The link itself is no longer kept in the page.
        assert page.locator("[data-backup-download-url]").count() == 0

        buttons.first.click(no_wait_after=True)
        for _ in range(50):
            if downloads:
                break
            page.wait_for_timeout(100)
        assert downloads and downloads[0].endswith("/api/v1/system/database-backups/1/download")
        assert page.evaluate("() => window.__backupXss") is None
        browser.close()
