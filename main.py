# -*- coding: utf-8 -*-
"""
PF System API - unified Flask app for Cloud Run
"""
import os
import json
import logging
import base64
import datetime
import urllib.request
import urllib.error

from PIL import Image
import io

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import psycopg2
import psycopg2.pool
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

# --- NEW IMPORTS FOR V1 MULTI-AGENT ARCHITECTURE ---
import services
from pydantic import ValidationError # 用于捕获 Pydantic 错误
# --- END NEW IMPORTS ---

# Gemini SDK (optional)
_GEM_ENABLED = False
try:
    # 【最终修正】修正 google.generativeai 的拼写错误
    import google.generativeai as genai
    _GEM_ENABLED = True
except Exception as e:
    # 【诊断代码】如果导入失败，将详细的错误信息打印到日志中
    logging.error(f"--- FATAL: FAILED TO IMPORT GOOGLE.GENERATIVEAI --- The real error is: {e}", exc_info=True)
    _GEM_ENABLED = False

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pf.api")

# ----------------------------------------------------------------------------
# Env
# ----------------------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_SECRET")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "CHANGE_ME_ADMIN")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")  # <project>:<region>:<instance>
DB_SOCKET_DIR = "/cloudsql"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BASE_URL = (os.getenv("BASE_URL") or "").rstrip("/")

BILLPLZ_API_KEY = os.getenv("BILLPLZ_API_KEY", "")
BILLPLZ_COLLECTION_ID = os.getenv("BILLPLZ_COLLECTION_ID", "")
BILLPLZ_X_SIGNATURE = os.getenv("BILLPLZ_X_SIGNATURE", "")

# ----------------------------------------------------------------------------
# Flask app & helpers
# ----------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

def json_response(payload, status=200):
    return app.response_class(
        response=json.dumps(payload, ensure_ascii=False),
        status=status,
        mimetype="application/json",
    )

# ----------------------------------------------------------------------------
# DB Pool
# ----------------------------------------------------------------------------
db_pool = None

def _db_dsn():
    if not (DB_USER and DB_PASSWORD and DB_NAME and INSTANCE_CONNECTION_NAME):
        return None
    host = f"{DB_SOCKET_DIR}/{INSTANCE_CONNECTION_NAME}"
    return f"user={DB_USER} password={DB_PASSWORD} dbname={DB_NAME} host={host}"

def init_db_pool():
    global db_pool
    if db_pool is not None:
        return
    dsn = _db_dsn()
    if not dsn:
        log.error("Database configuration is incomplete.")
        return
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=dsn)
    log.info("DB connection pool created.")

def get_conn():
    if db_pool is None:
        init_db_pool()
    if db_pool is None:
        raise RuntimeError("DB not available")
    return db_pool.getconn()

def put_conn(conn):
    try:
        if db_pool and conn:
            db_pool.putconn(conn)
    except Exception as e:
        log.error("put_conn error: %s", e)

