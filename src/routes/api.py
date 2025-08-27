from flask import Blueprint

api_bp = Blueprint("api", __name__)

@api_bp.route("/heartbeat", methods=["POST"])
def heartbeat():
    return {"status": "ok"}
