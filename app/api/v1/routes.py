from flask import Blueprint, current_app, g


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _success_response(data, status_code=200):
    return {"data": data, "meta": {"request_id": g.request_id}}, status_code


@api_v1_bp.get("/health")
def health_check():
    payload = {
        "status": "ok",
        "environment": current_app.config["APP_ENV"],
    }
    return _success_response(payload)