def ensure_schema(cur):
    # users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            created_at TIMESTAMPTZ,
            subscription_expires_at TIMESTAMPTZ,
            active_token TEXT
        )
    """)
    # activity logs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id SERIAL PRIMARY KEY,
            ts TIMESTAMPTZ DEFAULT NOW(),
            actor TEXT,
            action TEXT,
            details JSONB,
            ip TEXT,
            user_agent TEXT
        )
    """)
    # prompt versions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prompt_versions (
            id SERIAL PRIMARY KEY,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            prompt_content JSONB NOT NULL
        )
    """)

# ----------------------------------------------------------------------------
# Activity log helper
# ----------------------------------------------------------------------------
def _log_activity(cur, actor, action, details, req):
    try:
        ua = req.headers.get("User-Agent", "")
        ip = req.headers.get("X-Forwarded-For", req.remote_addr or "")
        cur.execute(
            "INSERT INTO activity_logs (ts, actor, action, details, ip, user_agent)"
            " VALUES (NOW(), %s, %s, %s::jsonb, %s, %s)",
            (actor or "system", action or "event", json.dumps(details or {}), ip, ua),
        )
    except Exception as e:
        log.error("log_activity failed: %s", e)

# ----------------------------------------------------------------------------
# JWT helpers
# ----------------------------------------------------------------------------
def _jwt_create(username):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(days=30)).timestamp()),
    }
    tok = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return tok.decode() if isinstance(tok, bytes) else tok

def _jwt_decode(req):
    ah = req.headers.get("Authorization", "")
    if not ah.startswith("Bearer "):
        return None
    token = ah.split(" ", 1)[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        log.warning("jwt decode failed: %s", e)
        return None

# ----------------------------------------------------------------------------
# Gemini helpers (Legacy - kept for existing routes like chat-with-image)
# ----------------------------------------------------------------------------
def gemini_available():
    return _GEM_ENABLED and bool(GEMINI_API_KEY)

def call_gemini(prompt, system_instruction=None):
    if not gemini_available():
        raise RuntimeError("Gemini not configured")
    genai.configure(api_key=GEMINI_API_KEY)

    # Prefer pro, fallback flash (stability)
    model_names = ["models/gemini-1.5-pro", "models/gemini-1.5-flash"]
    last_err = None
    for name in model_names:
        try:
            model = genai.GenerativeModel(name, system_instruction=system_instruction)
            resp = model.generate_content(
                prompt,
                safety_settings=None,
                generation_config={"temperature": 0.8, "max_output_tokens": 2048},
            )
            if hasattr(resp, "text") and resp.text:
                return resp.text
            # candidates path
            try:
                parts = resp.candidates[0].content.parts
                out = []
                for p in parts:
                    t = getattr(p, "text", None)
                    if t:
                        out.append(t)
                if out:
                    return "\n".join(out)
            except Exception:
                pass
            try:
                return json.dumps(resp.to_dict())
            except Exception:
                return str(resp)
        except Exception as e:
            last_err = e
            log.warning("Gemini %s failed: %s", name, e)
            continue
    raise RuntimeError(f"Gemini call failed: {last_err}")

# ----------------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------------
@app.route("/healthz", methods=["GET"])
def healthz():
    return json_response({"ok": True, "ts": datetime.datetime.utcnow().isoformat()})

@app.route("/healthz/gemini", methods=["GET"])
def healthz_gemini():
    if not gemini_available():
        return json_response({"ok": False, "reason": "no_api_key_or_sdk"}, 503)
    try:
        out = call_gemini("Say OK.")
        return json_response({"ok": True, "sample": (out or "")[:80]})
    except Exception as e:
        return json_response({"ok": False, "reason": "call_failed", "error": str(e)}, 502)

@app.route("/healthz/db", methods=["GET"])
def healthz_db():
    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)
        cur.execute("SELECT 1")
        cur.fetchone()
        return json_response({"ok": True})
    except Exception as e:
        log.exception("healthz_db error")
        return json_response({"ok": False, "error": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

# ----------------------------------------------------------------------------
# Admin password verify
# ----------------------------------------------------------------------------
@app.route("/admin/verify-password", methods=["POST"])
def admin_verify():
    if request.headers.get("X-Admin-Password") != ADMIN_PASSWORD:
        return json_response({"success": False, "error": "Unauthorized"}, 401)
    return json_response({"success": True})

# ----------------------------------------------------------------------------
# Auth & Users
# ----------------------------------------------------------------------------
@app.route("/register", methods=["POST"])
def register():
    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)

        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        if not username or not password:
            return json_response({"error": "Username and password required"}, 400)
        
        if len(password) < 6:
            return json_response({"error": "Password must be at least 6 characters long"}, 400)

        cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return json_response({"error": "User already exists"}, 409)

        now = datetime.datetime.now(datetime.timezone.utc)
        
        hashed_password = generate_password_hash(password)

        cur.execute(
            "INSERT INTO users (username, password, created_at) VALUES (%s, %s, %s)",
            (username, hashed_password, now),
        )
        _log_activity(cur, username, "register_success", {}, request)
        conn.commit()
        return json_response({"success": True}, 201)
    except Exception as e:
        log.exception("register error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

@app.route("/login", methods=["POST"])
def login():
    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)

        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()

        cur.execute("SELECT password FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        
        if not row or not check_password_hash(row[0], password):
            return json_response({"error": "Invalid credentials"}, 401)

        token = _jwt_create(username)
        cur.execute("UPDATE users SET active_token=%s WHERE username=%s", (token, username))
        _log_activity(cur, username, "login_success", {}, request)
        conn.commit()
        return json_response({"success": True, "token": token})
    except Exception as e:
        log.exception("login error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

@app.route("/get-user-status", methods=["GET"])
def get_user_status():
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    username = payload.get("username")

    conn = cur = None
    try:
        log.info(f"--- DASHBOARD LOG --- Checking status for user: {username}")
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)
        cur.execute("SELECT username, subscription_expires_at FROM users WHERE username=%s", (username,))
        r = cur.fetchone()
        log.info(f"--- DASHBOARD LOG --- DB result for {username}: {r}")
        if not r:
            return json_response({"error": "User not found"}, 404)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        is_subscribed = r[1] is not None and r[1] > now

        return json_response({
            "username": r[0],
            "subscription_expires_at": r[1].isoformat() if r[1] else None,
            "is_subscribed": is_subscribed
        })
    except Exception as e:
        log.exception("get-user-status error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

# ----------------------------------------------------------------------------
# Admin APIs (require X-Admin-Password)
# ----------------------------------------------------------------------------
def _admin_guard():
    if request.headers.get("X-Admin-Password") != ADMIN_PASSWORD:
        return json_response({"error": "Unauthorized"}, 401)

@app.route("/admin/users", methods=["GET"])
def admin_users():
    g = _admin_guard()
    if g: return g

    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)

        sort = (request.args.get("sort") or "").lower()
        order_sql = "ASC" if sort == "asc" else "DESC"
        cur.execute(f"SELECT username, password, created_at, subscription_expires_at FROM users ORDER BY created_at {order_sql} NULLS LAST")
        users = []
        for r in cur.fetchall():
            users.append({
                "username": r[0],
                "password": "[HASHED]",
                "created_at": r[2].isoformat() if r[2] else None,
                "subscription_expires_at": r[3].isoformat() if r[3] else None
            })
        return json_response({"users": users})
    except Exception as e:
        log.exception("admin_users error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

@app.route("/admin/add-user", methods=["POST"])
def admin_add_user():
    g = _admin_guard()
    if g: return g

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        return json_response({"error": "Username and password required"}, 400)

    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)

        cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return json_response({"error": "User already exists"}, 409)

        now = datetime.datetime.now(datetime.timezone.utc)
        
        hashed_password = generate_password_hash(password)

        cur.execute(
            "INSERT INTO users (username, password, created_at) VALUES (%s, %s, %s)",
            (username, hashed_password, now),
        )
        _log_activity(cur, "admin", "add_user", {"username": username}, request)
        conn.commit()
        return json_response({"success": True}, 201)
    except Exception as e:
        log.exception("admin_add_user error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

@app.route("/admin/delete-user", methods=["DELETE"])
def admin_delete_user():
    g = _admin_guard()
    if g: return g

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    if not username:
        return json_response({"error": "Username required"}, 400)

    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)

        cur.execute("DELETE FROM users WHERE username=%s", (username,))
        if cur.rowcount == 0:
            return json_response({"success": False, "message": "User not found"}, 404)
        _log_activity(cur, "admin", "delete_user", {"username": username}, request)
        conn.commit()
        return json_response({"success": True})
    except Exception as e:
        log.exception("admin_delete_user error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

@app.route("/admin/update-user", methods=["PUT"])
def admin_update_user():
    g = _admin_guard()
    if g: return g

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        return json_response({"error": "Username and new password required"}, 400)

    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)

        hashed_password = generate_password_hash(password)

        cur.execute("UPDATE users SET password=%s WHERE username=%s", (hashed_password, username))
        if cur.rowcount == 0:
            return json_response({"success": False, "message": "User not found"}, 404)
        _log_activity(cur, "admin", "update_user_password", {"username": username}, request)
        conn.commit()
        return json_response({"success": True})
    except Exception as e:
        log.exception("admin_update_user error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

@app.route("/admin/add-subscription-time", methods=["PUT"])
def admin_add_sub_time():
    g = _admin_guard()
    if g: return g

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    days_to_add = data.get("days_to_add")

    if not username or days_to_add is None:
        return json_response({"error": "Username and days_to_add required"}, 400)
    try:
        days_to_add = int(days_to_add)
    except Exception:
        return json_response({"error": "days_to_add must be integer"}, 400)

    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)

        cur.execute("SELECT subscription_expires_at FROM users WHERE username=%s", (username,))
        r = cur.fetchone()
        now = datetime.datetime.now(datetime.timezone.utc)
        current = r[0] if (r and r[0] and r[0] > now) else now
        new_expiry = current + datetime.timedelta(days=days_to_add)
        cur.execute("UPDATE users SET subscription_expires_at=%s WHERE username=%s", (new_expiry, username))
        if cur.rowcount == 0:
            return json_response({"success": False, "message": "User not found"}, 404)

        _log_activity(cur, "admin", "adjust_subscription", {"username": username, "days": days_to_add}, request)
        conn.commit()
        return json_response({"success": True, "message": "Subscription adjusted"})
    except Exception as e:
        log.exception("admin_add_sub_time error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

@app.route("/admin/activity", methods=["GET"])
def admin_activity():
    g = _admin_guard()
    if g: return g

    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)

        qp = request.args or {}
        actor = qp.get("actor")
        action = qp.get("action")
        since = qp.get("since")
        until = qp.get("until")
        sort = (qp.get("sort") or "desc").lower()
        try:
            limit = int(qp.get("limit") or 50)
            offset = int(qp.get("offset") or 0)
        except Exception:
            limit, offset = 50, 0

        where = []
        params = []
        if actor:
            where.append("actor=%s"); params.append(actor)
        if action:
            where.append("action=%s"); params.append(action)
        if since:
            where.append("ts >= %s"); params.append(since)
        if until:
            where.append("ts <= %s"); params.append(until)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        order_sql = "ASC" if sort == "asc" else "DESC"

        cur.execute(
            f"SELECT id, ts, actor, action, details, ip, user_agent FROM activity_logs {where_sql} "
            f"ORDER BY ts {order_sql} LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        rows = cur.fetchall()
        if where:
            cur.execute(f"SELECT COUNT(1) FROM activity_logs {where_sql}", params)
        else:
            cur.execute("SELECT COUNT(1) FROM activity_logs")
        total = cur.fetchone()[0]

        items = []
        for r in rows:
            items.append({
                "id": r[0],
                "ts": r[1].isoformat() if r[1] else None,
                "actor": r[2],
                "action": r[3],
                "details": r[4],
                "ip": r[5],
                "user_agent": r[6],
            })
        return json_response({"ok": True, "items": items, "total": total})
    except Exception as e:
        log.exception("admin_activity error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

# ----------------------------------------------------------------------------
# Public Activity ingest
# ----------------------------------------------------------------------------
@app.route("/activity/log", methods=["POST"])
def activity_log():
    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)

        data = request.get_json(silent=True) or {}
        actor = (data.get("actor") or "system").strip()
        action = (data.get("action") or "event").strip()
        details = data.get("details") or {}
        _log_activity(cur, actor, action, details, request)
        conn.commit()
        return json_response({"ok": True})
    except Exception as e:
        log.exception("activity_log error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

# ----------------------------------------------------------------------------
# Billplz
# ----------------------------------------------------------------------------
def _billplz_basic_auth_header():
    token = (BILLPLZ_API_KEY or "").strip() + ":"
    b64 = base64.b64encode(token.encode("utf-8")).decode("utf-8")
    return f"Basic {b64}"

@app.route("/create-bill", methods=["POST"])
def create_bill():
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    username = payload.get("username")

    data = request.get_json(silent=True) or {}
    plan_name = data.get("planName", "Pro Plan")
    amount = str(data.get("amount", "1000"))  # cents
    plan_id = data.get("planId", "pro_1m")

    if BASE_URL:
        callback_url = f"{BASE_URL}/api/webhook-billplz"
        redirect_url = f"{BASE_URL}/payment-success.html"
    else:
        scheme = request.headers.get("X-Forwarded-Proto", "https")
        host = request.headers.get("X-Forwarded-Host", request.host)
        callback_url = f"{scheme}://{host}/webhook-billplz"
        redirect_url = f"{scheme}://{host}/payment-success.html"

    billplz_payload = {
        "collection_id": BILLPLZ_COLLECTION_ID,
        "email": f"{username}@example.com",
        "name": username,
        "amount": amount,
        "callback_url": callback_url,
        "redirect_url": redirect_url,
        "description": plan_name,
        "reference_1_label": "username",
        "reference_1": username,
        "reference_2_label": "plan",
        "reference_2": plan_id,
        "deliver": True,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": _billplz_basic_auth_header(),
    }

    try:
        req = urllib.request.Request(
            "https://www.billplz.com/api/v3/bills",
            method="POST",
            data=json.dumps(billplz_payload).encode("utf-8"),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            url = body.get("url")
            bill_id = str(body.get("id"))
            return json_response({"url": url, "bill_id": bill_id})
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        log.error("Billplz rejected: %s %s", e, err_body)
        return json_response({"error": "Payment service rejected", "detail": err_body}, 502)
    except Exception as e:
        log.exception("Billplz create-bill failed")
        return json_response({"error": "Payment service error", "detail": str(e)}, 502)

@app.route("/webhook-billplz", methods=["POST"])
def webhook_billplz():
    conn = cur = None
    try:
        if not BILLPLZ_X_SIGNATURE:
            log.error("BILLPLZ_X_SIGNATURE is not configured. Webhook is insecure.")
            return json_response({"error": "Webhook security not configured"}, 500)
            
        sig = request.headers.get("X-Signature", "")
        if not sig or sig != BILLPLZ_X_SIGNATURE:
            return json_response({"error": "Invalid signature"}, 401)

        data = request.form
        paid = str(data.get("paid")).lower() in ("true",)
        username = (data.get("reference_1") or "").strip()
        plan_id = (data.get("reference_2") or "").strip()

        if not (paid and username):
            _log_activity(None, "system", "webhook_invalid", {"reason": "not_paid_or_no_user", "data": dict(data)}, request)
            return json_response({"error": "invalid webhook"}, 400)

        days = 30
        if plan_id == "pro_3m":
            days = 365
        elif plan_id == "competent_2m":
            days = 180

        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)

        cur.execute("SELECT subscription_expires_at FROM users WHERE username=%s", (username,))
        r = cur.fetchone()
        now = datetime.datetime.now(datetime.timezone.utc)
        current = r[0] if (r and r[0] and r[0] > now) else now
        new_expiry = current + datetime.timedelta(days=days)
        cur.execute("UPDATE users SET subscription_expires_at=%s WHERE username=%s", (new_expiry, username))
        
        if cur.rowcount == 0:
            _log_activity(cur, "system", "webhook_user_not_found", {"username": username, "plan": plan_id}, request)
        else:
            _log_activity(cur, "system", "webhook_paid", {"username": username, "days": days, "plan": plan_id}, request)
        
        conn.commit()
        return json_response({"success": True})
    except Exception as e:
        log.exception("webhook-billplz error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

# ----------------------------------------------------------------------------
# Chat with Image (Existing functionality)
# ----------------------------------------------------------------------------
@app.route("/chat-with-image", methods=["POST"])
def chat_with_image():
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    username = payload.get("username")
    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)
        cur.execute("SELECT subscription_expires_at FROM users WHERE username=%s", (username,))
        r = cur.fetchone()
        if not r or not r[0] or r[0] < datetime.datetime.now(datetime.timezone.utc):
            return json_response({"error": "Active subscription required for image analysis."}, 403)
        if 'file' not in request.files:
            return json_response({"error": "No file part in the request"}, 400)
        file = request.files['file']
        if file.filename == '':
            return json_response({"error": "No selected file"}, 400)
        prompt = request.form.get('prompt', 'Please analyze this image.')
        if not gemini_available():
            return json_response({"error": "Gemini Vision service not configured"}, 503)
        genai.configure(api_key=GEMINI_API_KEY)
        vision_model = genai.GenerativeModel('gemini-pro-vision')
        image_bytes = file.read()
        img = Image.open(io.BytesIO(image_bytes))
        response = vision_model.generate_content([prompt, img])
        _log_activity(cur, username, "chat_with_image", {"prompt": prompt, "filename": file.filename}, request)
        conn.commit()
        return json_response({"success": True, "response": response.text})
    except Exception as e:
        log.exception("chat-with-image error")
        return json_response({"error": "Internal error during image processing", "detail": str(e)}, 500)
    finally:
        try:
            if cur: cur.close()
        except Exception:
            pass
        put_conn(conn)

# ----------------------------------------------------------------------------
# V1 - Multi-Agent Script Generation Workflow (NEW)
# ----------------------------------------------------------------------------
@app.route("/v1/projects", methods=["POST"])
def create_project():
    """Endpoint to create a new project and get initial creative concepts."""
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    username = payload.get("username")

    user_input = request.get_json(silent=True)
    if not user_input or "project_title" not in user_input or "video_length_sec" not in user_input:
        return json_response({"error": "Missing required fields: project_title, video_length_sec"}, 400)

    conn = None
    try:
        conn = get_conn()
        # 调用 services.py 中的业务逻辑
        # 注意：services函数目前是伪代码，调用会通过但不会做任何事
        project_id, creative_options = services.create_project_and_generate_creatives(
            db_conn=conn, 
            user_id=username, 
            user_input=user_input
        )
        return json_response({"project_id": project_id, "creative_options": creative_options}, 201)
    except (ValidationError, json.JSONDecodeError) as e:
        log.warning(f"Validation Error from Gemini: {e}")
        return json_response({"error": "AI response validation failed", "detail": str(e)}, 502) # Bad Gateway
    except Exception as e:
        log.exception("create_project error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)

@app.route("/v1/projects/<uuid:project_id>/select-creative", methods=["POST"])
def select_creative(project_id):
    """Endpoint for the user to select their preferred creative concept."""
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    
    data = request.get_json(silent=True) or {}
    creative_id = data.get("creative_id")
    if not creative_id:
        return json_response({"error": "creative_id is required"}, 400)
        
    conn = None
    try:
        conn = get_conn()
        # 调用 services.py 中的业务逻辑
        # 注意：services函数目前是伪代码，调用会通过但不会做任何事
        storyboard, qa_critique = services.select_creative_and_generate_storyboard(
            db_conn=conn,
            project_id=str(project_id),
            selected_creative_id=creative_id
        )
        return json_response({"storyboard": storyboard, "qa_critique": qa_critique})
    except (ValidationError, json.JSONDecodeError) as e:
        log.warning(f"Validation Error from Gemini for project {project_id}: {e}")
        return json_response({"error": "AI response validation failed", "detail": str(e)}, 502)
    except Exception as e:
        log.exception(f"select_creative error for project {project_id}")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)

# ----------------------------------------------------------------------------
# Main execution
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # This is used for local development.
    # For production, use a Gunicorn-like server.
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)