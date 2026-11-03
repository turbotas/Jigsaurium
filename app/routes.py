from flask import Blueprint, redirect, render_template, url_for


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    return render_template("home.html")


@main_bp.get("/mobile-capture")
def mobile_capture():
    return render_template("mobile_capture.html")


@main_bp.get("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="branding/icons/favicon.ico"), code=302)


@main_bp.get("/apple-touch-icon.png")
def apple_touch_icon():
    return redirect(url_for("static", filename="branding/icons/apple-touch-icon.png"), code=302)


@main_bp.get("/site.webmanifest")
def site_webmanifest():
    return redirect(url_for("static", filename="branding/site.webmanifest"), code=302)
