"""Browser tests for the image browser while saves run in the background (issue #7).

A save finishing later must not change which image is open, throw away edits made since, or send
the next action to a different image; and a slow image load must not replace a newer one.
"""

import time
from io import BytesIO
from threading import Thread

import pytest
from flask import request
from PIL import Image
from werkzeug.serving import make_server

from app import create_app
from app.db import get_session
from app.models import Role, User, UserRole
from tests.migration_utils import upgrade_database_to_head

playwright_sync_api = pytest.importorskip("playwright.sync_api")

SLOW_SECONDS = 2.5
# Solid colours, so the test can tell which image the canvas really shows.
COLOURS = {
    "red": (220, 30, 30),
    "green": (30, 170, 60),
    "blue": (30, 70, 220),
    "yellow": (230, 200, 20),
}


def _solid_png(rgb):
    buffer = BytesIO()
    Image.new("RGB", (96, 64), color=rgb).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture()
def image_browser_server(tmp_path):
    db_path = tmp_path / "ui_image_browser.db"

    class UITestImageBrowserConfig:
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

    app = create_app(UITestImageBrowserConfig)
    upgrade_database_to_head(UITestImageBrowserConfig.DATABASE_URL)

    with app.app_context():
        db_session = get_session()
        admin_role = db_session.query(Role).filter_by(name="administrator").one()
        admin = User(email="admin@example.com", display_name="Admin User", is_active=True)
        admin.set_password("AdminPassword123!")
        db_session.add(admin)
        db_session.flush()
        db_session.add(UserRole(user_id=admin.id, role_id=admin_role.id))
        db_session.commit()

    # Switched on after seeding (Flask needs hooks registered before the first request).
    slow = {"saves": False, "content_ids": set()}

    @app.before_request
    def _slow_down():
        path = request.path
        is_overwrite = request.method == "PUT" and path.endswith("/content")
        is_save_create = request.method == "POST" and path.endswith("/images") and request.form.get("tag") == "Reference"
        if slow["saves"] and (is_overwrite or is_save_create):
            time.sleep(SLOW_SECONDS)
        if request.method == "GET" and not request.args.get("variant"):
            for image_id in slow["content_ids"]:
                if path == f"/api/v1/images/{image_id}/content":
                    time.sleep(SLOW_SECONDS)

    # Jigsaw 1: red "Box front", then green "In progress". A Reference made from the red image
    # sorts between them, so it moves the green image down one place.
    # Jigsaw 2: blue "Box front", yellow "Box side".
    client = app.test_client()
    login = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "AdminPassword123!"})
    headers = {"X-CSRF-Token": login.get_json()["data"]["csrf_token"]}
    ids = {}
    for title, images in (
        ("Autumn Lake", [("red", "Box front"), ("green", "In progress")]),
        ("Harbour Lights", [("blue", "Box front"), ("yellow", "Box side")]),
    ):
        jigsaw = client.post("/api/v1/jigsaws", json={"title": title, "piece_count": 1000}, headers=headers)
        jigsaw_id = jigsaw.get_json()["data"]["id"]
        for colour, tag in images:
            uploaded = client.post(
                f"/api/v1/jigsaws/{jigsaw_id}/images",
                data={"tag": tag, "image": (BytesIO(_solid_png(COLOURS[colour])), f"{colour}.png")},
                headers=headers,
                content_type="multipart/form-data",
            )
            assert uploaded.status_code == 201, uploaded.get_data(as_text=True)
            ids[colour] = uploaded.get_json()["data"]["id"]

    slow["saves"] = True

    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", ids, slow
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _open_image_browser(playwright, base_url):
    try:
        browser = playwright.chromium.launch(headless=True)
    except Exception as error:  # pragma: no cover
        pytest.skip(f"Playwright browser unavailable: {error}")
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto(base_url, wait_until="networkidle")
    page.click("#login-open-button")
    page.fill("#login-email", "admin@example.com")
    page.fill("#login-password", "AdminPassword123!")
    page.click("#login-form button[type='submit']")
    page.wait_for_selector("text=Signed in successfully.")
    page.click("#workspace-tab-collection")
    page.click("#collection-tab-image-browser")  # opening the tab launches the browser
    page.wait_for_selector("#image-browser-status:has-text('Image 1 of')")
    return browser, page


def _status(page):
    return page.inner_text("#image-browser-status")


