# -*- coding: utf-8 -*-
"""
PF System API - unified Flask app for Cloud Run
- Billplz callback uses HMAC-SHA256 via BILLPLZ_X_SIGNATURE_KEY
- callback_url: auto-derived from request headers (backend domain)
- redirect_url: FRONTEND_BASE_URL/payment-success.html (fallback to backend if unset)
- STRICT_SECRET_CHECK: refuse to start with default secrets when set to 1
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any
import io
import json
import hmac
import base64
import hashlib
import logging
import re
import datetime
import urllib.request
import urllib.error
from urllib.parse import urlencode
import uuid  # ★ for session_id canonicalization

# Pillow              (      )
from PIL import Image  # noqa: F401

from flask import Flask, request, jsonify, Response, redirect
from flask_cors import CORS, cross_origin
import psycopg2
import psycopg2.pool
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

#      
import services
from pydantic import ValidationError
from typing import Any, Dict, List, Optional

# Gemini SDK(       )
_GEM_ENABLED = False
try:
    import google.generativeai as genai  # noqa: F401
    _GEM_ENABLED = True
except Exception as e:
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
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")
DB_SOCKET_DIR = "/cloudsql"

#    BASE_URL       callback;       
BASE_URL = (os.getenv("BASE_URL") or "").rstrip("/")
#       :   redirect_url
FRONTEND_BASE_URL = (os.getenv("FRONTEND_BASE_URL") or "").rstrip("/")

# Billplz
BILLPLZ_API_KEY = os.getenv("BILLPLZ_API_KEY", "")
BILLPLZ_COLLECTION_ID = os.getenv("BILLPLZ_COLLECTION_ID", "")
#   :HMAC   
BILLPLZ_X_SIGNATURE_KEY = os.getenv("BILLPLZ_X_SIGNATURE_KEY", "")
#      :       (   ,      KEY    )
BILLPLZ_X_SIGNATURE_LEGACY = os.getenv("BILLPLZ_X_SIGNATURE", "")

# Gemini( )
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ----------------------------------------------------------------------------
# Secret self-check
# ----------------------------------------------------------------------------
STRICT_SECRET_CHECK = (os.getenv("STRICT_SECRET_CHECK", "0") == "1")
DEFAULT_SECRETS_IN_USE = (JWT_SECRET == "CHANGE_ME_SECRET" or ADMIN_PASSWORD == "CHANGE_ME_ADMIN")
ADMIN_LOCKDOWN = False

if DEFAULT_SECRETS_IN_USE:
    msg = "SECURITY WARNING: Default secrets in use. Please set JWT_SECRET and ADMIN_PASSWORD."
    if STRICT_SECRET_CHECK:
        log.critical(msg + " Refusing to start because STRICT_SECRET_CHECK=1.")
        raise RuntimeError("Refusing to start with default secrets. Configure JWT_SECRET and ADMIN_PASSWORD.")
    else:
        ADMIN_LOCKDOWN = True
        log.critical(msg + " Admin endpoints will be disabled until configured.")

# ----------------------------------------------------------------------------
# Flask app & helpers
# ----------------------------------------------------------------------------
app = Flask(__name__)
from health import health_bp
app.register_blueprint(health_bp)

# ===== CORS（一次性修好预检 + 带凭据）===========================
# ★ 允许带 cookie/Authorization 的跨域；必须是具体来源，不能用 '*'
#   这里把你的 vercel 线上域、以及 FRONTEND_BASE_URL（如果设置）加入白名单
DEFAULT_ALLOWED = {
    "https://pfcreativeaistudio.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}
# Support comma-separated extra origins from env (e.g., preview domains, custom domains)
extra_origins = {o.strip() for o in os.getenv("FRONTEND_BASE_URLS", "").split(",") if o.strip()}
ALLOWED_ORIGINS = list(DEFAULT_ALLOWED | extra_origins)

CORS(
    app,
    resources={r"/*": {"origins": ALLOWED_ORIGINS}},
    supports_credentials=True,                 # ★ 关键：返回 Access-Control-Allow-Credentials: true
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization", "Content-Type",
        "X-Admin-Password", "X-Requested-With"
    ],
    expose_headers=["Content-Type"],
    max_age=86400
)

# ★ 保底：所有响应都带上 Allow-Credentials，避免 401/错误时少头导致浏览器拦截
@app.after_request
def _ensure_cors_headers(resp):
    resp.headers.setdefault("Access-Control-Allow-Credentials", "true")
    return resp

# Request logging for debugging CORS and API calls
@app.before_request
def _log_request():
    log.info(f"--- REQUEST --- {request.method} {request.path} | Origin: {request.headers.get('Origin', 'N/A')} | User-Agent: {request.headers.get('User-Agent', 'N/A')[:80]}")
# ============================================================

def json_response(payload, status=200):
    return app.response_class(
        response=json.dumps(payload, ensure_ascii=False),
        status=status,
        mimetype="application/json",
    )

# ----------------------------------------------------------------------------
# Admin guard helper
# ----------------------------------------------------------------------------
def _admin_guard():
    if ADMIN_LOCKDOWN:
        return json_response({"error": "Admin endpoints disabled due to insecure defaults. Set JWT_SECRET & ADMIN_PASSWORD."}, 503)
    if request.headers.get("X-Admin-Password") != ADMIN_PASSWORD:
        return json_response({"error": "Unauthorized"}, 401)
    return None

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

# ----------------------------------------------------------------------------
# ★ Session ID canonicalization (accept any string, map to stable UUIDv5)
# ----------------------------------------------------------------------------
def _canon_session_uuid(s: str) -> str:
    s = (s or "").strip()
    if not s:
        # empty → generate a random uuid4 so it still works
        return str(uuid.uuid4())
    try:
        # if already a valid uuid string, keep it
        return str(uuid.UUID(s))
    except Exception:
        # stable mapping from arbitrary string to uuid (deterministic)
        return str(uuid.uuid5(uuid.NAMESPACE_URL, s))

# ----------------------------------------------------------------------------
# Director Orchestrator Helpers (lightweight, server-side)
# ----------------------------------------------------------------------------

DIRECTOR_REQUIRED_SLOTS = ["goal","audience","platform","duration_sec","key_message","cta"]

def _director_get_session(conn, session_id: str):
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, state, selections, step, project_id FROM sessions WHERE id::text = %s", (session_id,))
    row = cur.fetchone()
    if not row:
        return None
    return {
        "id": str(row[0]),
        "user_id": row[1],
        "state": row[2],
        "selections": row[3] or {},
        "step": row[4],
        "project_id": str(row[5]) if row[5] else None
    }

def _director_create_session(conn, session_id: str, user_id: str):
    cur = conn.cursor()
    try:
        # try inserting with provided (already canonicalized) uuid string
        cur.execute("""
            INSERT INTO sessions (id, user_id, state, selections, step)
            VALUES (%s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (id) DO NOTHING
        """, (session_id, user_id, 'G1', json.dumps({}), 1))
    except Exception as e:
        # fallback: let DB generate default UUID if type casting fails
        cur.execute("""
            INSERT INTO sessions (user_id, state, selections, step)
            VALUES (%s, %s, %s::jsonb, %s)
            ON CONFLICT DO NOTHING
        """, (user_id, 'G1', json.dumps({}), 1))
    conn.commit()

def _director_update_session(conn, session_id: str, selections_delta: Dict[str, Any] = None, state: Optional[str] = None, step: Optional[int] = None, project_id: Optional[str] = None):
    sels_sql = json.dumps(selections_delta or {})
    cur = conn.cursor()
    cur.execute("SELECT selections FROM sessions WHERE id::text = %s", (session_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError("Session not found")
    current = row[0] or {}
    merged = current.copy()
    merged.update(selections_delta or {})
    fields = ["selections=%s::jsonb"]
    params = [json.dumps(merged)]
    if state:
        fields.append("state=%s")
        params.append(state)
    if step is not None:
        fields.append("step=%s")
        params.append(step)
    if project_id is not None:
        fields.append("project_id=%s::uuid")
        params.append(project_id)
    params.append(session_id)
    sql = "UPDATE sessions SET " + ", ".join(fields) + ", updated_at=NOW() WHERE id::text=%s"
    cur.execute(sql, params)
    conn.commit()

def _slots_ready(slots: Dict[str, Any]) -> bool:
    for k in DIRECTOR_REQUIRED_SLOTS:
        if not slots.get(k):
            return False
    try:
        if int(slots.get("duration_sec", 0)) <= 0:
            return False
    except Exception:
        return False
    return True

PLATFORM_ALIASES = {
    "tiktok": "TikTok",
    "douyin": "TikTok",
    "reels": "Instagram Reels",
    "instagram": "Instagram Reels",
    "youtube": "YouTube Shorts",
    "shorts": "YouTube Shorts",
    "facebook": "Facebook",
    "fb": "Facebook"
}

TONE_VOCAB = {"playful","fun","energetic","heartwarming","dramatic","epic","serious","inspirational","whimsical"}
STYLE_VOCAB = {"cinematic","ugc","asmr","documentary","vlog","retro","surreal","minimal","luxury"}

def _parse_slots_from_text(text: str, current: Dict[str, Any]) -> Dict[str, Any]:
    text_l = (text or "").lower()
    upd: Dict[str, Any] = {}

    # duration
    m = re.search(r'(\d+)\s*(s|sec|secs|second|seconds)\b', text_l)
    if m:
        try:
            upd["duration_sec"] = int(m.group(1))
        except Exception:
            pass
    m = re.search(r'(\d+)\s*(m|min|mins|minute|minutes)\b', text_l)
    if m:
        try:
            upd["duration_sec"] = int(m.group(1)) * 60
        except Exception:
            pass
    # common quick durations
    for d in (15, 20, 30, 45, 60):
        if re.search(rf'\b{d}\s*(s|sec|seconds)?\b', text_l):
            upd.setdefault("duration_sec", d)

    # platform
    for key, norm in PLATFORM_ALIASES.items():
        if re.search(rf'\b{re.escape(key)}\b', text_l):
            upd["platform"] = norm
            break

    # tone & style
    found_tone = [w for w in TONE_VOCAB if re.search(rf'\\b{re.escape(w)}\\b', text_l)]
    if found_tone:
        upd["tone"] = ", ".join(sorted(set(found_tone)))
    found_style = [w for w in STYLE_VOCAB if re.search(rf'\\b{re.escape(w)}\\b', text_l)]
    if found_style:
        upd["style"] = ", ".join(sorted(set(found_style)))

    # naive CTA and message cues
    if "cta" in text_l or "call to action" in text_l:
        # extract after colon if present
        m = re.search(r'(cta|call to action)\s*[:\-]\s*([^\n]+)', text_l)
        if m:
            upd["cta"] = m.group(2).strip()

    # goal shortcut words
    if "awareness" in text_l and not current.get("goal"):
        upd["goal"] = "Brand awareness"
    if "conversion" in text_l and not current.get("goal"):
        upd["goal"] = "Drive conversions"

    return upd

def _next_prompt(slots: Dict[str, Any]) -> Dict[str, str]:
    if not slots.get("goal"):
        return {
            "assistant_message": "What is your goal for this video?",
            "director_recommendation": "Keep it simple: brand awareness, conversions, event promo, app installs.",
        }
    if not slots.get("audience"):
        return {
            "assistant_message": "Who is the target audience?",
            "director_recommendation": "Think demographic + intent, e.g., Gen-Z students in KL or young parents seeking healthy snacks.",
        }
    if not slots.get("platform") or not slots.get("duration_sec"):
        return {
            "assistant_message": "Which platform and duration do you want?",
            "director_recommendation": "Examples: TikTok 15s, Instagram Reels 30s, YouTube Shorts 60s.",
        }
    if not slots.get("key_message"):
        return {
            "assistant_message": "What's the key message or single most important takeaway?",
            "director_recommendation": "One sentence; focus on the benefit or value proposition.",
        }
    if not slots.get("cta"):
        return {
            "assistant_message": "What is the call to action (CTA)?",
            "director_recommendation": "Examples: Order now, Visit the store, Use code PF30, Click to learn more.",
        }
    if not slots.get("tone") or not slots.get("style"):
        return {
            "assistant_message": "Any preferred tone or style?",
            "director_recommendation": "Tone: playful/epic/heartwarming; Style: cinematic/UGC/ASMR/documentary.",
        }
    if not slots.get("assets"):
        return {
            "assistant_message": "Any assets or references to include? (links, brand rules)",
            "director_recommendation": "You can paste URLs or say 'none'.",
        }
    if not slots.get("constraints"):
        return {
            "assistant_message": "Any constraints or must-avoid items? (budget, legal, safety)",
            "director_recommendation": "Example: No text overlays; follow halal/brand safety rules.",
        }
    # ready to review brief
    brief_lines = [
        f"Goal: {slots.get('goal')}",
        f"Audience: {slots.get('audience')}",
        f"Platform: {slots.get('platform')} | Duration: {slots.get('duration_sec')}s",
        f"Key message: {slots.get('key_message')}",
        f"CTA: {slots.get('cta')}",
        f"Tone: {slots.get('tone')} | Style: {slots.get('style')}",
    ]
    if slots.get("assets"):
        brief_lines.append(f"Assets/Refs: {slots.get('assets')}")
    if slots.get("constraints"):
        brief_lines.append(f"Constraints: {slots.get('constraints')}")
    return {
        "assistant_message": "Here is your brief:\n" + "\n".join(brief_lines) + "\nType 'looks good' to proceed or edit any field.",
        "director_recommendation": "Say 'looks good' to continue; or update a field (e.g., 'CTA: Visit our Bukit Bintang store').",
    }

def _ready_flags(slots: Dict[str, Any], project_id: Optional[str]) -> Dict[str, bool]:
    return {
        "can_generate_creatives": _slots_ready(slots),
        "can_storyboard": bool(project_id),
        "can_build_veo3_prompt": bool(project_id),  # becomes true after storyboard in UI
        "can_export": bool(project_id),
    }

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

    #    
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")  # gen_random_uuid()
    except Exception:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id TEXT NOT NULL,
            project_title TEXT NOT NULL,
            user_input JSONB NOT NULL,
            video_length_sec INT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS creative_options (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
            option_index INT NOT NULL,
            title TEXT NOT NULL,
            logline TEXT NOT NULL,
            why_it_works TEXT NOT NULL,
            is_selected BOOLEAN DEFAULT FALSE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS storyboards (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
            creative_option_id UUID REFERENCES creative_options(id) ON DELETE SET NULL,
            scenes JSONB NOT NULL,
            qa_status TEXT CHECK (qa_status IN ('passed','failed')) NOT NULL,
            qa_feedback TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'init',
            selections JSONB NOT NULL DEFAULT '{}'::jsonb,
            step INT NOT NULL DEFAULT 1,
            project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blueprints (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
            storyboard_id UUID REFERENCES storyboards(id) ON DELETE CASCADE,
            scene_number INT NOT NULL,
            content_json JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
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
# Gemini helpers(legacy)
# ----------------------------------------------------------------------------
def gemini_available():
    return _GEM_ENABLED and bool(GEMINI_API_KEY)

def call_gemini(prompt, system_instruction=None):
    if not gemini_available():
        raise RuntimeError("Gemini not configured")
    import google.generativeai as genai  #              
    genai.configure(api_key=GEMINI_API_KEY)
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
    # 带 revision，方便你在监控/日志确认活跃修订
    app.logger.info("--- HEALTHZ --- /healthz hit")
    return json_response({
        "status": "ok",
        "ts": datetime.datetime.utcnow().isoformat(),
        "revision": os.getenv("K_REVISION", "")
    })

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
        conn.commit()
        return json_response({"ok": True})
    except Exception as e:
        log.exception("healthz_db error")
        return json_response({"ok": False, "error": str(e)}, 500)
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        put_conn(conn)

# ----------------------------------------------------------------------------
# Admin password verify
# ----------------------------------------------------------------------------
@app.route("/admin/verify-password", methods=["POST"])
def admin_verify():
    if ADMIN_LOCKDOWN:
        return json_response({"success": False, "error": "Admin disabled due to insecure defaults"}, 503)
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
            if cur:
                cur.close()
        except Exception:
            pass
        put_conn(conn)

@app.route("/login", methods=["POST"])
def login():
    # Log request details for debugging CORS and authentication flow
    log.info(f"--- LOGIN REQUEST --- Method: {request.method}, Origin: {request.headers.get('Origin', 'N/A')}, User-Agent: {request.headers.get('User-Agent', 'N/A')[:100]}")
    
    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        
        log.info(f"--- LOGIN ATTEMPT --- Username: {username}, Password length: {len(password)}")
        
        cur.execute("SELECT password FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        if not row or not check_password_hash(row[0], password):
            log.info(f"--- LOGIN FAILED --- Invalid credentials for user: {username}")
            return json_response({"error": "Invalid credentials"}, 401)
        
        token = _jwt_create(username)
        cur.execute("UPDATE users SET active_token=%s WHERE username=%s", (token, username))
        _log_activity(cur, username, "login_success", {}, request)
        conn.commit()
        
        log.info(f"--- LOGIN SUCCESS --- User: {username}, Token generated")
        return json_response({"success": True, "token": token})
    except Exception as e:
        log.exception("login error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur:
                cur.close()
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
            if cur:
                cur.close()
        except Exception:
            pass
        put_conn(conn)

# ----------------------------------------------------------------------------
# Admin APIs
# ----------------------------------------------------------------------------
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
            if cur:
                cur.close()
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
            if cur:
                cur.close()
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
            if cur:
                cur.close()
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
            if cur:
                cur.close()
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
            if cur:
                cur.close()
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
            if cur:
                cur.close()
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
            if cur:
                cur.close()
        except Exception:
            pass

# ----------------------------------------------------------------------------
# Billplz Helpers & APIs
# ----------------------------------------------------------------------------
def _billplz_basic_auth_header():
    token = (BILLPLZ_API_KEY or "").strip() + ":"
    b64 = base64.b64encode(token.encode("utf-8")).decode("utf-8")
    return f"Basic {b64}"


# ---------------------------------------------------------------------
# Plans catalog (server-side source of truth)
# ---------------------------------------------------------------------
PLANS_CATALOG = [
    {"id": "p1m", "name": "1 Month",  "days": 30,  "amount_cents": 9900},
    {"id": "p6m", "name": "6 Months", "days": 180, "amount_cents": 19800},
    {"id": "p12m","name": "12 Months","days": 365, "amount_cents": 29700},
    # Legacy aliases supported for compatibility
    {"id": "starter_1m",   "name": "1 Month",  "days": 30,  "amount_cents": 9900},
    {"id": "competent_2m", "name": "2 Months", "days": 60,  "amount_cents": 14900},
    {"id": "pro_3m",       "name": "3 Months", "days": 90,  "amount_cents": 19900},
    {"id": "pro_12m",      "name": "12 Months","days": 365, "amount_cents": 29700},
]

def resolve_plan(plan_id: str):
    for p in PLANS_CATALOG:
        if p["id"] == plan_id:
            return p
    return None

def _current_backend_base():
    """                  (Cloud Run     )."""
    scheme = request.headers.get("X-Forwarded-Proto", "https")
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{scheme}://{host}"

def _normalize_form_for_hmac(form_dict: dict) -> bytes:
    """   (   x_signature)  key   ,    key=value&...    HMAC."""
    items = [(k, v) for k, v in form_dict.items() if k.lower() != "x_signature"]
    items.sort(key=lambda kv: kv[0])
    return urlencode(items, doseq=False).encode("utf-8")

def verify_billplz_signature(req, key_plain: str) -> bool:
    """
       X Signature Key   HMAC-SHA256   .      ,      :
    A)    body(bytes)
    B)        (   x_signature,  key   )
    C)    billplz.* / billplz[xxx]      
    """
    if not key_plain:
        return False

    key = key_plain.encode("utf-8")
    provided = (req.form.get("x_signature") or req.headers.get("X-Signature") or "").strip().lower()
    if not provided:
        return False

    # A: raw body
    raw_body = req.get_data(cache=True, as_text=False) or b""
    cand = hmac.new(key, raw_body, hashlib.sha256).hexdigest().lower()
    if hmac.compare_digest(cand, provided):
        return True

    # B: normalized full form
    norm = _normalize_form_for_hmac(req.form.to_dict(flat=True))
    cand = hmac.new(key, norm, hashlib.sha256).hexdigest().lower()
    if hmac.compare_digest(cand, provided):
        return True

    # C: subset billplz.* / billplz[...]
    subset = {}
    for k, v in req.form.items():
        lk = k.lower()
        if lk.startswith("billplz.") or lk.startswith("billplz["):
            if lk != "x_signature":
                subset[k] = v
    if subset:
        norm2 = _normalize_form_for_hmac(subset)
        cand = hmac.new(key, norm2, hashlib.sha256).hexdigest().lower()
        if hmac.compare_digest(cand, provided):
            return True

    log.warning("Billplz HMAC not matched. provided=%s...", provided[:10])
    return False

@app.route("/create-bill", methods=["POST"])
def create_bill():
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    # ★ username 兼容 user_id
    username = (payload.get("username") or payload.get("user_id") or "guest")

    data = request.get_json(silent=True) or {}
    plan_name = data.get('planName')
    amount = data.get('amount')
    plan_id = data.get('planId') or data.get('plan')

    backend_base = _current_backend_base()
    
    # Resolve plan details from server catalog if not provided by client
    plan = resolve_plan((plan_id or '').strip()) if plan_id else None
    if plan:
        if not plan_name: 
            plan_name = plan['name']
        if not amount:
            amount = str(plan['amount_cents'])
    # Final fallbacks
    plan_name = plan_name or 'Pro Plan'
    amount = str(amount or '1000')
    plan_id = (plan_id or 'p1m')
    callback_url = f"{backend_base}/webhook-billplz"
    # redirect      ;           
    if FRONTEND_BASE_URL:
        redirect_url = f"{FRONTEND_BASE_URL}/payment-success.html"
    else:
        redirect_url = f"{backend_base}/payment-success.html"

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
    headers = {"Content-Type": "application/json", "Authorization": _billplz_basic_auth_header()}

    try:
        req = urllib.request.Request(
            "https://www.billplz.com/api/v3/bills", method="POST",
            data=json.dumps(billplz_payload).encode("utf-8"), headers=headers,
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
        #   :HMAC   
        if BILLPLZ_X_SIGNATURE_KEY:
            if not verify_billplz_signature(request, BILLPLZ_X_SIGNATURE_KEY):
                log.warning("Billplz webhook invalid HMAC signature")
                return json_response({"error": "Invalid signature"}, 401)
        else:
            #      :      KEY    (   )
            sig = request.headers.get("X-Signature", "") or request.form.get("x_signature", "")
            if not (sig and BILLPLZ_X_SIGNATURE_LEGACY and sig == BILLPLZ_X_SIGNATURE_LEGACY):
                log.warning("Billplz webhook rejected (no key configured and legacy check failed)")
                return json_response({"error": "Invalid signature (legacy)"}, 401)

        data = request.form
        paid = str(data.get("paid")).lower() in ("true",)
        username = (data.get("reference_1") or "").strip()
        plan_id = (data.get("reference_2") or "").strip()
        if not (paid and username):
            log.warning("Billplz webhook invalid payload: %s", dict(data))
            return json_response({"error": "invalid webhook"}, 400)

        #       (         )
        days = 30
        # Map plan to days using catalog
        p = resolve_plan(plan_id) if plan_id else None
        if p:
            days = int(p['days'])

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
        log.exception("webhook_billplz error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass

# ----------------------------------------------------------------------------
# V1 - Multi-Agent Script Generation Workflow
# ----------------------------------------------------------------------------
@app.route("/v1/projects", methods=["POST", "OPTIONS"])
@cross_origin()
def create_project():
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
        project_id, creative_options = services.create_project_and_generate_creatives(
            db_conn=conn,
            user_id=username,
            user_input=user_input
        )
        return json_response({"project_id": project_id, "creative_options": creative_options}, 201)
    except ImportError as e:
        log.warning("AI unavailable in /v1/projects: %s", e)
        return json_response({"error": "AI unavailable", "detail": str(e)}, 503)
    except (ValidationError, json.JSONDecodeError) as e:
        log.warning(f"Validation Error from Gemini: {e}")
        return json_response({"error": "AI response validation failed", "detail": str(e)}, 502)
    except Exception as e:
        log.exception("create_project error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)

# ★ 新增：Dashboard 用的「最近项目列表」
@app.route("/v1/projects", methods=["GET", "OPTIONS"])
@cross_origin()
def list_projects():
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    username = payload.get("username")
    recent = request.args.get("recent", default=6, type=int)

    conn = cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ensure_schema(cur)
        cur.execute("""
            SELECT id, project_title, video_length_sec, created_at
            FROM projects
            WHERE user_id=%s
            ORDER BY created_at DESC NULLS LAST
            LIMIT %s
        """, (username, recent))
        rows = cur.fetchall()
        items = [{
            "id": str(r[0]),
            "project_title": r[1],
            "video_length_sec": r[2],
            "created_at": r[3].isoformat() if r[3] else None
        } for r in rows]
        return json_response({"items": items})
    except Exception as e:
        log.exception("list_projects error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        put_conn(conn)

@app.route("/v1/projects/<uuid:project_id>/select-creative", methods=["POST", "OPTIONS"])
@cross_origin()
def select_creative(project_id):
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
        storyboard, qa_critique = services.select_creative_and_generate_storyboard(
            db_conn=conn,
            project_id=str(project_id),
            selected_creative_id=creative_id
        )
        return json_response({"storyboard": storyboard, "qa_critique": qa_critique})
    except ImportError as e:
        log.warning("AI unavailable in select-creative: %s", e)
        return json_response({"error": "AI unavailable", "detail": str(e)}, 503)
    except (ValidationError, json.JSONDecodeError) as e:
        log.warning(f"Validation Error from Gemini for project {project_id}: {e}")
        return json_response({"error": "AI response validation failed", "detail": str(e)}, 502)
    except Exception as e:
        log.exception(f"select_creative error for project {project_id}")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)

@app.route("/v1/sessions", methods=["POST", "OPTIONS"])
@cross_origin()
def create_session_route():
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    username = payload.get("username")

    data = request.get_json(silent=True) or {}
    project_title = (data.get("project_title") or "").strip()
    video_length_sec = data.get("video_length_sec")
    user_input = data.get("user_input") or {}

    if not project_title or video_length_sec is None:
        return json_response({"error": "Missing required fields: project_title, video_length_sec"}, 400)

    conn = None
    try:
        conn = get_conn()
        resp = services.create_session(
            db_conn=conn,
            user_id=username,
            user_input={
                "project_title": project_title,
                "video_length_sec": video_length_sec,
                **user_input
            }
        )
        return json_response({"success": True, **resp}, 201)
    except Exception as e:
        log.exception("create_session_route error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)

@app.route("/v1/sessions/<uuid:session_id>/next", methods=["POST", "OPTIONS"])
@cross_origin()
def advance_session_route(session_id):
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)

    data = request.get_json(silent=True) or {}
    user_choice = data.get("choice") or {}

    conn = None
    try:
        conn = get_conn()
        resp = services.advance_session(
            db_conn=conn,
            session_id=str(session_id),
            user_choice=user_choice
        )
        return json_response({"success": True, **resp})
    except Exception as e:
        log.exception("advance_session_route error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)

@app.route("/v1/projects/<uuid:project_id>/finalize", methods=["POST", "OPTIONS"])
@cross_origin()
def finalize_project(project_id):
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)

    conn = None
    try:
        conn = get_conn()
        result = services.release_gate_finalize(
            db_conn=conn,
            project_id=str(project_id)
        )
        return json_response({"success": True, "result": result})
    except ImportError as e:
        log.warning("AI unavailable in finalize: %s", e)
        return json_response({"error": "AI unavailable", "detail": str(e)}, 503)
    except Exception as e:
        log.exception("finalize_project error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)

# Render/Status(  )
@app.route("/v1/projects/<uuid:project_id>/render", methods=["POST", "OPTIONS"])
@cross_origin()
def render_project(project_id):
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    return json_response({"success": True, "total": 0})

@app.route("/v1/projects/<uuid:project_id>/render/status", methods=["GET", "OPTIONS"])
@cross_origin()
def render_status(project_id):
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    return json_response({"success": True, "items": []})

#   
@app.route("/v1/projects/<uuid:project_id>/export", methods=["GET", "OPTIONS"])
@cross_origin()
def export_project(project_id):
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)

    conn = None
    try:
        conn = get_conn()
        zip_bytes = services.build_export_zip(conn, str(project_id))
        headers = {
            "Content-Type": "application/zip",
            "Content-Disposition": f'attachment; filename="pf-package-{project_id}.zip"',
            "Cache-Control": "no-store",
        }
        return Response(zip_bytes, status=200, headers=headers)
    except ValueError as ve:
        return json_response({"error": str(ve)}, 404)
    except Exception as e:
        log.exception("export_project error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)

# ----------------------------------------------------------------------------
# Main execution

@app.route("/v1/plans", methods=["GET"])
@cross_origin()
def v1_plans():
    # Expose the public catalog (id, name, price in major units)
    out = []
    for p in PLANS_CATALOG:
        out.append({
            "id": p["id"],
            "name": p["name"],
            "days": p["days"],
            "price": round(p["amount_cents"]/100, 2),
        })
    return json_response(out)

# ----------------------------------------------------------------------------



# ===== Appendix Library Loader =====
_APPENDIX_CACHE = None

def _load_appendix_library():
    """Load appendix_library.json once and cache it. Fallback to defaults if missing."""
    global _APPENDIX_CACHE
    if _APPENDIX_CACHE is not None:
        return _APPENDIX_CACHE
    import os, json
    search_paths = [
        os.path.join(os.getcwd(), "appendix_library.json"),
        os.path.join(os.path.dirname(__file__), "appendix_library.json"),
        "/workspace/appendix_library.json",
    ]
    for pth in search_paths:
        if os.path.exists(pth):
            with open(pth, "r", encoding="utf-8") as f:
                _APPENDIX_CACHE = json.load(f)
                break
    if _APPENDIX_CACHE is None:
        _APPENDIX_CACHE = {
            "goals": [{"id":"awareness","label":"Brand awareness"},{"id":"conversions","label":"Drive conversions"}],
            "tones": ["playful","energetic"],
            "styles": ["cinematic","ugc"],
            "platforms": [{"id":"tiktok","label":"TikTok","durations_sec":[15,30,60],"aspect_ratio":"9:16"}],
            "comedy_substyles": ["slapstick","situational"],
            "camera_moves": ["push-in","dolly"],
            "narrative_templates": [{"id":"hook-build-payoff","label":"Hook → Build → Payoff","beats":[{"name":"Hook"},{"name":"Build"},{"name":"Payoff"}]}],
            "veo_blueprint_rules": {"text_free": True, "language": "English", "negative_prompt": ["no on-screen text"]}
        }
    return _APPENDIX_CACHE





def _next_prompt_v2(slots: Dict[str, Any]) -> Dict[str, Any]:
    lib = _load_appendix_library()
    if not slots.get("goal"):
        return {
            "step_label": "Step 1: Goal (1/8)",
            "assistant_message": "What is your goal for this video?",
            "options": [g["label"] for g in lib.get("goals", [])] or ["Brand awareness","Drive conversions","Event promo","App installs"],
            "directors_recommendation": "Pick one goal only to keep the edit tight. For 'viral', choose Brand awareness.",
        }
    if not slots.get("audience"):
        return {
            "step_label": "Step 2: Audience (2/8)",
            "assistant_message": "Who is the target audience?",
            "options": ["Gen-Z in Malaysia","Young parents","Foodies","Office workers","University students"],
            "directors_recommendation": "Name one concrete group (age + interest + location).",
        }
    if not slots.get("platform") or not slots.get("duration_sec"):
        durs = []
        plat_opts = []
        for p in lib.get("platforms", []):
            plat_opts.append(p["label"])
            durs.extend(p.get("durations_sec", []))
        durs = sorted(set(durs))[:6] or [15,30,45,60]
        return {
            "step_label": "Step 3: Platform & Duration (3/8)",
            "assistant_message": "Which platform and duration do you want?",
            "options": [f"{plat} · {d}s" for plat in plat_opts for d in durs][:12],
            "directors_recommendation": "For fast comedy on TikTok, 20–40s works well.",
        }
    if not slots.get("key_message"):
        return {
            "step_label": "Step 4: Key Message (4/8)",
            "assistant_message": "What is the single key message?",
            "options": ["Save RM50 today","Faster than rivals","Made in Malaysia","Halal certified","Limited-time bundle"],
            "directors_recommendation": "Keep it to 1 line; we will reinforce it visually, not with on-screen text.",
        }
    if not slots.get("cta"):
        return {
            "step_label": "Step 5: CTA (5/8)",
            "assistant_message": "What is the call-to-action?",
            "options": ["DM us","Shop now","Book a demo","Visit our website","Click the link"],
            "directors_recommendation": "One clear action only. We will place it in the payoff beat.",
        }
    if not slots.get("tone") or not slots.get("style"):
        return {
            "step_label": "Step 6: Tone & Style (6/8)",
            "assistant_message": "Any preferred tone and style?",
            "options": [f"Tone: {t}" for t in lib.get("tones", [])] + [f"Style: {s}" for s in lib.get("styles", [])],
            "directors_recommendation": "For comedy UGC on TikTok, try Tone: playful + Style: UGC.",
        }
    if not slots.get("assets"):
        return {
            "step_label": "Step 7: Assets (7/8)",
            "assistant_message": "Any assets or references to include? (links, brand rules)",
            "options": ["No assets","Logo only","Product images","Competitor references","Brand color palette"],
            "directors_recommendation": "Paste links; we will not show on-screen text per text-free policy.",
        }
    if not slots.get("constraints"):
        return {
            "step_label": "Step 8: Constraints (8/8)",
            "assistant_message": "Any constraints or must-avoid items?",
            "options": ["No text overlays","No music with lyrics","Keep it halal-safe","Budget-friendly props","No shaky cam"],
            "directors_recommendation": "If unsure, choose 'No text overlays' and 'Keep it halal-safe'.",
        }
    return {
        "step_label": "Brief complete",
        "assistant_message": "Great. Brief confirmed. Say 'generate blueprint' to build the VEO prompt.",
        "options": ["generate blueprint"],
        "directors_recommendation": "We will use Hook → Build → Payoff and keep it text-free.",
    }





@app.route("/v1/director/library", methods=["GET","OPTIONS"])
@cross_origin()
def director_library():
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        return json_response(_load_appendix_library())
    except Exception as e:
        return json_response({"error":"Failed to load library","detail":str(e)}, 500)





@app.route("/v1/director/blueprint", methods=["POST","OPTIONS"])
@cross_origin()
def director_blueprint():
    if request.method == "OPTIONS":
        return ("", 204)
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    body = request.get_json(silent=True) or {}
    raw_session_id = (body.get("session_id") or "").strip()
    if not raw_session_id:
        return json_response({"error":"Missing session_id"}, 400)
    session_id = _canon_session_uuid(raw_session_id)
    conn = None
    try:
        conn = get_conn()
        sess = _director_get_session(conn, session_id)
        if not sess:
            return json_response({"error":"Session not found"}, 404)
        slots = sess["selections"] or {}
        lib = _load_appendix_library()
        goal = slots.get("goal") or "Brand awareness"
        platform = slots.get("platform") or "tiktok"
        try:
            duration = int(slots.get("duration_sec") or 30)
        except Exception:
            duration = 30
        tone = slots.get("tone") or "playful"
        style = slots.get("style") or "ugc"
        key_msg = slots.get("key_message") or "Strong hook in first 2s"
        cta = slots.get("cta") or "DM us"
        rules = lib.get("veo_blueprint_rules", {})
        beats = lib.get("narrative_templates",[{}])[0].get("beats", [{"name":"Hook"},{"name":"Build"},{"name":"Payoff"}])
        total = max(duration, 15)
        hook_sec = max(int(total*0.2), 3)
        payoff_sec = max(int(total*0.2), 3)
        build_sec = max(total - hook_sec - payoff_sec, 6)
        blueprint = {
            "meta": {"platform": platform, "duration_sec": total, "tone": tone, "style": style, "text_free": bool(rules.get("text_free", True))},
            "overview": f"Goal: {goal}. Key message: {key_msg}. CTA: {cta}. Text-free policy enforced.",
            "beats": [
                {"name": beats[0].get("name","Hook"), "secs": hook_sec, "direction": "Grab attention visually in 2s; no on-screen text."},
                {"name": beats[1].get("name","Build"), "secs": build_sec, "direction": "Escalate the premise; include product claim or gag."},
                {"name": beats[2].get("name","Payoff"), "secs": payoff_sec, "direction": f"Punchline + CTA ('{cta}')."},
            ],
            "negative_prompt": rules.get("negative_prompt", []),
        }
        return json_response({"blueprint": blueprint})
    except Exception as e:
        log.exception("director_blueprint error")
        return json_response({"error":"Internal error","detail":str(e)}, 500)
    finally:
        put_conn(conn)





# ===== Conversation Memory (DB tables + helpers) =====




def director_session_get():
    if request.method == "OPTIONS":
        return ("", 204)
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    session_id = request.args.get("session_id","").strip()
    if not session_id:
        return json_response({"error":"Missing session_id"}, 400)
    conn = None
    try:
        conn = get_conn()
        sess = _director_get_session(conn, _canon_session_uuid(session_id))
        if not sess:
            return json_response({"error":"Session not found"}, 404)
        msgs = list(reversed(_director_get_recent_messages(conn, sess["id"], limit=20)))
        return json_response({"session_id": sess["id"], "selections": sess.get("selections") or {}, "messages": msgs})
    except Exception as e:
        log.exception("director_session_get error")
        return json_response({"error":"Internal error","detail":str(e)}, 500)
    finally:
        put_conn(conn)





@app.route("/v1/director/reset", methods=["POST","OPTIONS"])
@cross_origin()
def director_session_reset():
    if request.method == "OPTIONS":
        return ("", 204)
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    body = request.get_json(silent=True) or {}
    sid = (body.get("session_id") or "").strip()
    conn = None
    try:
        conn = get_conn()
        if sid:
            cur = conn.cursor()
            cur.execute("UPDATE director_sessions SET archived=TRUE WHERE id=%s", (_canon_session_uuid(sid),))
            conn.commit()
            cur.close()
        new_sess = _director_create_session(conn, None, user_id=payload.get("uid"))
        return json_response({"session_id": new_sess["id"]})
    except Exception as e:
        log.exception("director_session_reset error")
        return json_response({"error":"Internal error","detail":str(e)}, 500)
    finally:
        put_conn(conn)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)

# ----------------------------------------------------------------------------
# Director endpoints (non-breaking addition; front-end uses /v1/director/*)
# ----------------------------------------------------------------------------

@app.route("/v1/director/chat", methods=["POST", "OPTIONS"])
@cross_origin()

def director_chat():
    if request.method == "OPTIONS":
        return ("", 204)

    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)

    body = request.get_json(silent=True) or {}
    raw_session_id = (body.get("session_id") or "").strip()
    user_text = (body.get("user_text") or "").strip()

    conn = None
    try:
        conn = get_conn()
        _ensure_director_tables(conn)

        sess = _director_get_or_create_active_session(conn, user_id=payload.get("uid"), session_id=_canon_session_uuid(raw_session_id) if raw_session_id else None)
        session_id = sess["id"]

        if user_text:
            _director_append_message(conn, session_id, "user", user_text)

        slots = dict((sess.get("selections") or {}))

        parsed = _parse_slots_from_text(user_text, slots) if user_text else {}
        if parsed:
            slots.update(parsed)

        lowered = user_text.lower()
        if lowered in ("blueprint", "generate blueprint") or "generate the blueprint" in lowered:
            lib = _load_appendix_library()
            goal = slots.get("goal") or "Brand awareness"
            platform = slots.get("platform") or "tiktok"
            try:
                duration = int(slots.get("duration_sec") or 30)
            except Exception:
                duration = 30
            tone = slots.get("tone") or "playful"
            style = slots.get("style") or "ugc"
            key_msg = slots.get("key_message") or "Strong hook in first 2s"
            cta = slots.get("cta") or "DM us"
            rules = lib.get("veo_blueprint_rules", {})
            beats = lib.get("narrative_templates",[{}])[0].get("beats", [{"name":"Hook"},{"name":"Build"},{"name":"Payoff"}])
            total = max(duration, 15)
            hook_sec = max(int(total*0.2), 3)
            payoff_sec = max(int(total*0.2), 3)
            build_sec = max(total - hook_sec - payoff_sec, 6)
            blueprint = {
                "meta": {"platform": platform, "duration_sec": total, "tone": tone, "style": style, "text_free": bool(rules.get("text_free", True))},
                "overview": f"Goal: {goal}. Key message: {key_msg}. CTA: {cta}. Text-free policy enforced.",
                "beats": [
                    {"name": beats[0].get("name","Hook"), "secs": hook_sec, "direction": "Grab attention visually in 2s; no on-screen text."},
                    {"name": beats[1].get("name","Build"), "secs": build_sec, "direction": "Escalate the premise; include product claim or gag."},
                    {"name": beats[2].get("name","Payoff"), "secs": payoff_sec, "direction": f"Punchline + CTA ('{cta}')."},
                ],
                "negative_prompt": rules.get("negative_prompt", []),
            }
            _director_update_session(conn, session_id, {"selections": slots})
            assistant_message = "Blueprint generated from your current brief."
            _director_append_message(conn, session_id, "assistant", assistant_message)
            return json_response({
                "session_id": session_id,
                "assistant_message": assistant_message,
                "blueprint": blueprint
            })

        _director_update_session(conn, session_id, {"selections": slots})

        prompt = _next_prompt_v2(slots)

        confirmations = []
        for k in ["goal","platform","duration_sec","tone","style","audience","key_message","cta"]:
            if k in parsed:
                val = parsed[k]
                confirmations.append(f"{k.replace('_',' ').title()} = {val if not isinstance(val, dict) else json.dumps(val)}")
        confirm_line = f"Noted. {'; '.join(confirmations)}" if confirmations else ""

        assistant_message = prompt.get("assistant_message") or "Let's continue."
        if confirm_line:
            assistant_message = f"{confirm_line}\n\n{assistant_message}"

        _director_append_message(conn, session_id, "assistant", assistant_message)

        return json_response({
            "session_id": session_id,
            "assistant_message": assistant_message,
            "step_label": prompt.get("step_label"),
            "options": prompt.get("options", []),
            "directors_recommendation": prompt.get("directors_recommendation"),
            "selections": slots,
        })

    except Exception as e:
        log.exception("director_chat error")
        return json_response({"error":"Internal error","detail":str(e)}, 500)
    finally:
        put_conn(conn)

def director_commit_brief():
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    username = (payload.get("username") or payload.get("user_id") or "guest")  # ★

    body = request.get_json(silent=True) or {}
    raw_session_id = (body.get("session_id") or "").strip()
    slots = body.get("slots") or {}
    if not raw_session_id:
        return json_response({"error": "Missing session_id"}, 400)
    session_id = _canon_session_uuid(raw_session_id)  # ★

    conn = None
    try:
        conn = get_conn()
        sess = _director_get_session(conn, session_id)
        if not sess:
            _director_create_session(conn, session_id, username)
            sess = _director_get_session(conn, session_id)
        merged = sess["selections"].copy()
        merged.update(slots)

        if not _slots_ready(merged):
            return json_response({"error": "Brief not ready. Required: " + ", ".join(DIRECTOR_REQUIRED_SLOTS)}, 400)

        project_title = merged.get("project_title") or (merged.get("goal") or "Untitled Project")
        video_length_sec = int(merged.get("duration_sec") or 30)
        user_input = {
            "project_title": project_title,
            "video_length_sec": video_length_sec,
            "brief": merged,
        }
        conn.autocommit = False
        pid, creative_options = services.create_project_and_generate_creatives(
            db_conn=conn, user_id=username, user_input=user_input
        )
        _director_update_session(conn, session_id, selections_delta=merged, state="G9", step=10, project_id=pid)
        flags = _ready_flags(merged, pid)
        conn.commit()
        return json_response({"project_id": pid, "creative_options": creative_options, "next_state": "G9", "ready_flags": flags})
    except Exception as e:
        log.exception("director_commit_brief error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)


@app.route("/v1/director/storyboard", methods=["POST", "OPTIONS"])
@cross_origin()
def director_storyboard():
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)
    username = (payload.get("username") or payload.get("user_id") or "guest")  # ★

    data = request.get_json(silent=True) or {}
    raw_session_id = (data.get("session_id") or "").strip()
    project_id = (data.get("project_id") or "").strip()
    selected_option_index = data.get("selected_option_index")

    if not project_id or selected_option_index is None:
        return json_response({"error": "Missing project_id or selected_option_index"}, 400)

    session_id = _canon_session_uuid(raw_session_id) if raw_session_id else None  # ★

    conn = None
    try:
        conn = get_conn()
        resp = services.select_creative_and_generate_storyboard(
            db_conn=conn,
            user_id=username,
            project_id=project_id,
            selected_option_index=int(selected_option_index)
        )
        if session_id:
            try:
                _director_update_session(conn, session_id, state="G11", step=12)
            except Exception:
                pass
        flags = _ready_flags({}, project_id)
        return json_response({"storyboard": resp.get("storyboard"), "next_state": "G11", "ready_flags": flags})
    except Exception as e:
        log.exception("director_storyboard error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)


@app.route("/v1/director/veo-3-prompt", methods=["GET", "OPTIONS"])
@cross_origin()
def director_veo3_prompt_compat():
    # 兼容路由（旧前端若调用 /v1/director/veo-3-prompt）
    return director_veo3_prompt()

# POST compatibility: forward POST to the same underlying handler
@app.route("/v1/director/veo-3-prompt", methods=["POST", "OPTIONS"], endpoint="director_veo3_prompt_post")
@cross_origin()
def director_veo3_prompt_post():
    if request.method == "OPTIONS":
        return ("", 204)
    # Delegate to the canonical handler (expects query args; POST body is ignored for compatibility)
    return director_veo3_prompt()

@app.route("/v1/director/veo3-prompt", methods=["GET", "OPTIONS"])
@cross_origin()
def director_veo3_prompt():
    payload = _jwt_decode(request)
    if not payload:
        return json_response({"error": "Invalid token"}, 401)

    project_id = (request.args.get("project_id") or "").strip()
    if not project_id:
        return json_response({"error": "Missing project_id"}, 400)

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        # fetch storyboard scenes
        cur.execute("SELECT scenes FROM storyboards WHERE project_id=%s ORDER BY created_at DESC LIMIT 1", (project_id,))
        row = cur.fetchone()
        if not row:
            return json_response({"error": "Storyboard not found for project"}, 404)
        scenes = row[0] or {}

        # Build a minimal, stable JSON for VEO-3 (no on-screen text)
        prompt_json = {
            "scenes": scenes.get("scenes") if isinstance(scenes, dict) else scenes
        }
        return json_response({"veo3_prompt": json.dumps(prompt_json, ensure_ascii=False)})
    except Exception as e:
        log.exception("director_veo3_prompt error")
        return json_response({"error": "Internal error", "detail": str(e)}, 500)
    finally:
        put_conn(conn)



# ===== Conversation Memory (safer schema) =====
def _sql_table_has_columns(conn, table, cols):
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s
        """, (table,))
        names = {r[0] for r in cur.fetchall()}
        cur.close()
        return all(c in names for c in cols)
    except Exception:
        return False

