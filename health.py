from flask import Blueprint, jsonify
import datetime

health_bp = Blueprint("health", __name__)

@health_bp.route("/healthz", methods=["GET"])
def healthz():
    # trivial, no deps, always 200; include ts for tests/monitoring
    return jsonify({
        "status": "ok",
        "ts": datetime.datetime.utcnow().isoformat()
    }), 200

@health_bp.route("/ping", methods=["GET"])
def ping():
    return "pong", 200


