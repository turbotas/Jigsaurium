from flask import Blueprint, current_app, make_response, redirect, render_template, url_for


main_bp = Blueprint("main", __name__)

# Every other page denies the camera (see the security headers in app/__init__.py). The guided
# capture page is the one place that may use it, for its own origin only, so desktop browsers
# can offer a live webcam capture (issue #10).
MOBILE_CAPTURE_PERMISSIONS_POLICY = "geolocation=(), camera=(self), microphone=()"


def _feature_flag_context():
    return {
        "feature_ai_enabled": bool(current_app.config.get("AI_ENABLED", False)),
        "feature_embeddings_enabled": bool(current_app.config.get("IMAGE_EMBEDDINGS_ENABLED", False)),
    }


@main_bp.get("/")
def home():
    return render_template(
        "home.html",
        image_editor_mode=False,
        image_editor_image_id=None,
        **_feature_flag_context(),
    )


@main_bp.get("/image-editor/<int:image_id>")
def image_editor(image_id):
    return render_template(
        "home.html",
        image_editor_mode=True,
        image_editor_image_id=int(image_id),
        **_feature_flag_context(),
    )


@main_bp.get("/mobile-capture")
def mobile_capture():
    response = make_response(render_template("mobile_capture.html"))
    response.headers["Permissions-Policy"] = MOBILE_CAPTURE_PERMISSIONS_POLICY
    return response


@main_bp.get("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="branding/icons/favicon.ico"), code=302)


@main_bp.get("/apple-touch-icon.png")
def apple_touch_icon():
    return redirect(url_for("static", filename="branding/icons/apple-touch-icon.png"), code=302)


@main_bp.get("/site.webmanifest")
def site_webmanifest():
    return redirect(url_for("static", filename="branding/site.webmanifest"), code=302)