def _ensure_director_tables(conn):
    cur = conn.cursor()
    # Create table if missing (new schema: speaker/content)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS director_messages (
            id BIGSERIAL PRIMARY KEY,
            session_id UUID NOT NULL,
            speaker TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    # Back-compat: if older columns "role"/"text" exist but new ones don't, add them.
    try:
        if not _sql_table_has_columns(conn, "director_messages", ["speaker","content"]):
            try:
                cur.execute("ALTER TABLE director_messages ADD COLUMN IF NOT EXISTS speaker TEXT")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE director_messages ADD COLUMN IF NOT EXISTS content TEXT")
            except Exception:
                pass
    except Exception:
        pass
    # Add archived flag to sessions if not exists
    try:
        cur.execute("ALTER TABLE director_sessions ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE")
    except Exception:
        pass
    conn.commit()
    cur.close()

def _director_append_message(conn, session_id, role, text):
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO director_messages (session_id, speaker, content) VALUES (%s,%s,%s)",
            (session_id, role, text or "")
        )
    except Exception:
        # Fallback to legacy columns if table is old, quoting reserved names
        cur.execute(
            'INSERT INTO director_messages (session_id, "role", "text") VALUES (%s,%s,%s)',
            (session_id, role, text or "")
        )
    conn.commit()
    cur.close()

