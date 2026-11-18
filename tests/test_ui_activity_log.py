"""Browser tests for the richer Activity Log (issue #96)."""

import pytest

from tests.test_ui_admin_panel import playwright_sync_api, ui_server  # noqa: F401

expect = playwright_sync_api.expect

HOSTILE_TITLE = 'Lighthouse <img src=x onerror="window.__auditXss=1">'


def _launch(playwright):
    try:
        return playwright.chromium.launch(headless=True)
    except Exception as error:  # pragma: no cover
        pytest.skip(f"Playwright browser unavailable: {error}")


def _api(page, method, path, body=None):
    """Call the API from inside the signed-in page (session cookie plus CSRF token)."""
    return page.evaluate(
        """async ([method, path, body]) => {
            const me = await (await fetch('/api/v1/auth/me', { credentials: 'same-origin' })).json();
            const response = await fetch(path, {
                method,
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': me.data.csrf_token },
                body: body ? JSON.stringify(body) : undefined,
            });
            return { status: response.status, body: await response.json() };
        }""",
        [method, path, body],
    )


@pytest.fixture()
def activity_page(ui_server):  # noqa: F811
    with playwright_sync_api.sync_playwright() as playwright:
        browser = _launch(playwright)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        page.goto(ui_server, wait_until="networkidle")
        page.click("#login-open-button")
        page.fill("#login-email", "admin@example.com")
        page.fill("#login-password", "AdminPassword123!")
        page.click("#login-form button[type='submit']")
        page.wait_for_selector("text=Signed in successfully.")

        created = _api(page, "POST", "/api/v1/jigsaws", {"title": "Harbour Lights", "piece_count": 1000})
        assert created["status"] == 201, created
        jigsaw_id = created["body"]["data"]["id"]
        other = _api(page, "POST", "/api/v1/jigsaws", {"title": "Autumn Lake", "piece_count": 500})
        edited = _api(page, "PATCH", f"/api/v1/jigsaws/{jigsaw_id}", {"title": HOSTILE_TITLE})
        assert edited["status"] == 200, edited

        page.click("#workspace-tab-activity-log")
        page.wait_for_selector("#audit-section:not([hidden])")
        page.wait_for_selector("#audit-table-body tr:has-text('Jigsaw updated')")
        yield page, jigsaw_id, other["body"]["data"]["id"]
        browser.close()


def _rows(page):
    return page.locator("#audit-table-body tr")


@pytest.mark.functional
@pytest.mark.ui
def test_rows_show_readable_events_with_before_and_after_values(activity_page):
    page, jigsaw_id, _other_id = activity_page
    row = _rows(page).filter(has_text="Jigsaw updated").first

    assert row.locator(".govuk-tag").inner_text().strip().lower() == "jigsaw updated"
    assert row.locator("[data-audit-actor]").inner_text() == "Admin User"
    assert row.locator(".app-audit-change__from").inner_text() == "Harbour Lights"
    assert row.locator(".app-audit-change__to").inner_text() == HOSTILE_TITLE
    assert row.locator(f"[data-jigsaw-view='{jigsaw_id}']").count() == 1
    assert row.locator("td").last.inner_text().strip() not in ("", "-")  # IP address
    # Text from the record is shown as text, never run as markup.
    assert row.locator("img").count() == 0
    assert page.evaluate("() => window.__auditXss") is None


@pytest.mark.functional
@pytest.mark.ui
def test_event_filter_and_search(activity_page):
    page, _jigsaw_id, _other_id = activity_page

    page.select_option("#audit-filter-event", "action:jigsaw.created")
    page.click("#audit-filter-apply")
    # Wait for the filtered results themselves: the old table stays on screen until they arrive.
    page.wait_for_function(
        "() => [...document.querySelectorAll('#audit-table-body .govuk-tag')].every(t => t.textContent === 'Jigsaw created')"
    )
    expect(_rows(page)).to_have_count(2)

    page.click("#audit-filter-clear")
    page.fill("#audit-filter-q", "autumn lake")
    page.click("#audit-filter-apply")
    expect(_rows(page)).to_have_count(1)
    expect(_rows(page).first).to_contain_text("Autumn Lake")


@pytest.mark.functional
@pytest.mark.ui
def test_history_link_shows_one_records_events(activity_page):
    page, jigsaw_id, _other_id = activity_page
    row = _rows(page).filter(has_text="Jigsaw updated").first

    row.locator("[data-audit-history-type]").click()
    page.wait_for_selector("#audit-record-filter:not([hidden])")
    assert f"Jigsaw #{jigsaw_id}" in page.inner_text("#audit-record-filter-label")
    expect(_rows(page)).to_have_count(2)
    tags = sorted(t.strip().lower() for t in page.locator("#audit-table-body .govuk-tag").all_inner_texts())
    assert tags == ["jigsaw created", "jigsaw updated"]

    page.click("#audit-record-filter-clear")
    page.wait_for_selector("#audit-record-filter", state="hidden")
    page.wait_for_selector("#audit-table-body tr:has-text('Signed in')")


@pytest.mark.functional
@pytest.mark.ui
def test_clicking_an_account_filters_to_it(activity_page):
    page, _jigsaw_id, _other_id = activity_page

    _rows(page).first.locator("[data-audit-actor]").click()
    page.wait_for_function("() => document.getElementById('audit-filter-actor').value !== ''")
    expect(_rows(page).filter(has_not=page.locator("[data-audit-actor]:text-is('Admin User')"))).to_have_count(0)
    names = set(page.locator("#audit-table-body [data-audit-actor]").all_inner_texts())
    assert names == {"Admin User"}


@pytest.mark.functional
@pytest.mark.ui
def test_filter_options_arriving_late_keep_what_was_typed(activity_page):
    """The filter option lists reload with each search; they must not wipe a search being typed."""
    page, _jigsaw_id, _other_id = activity_page
    held = []
    page.route("**/api/v1/audit-events/facets", lambda route: held.append(route))

    page.click("#audit-filter-clear")
    for _ in range(100):
        if held:
            break
        page.wait_for_timeout(50)
    assert held, "the filter options were not reloaded"
    page.fill("#audit-filter-q", "autumn lake")

    for route in held:
        route.continue_()
    page.unroute("**/api/v1/audit-events/facets")
    expect(page.locator("#audit-table-body tr")).to_have_count(4)  # The cleared search has finished.
    assert page.input_value("#audit-filter-q") == "autumn lake"

    page.click("#audit-filter-apply")
    expect(_rows(page)).to_have_count(1)
    expect(_rows(page).first).to_contain_text("Autumn Lake")
