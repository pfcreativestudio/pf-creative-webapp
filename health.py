from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)

@health_bp.route("/healthz", methods=["GET"])
def healthz():
    # trivial, no deps, always 200
    return jsonify({"status": "ok"}), 200

@health_bp.route("/ping", methods=["GET"])
def ping():
    return "pong", 200