def _director_get_recent_messages(conn, session_id, limit=20):
    cur = conn.cursor()
    try:
        cur.execute("SELECT speaker, content, created_at FROM director_messages WHERE session_id=%s ORDER BY id DESC LIMIT %s", (session_id, limit))
        rows = cur.fetchall()
    except Exception:
        cur.execute('SELECT "role", "text", created_at FROM director_messages WHERE session_id=%s ORDER BY id DESC LIMIT %s', (session_id, limit))
        rows = cur.fetchall()
    cur.close()
    return [{"role": r[0], "text": r[1], "created_at": r[2].isoformat()} for r in rows]

def _director_get_or_create_active_session(conn, user_id, session_id=None):
    """Reuse 24h active session if none provided; otherwise create/fetch by id."""
    if session_id:
        sess = _director_get_session(conn, session_id)
        if not sess:
            sess = _director_create_session(conn, session_id, user_id=user_id)
        return sess
    cur = conn.cursor()
    cur.execute("""
        SELECT id, selections, created_at, updated_at, archived
        FROM director_sessions
        WHERE user_id = %s AND archived = FALSE AND (NOW() - COALESCE(updated_at, created_at)) <= INTERVAL '24 hours'
        ORDER BY COALESCE(updated_at, created_at) DESC
        LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    if row:
        return {"id": row[0], "selections": row[1], "created_at": row[2], "updated_at": row[3], "archived": row[4]}
    return _director_create_session(conn, None, user_id=user_id)



# ----------------------------------------------------------------------------
# v1 Health (lightweight JSON for front-end probes)
# ----------------------------------------------------------------------------
@app.route("/v1/health", methods=["GET"])
def v1_health():
    try:
        # Prefer project helper if available
        return json_response({
            "ok": True,
            "service": "pf-system-api",
            "time": datetime.utcnow().isoformat() + "Z"
        }, 200)
    except Exception:
        # Fallback to Flask jsonify if helper is unavailable
        try:
            from flask import jsonify
            return jsonify({
                "ok": True,
                "service": "pf-system-api",
                "time": datetime.utcnow().isoformat() + "Z"
            }), 200
        except Exception:
            # Last fallback to plain response
            body = '{"ok": true, "service": "pf-system-api", "time": "' + datetime.utcnow().isoformat() + 'Z"}'
            return body, 200, {"Content-Type": "application/json"}

# --- Alias: /v1/login -> login() ---
@app.route('/v1/login', methods=['POST', 'OPTIONS'], endpoint='login_v1_alias')
def login_v1_alias():
    # CORS preflight fast-path
    if request.method == 'OPTIONS':
        return ('', 204)
    return login()

# --- Alias: /generate-script -> /v1/director/veo-3-prompt ---
@app.route('/generate-script', methods=['POST', 'OPTIONS'], endpoint='generate_script_alias')
def generate_script_alias():
    if request.method == 'OPTIONS':
        return ('', 204)
    # Preserve method & body
    return redirect('/v1/director/veo-3-prompt', code=307)

# ----------------------------------------------------------------------------
# Main app runner
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 8080))
    log.info(f"Starting PF System API on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