def _canvas_colour(page):
    """The colour name closest to the pixel in the middle of the canvas."""
    rgb = page.evaluate(
        """() => {
            const canvas = document.getElementById('image-browser-canvas');
            const pixel = canvas.getContext('2d').getImageData(canvas.width / 2, canvas.height / 2, 1, 1).data;
            return [pixel[0], pixel[1], pixel[2]];
        }"""
    )
    return min(COLOURS, key=lambda name: sum((a - b) ** 2 for a, b in zip(COLOURS[name], rgb)))


def _wait_for_canvas(page, colour):
    deadline = time.time() + 10
    while time.time() < deadline:
        if _canvas_colour(page) == colour:
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"canvas shows {_canvas_colour(page)}, expected {colour}")


@pytest.mark.functional
@pytest.mark.ui
def test_save_create_finishing_later_keeps_the_open_image_and_its_edits(image_browser_server):
    base_url, ids, _slow = image_browser_server
    with playwright_sync_api.sync_playwright() as playwright:
        browser, page = _open_image_browser(playwright, base_url)
        _wait_for_canvas(page, "red")
        assert f"ID: {ids['red']}" in _status(page)

        # Save create on the red image runs in the background; meanwhile edit the next image.
        page.click("#image-browser-save-create")
        page.wait_for_selector("text=Reference image save started in background.")
        page.click("#image-browser-next")
        _wait_for_canvas(page, "green")
        page.click("#image-browser-rotate-right")
        page.wait_for_selector("#image-browser-status:has-text('unsaved edits')")

        page.wait_for_selector("text=Reference image created as image #", timeout=15000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)

        # Still the green image, with its rotation not thrown away.
        status = _status(page)
        assert f"ID: {ids['green']}" in status, status
        assert "unsaved edits" in status, status
        assert _canvas_colour(page) == "green"
        browser.close()


@pytest.mark.functional
@pytest.mark.ui
def test_next_save_after_a_background_save_goes_to_the_image_on_screen(image_browser_server):
    base_url, ids, slow = image_browser_server
    with playwright_sync_api.sync_playwright() as playwright:
        browser, page = _open_image_browser(playwright, base_url)
        _wait_for_canvas(page, "red")

        page.click("#image-browser-save-create")
        page.click("#image-browser-next")
        _wait_for_canvas(page, "green")
        page.wait_for_selector("text=Reference image created as image #", timeout=15000)
        page.wait_for_load_state("networkidle")

        slow["saves"] = False
        overwrite_targets = []
        page.on(
            "request",
            lambda req: overwrite_targets.append(req.url) if req.method == "PUT" and "/content" in req.url else None,
        )
        page.click("#image-browser-rotate-right")
        page.click("#image-browser-save")
        page.wait_for_selector("text=Image overwritten successfully.")
        browser.close()

    assert len(overwrite_targets) == 1
    assert f"/image-library/images/{ids['green']}/content" in overwrite_targets[0], overwrite_targets


@pytest.mark.functional
@pytest.mark.ui
def test_a_slow_image_load_does_not_replace_a_newer_one(image_browser_server):
    base_url, ids, slow = image_browser_server
    with playwright_sync_api.sync_playwright() as playwright:
        browser, page = _open_image_browser(playwright, base_url)
        _wait_for_canvas(page, "red")
        # The blue image loads slowly; move past it to the yellow image before it arrives.
        slow["content_ids"].add(ids["blue"])
        page.evaluate("() => sessionStorage.clear()")
        page.click("#image-browser-next")  # green
        _wait_for_canvas(page, "green")
        page.click("#image-browser-next")  # blue (slow)
        page.click("#image-browser-next")  # yellow
        page.wait_for_selector(f"#image-browser-status:has-text('ID: {ids['yellow']}')")

        page.wait_for_timeout(int(SLOW_SECONDS * 1000) + 1500)

        assert f"ID: {ids['yellow']}" in _status(page)
        assert _canvas_colour(page) == "yellow"
        browser.close()


@pytest.mark.functional
@pytest.mark.ui
def test_tagging_keeps_the_open_image_and_its_unsaved_rotation(image_browser_server):
    base_url, ids, _slow = image_browser_server
    with playwright_sync_api.sync_playwright() as playwright:
        browser, page = _open_image_browser(playwright, base_url)
        _wait_for_canvas(page, "red")
        page.click("#image-browser-rotate-right")
        page.wait_for_selector("#image-browser-status:has-text('unsaved edits')")

        page.keyboard.press("c")  # tag as Completed: the image moves within its jigsaw's group
        page.wait_for_selector("text=Image tagged as Completed.")
        page.wait_for_load_state("networkidle")

        status = _status(page)
        assert f"ID: {ids['red']}" in status, status
        assert "Completed" in status, status
        assert "unsaved edits" in status, status
        browser.close()
