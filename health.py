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
    # trivial, no deps, always 200
    return "pong", 200

@health_bp.route("/health", methods=["GET"])
def health_alias():
    # JSON alias for generic probes
    return jsonify({"status": "ok"}), 200

@health_bp.route("/_ah/health", methods=["GET"])
def ah_health_alias():
    # Legacy GAE probe path
    return "ok", 200


