from flask import Blueprint, render_template


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    return render_template("home.html")


@main_bp.get("/mobile-capture")
def mobile_capture():
    return render_template("mobile_capture.html")
