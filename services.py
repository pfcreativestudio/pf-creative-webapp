# -*- coding: utf-8 -*-
"""
services.py
     (  Flask     ):
-      +       
-      +      +    QA
-     Onboarding(   )
-      (zip)
-   :  /     

    :
-     Gemini     "    " SDK;        API Key    ImportError
-         'models/gemini-1.5-pro'
-   AI   JSON     Pydantic   ,    ValidationError
-    DB        (conn.commit()),         
"""

from __future__ import annotations
import os
import io
import json
import uuid
import zipfile
import logging
from typing import Any, Dict, List, Tuple, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

# ---------------------------------------------------------------------------
# Pydantic models (to validate AI output)
# ---------------------------------------------------------------------------
class CreativeOption(BaseModel):
    title: str = Field(..., min_length=1)
    logline: str = Field(..., min_length=1)
    why_it_works: str = Field(..., min_length=1)

class CreativeOptionsPayload(BaseModel):
    options: List[CreativeOption]

    @field_validator("options")
    @classmethod
    def at_least_one(cls, v):
        if not v:
            raise ValueError("No creative options generated")
        return v

class StoryboardScene(BaseModel):
    number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    visuals: Optional[str] = ""
    voiceover: Optional[str] = ""
    duration_sec: Optional[int] = Field(5, ge=1)

class StoryboardPayload(BaseModel):
    scenes: List[StoryboardScene]

    @field_validator("scenes")
    @classmethod
    def at_least_one_scene(cls, v):
        if not v:
            raise ValueError("Storyboard has no scenes")
        return v


log = logging.getLogger("pf.services")

# ---------------------------------------------------------------------------
#    & AI   
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-1.5-pro")

def _require_genai():
    """
         Gemini SDK.         API Key,  ImportError.
    """
    if not GEMINI_API_KEY:
        raise ImportError("Gemini SDK/API key is not configured")
    try:
        import google.generativeai as genai  # type: ignore
    except Exception as e:
        raise ImportError(f"google.generativeai not available: {e}")
    genai.configure(api_key=GEMINI_API_KEY)
    return genai


def _call_gemini_for_json(prompt: str, system_instruction: Optional[str] = None) -> Any:
    """
    Call Gemini and expect JSON. Prefer response.text, otherwise inspect candidates/parts and to_dict().
    Force JSON by setting response_mime_type. If nothing parsable is found, raise ValueError so caller can fallback.
    """
    genai = _require_genai()
    model = genai.GenerativeModel(
        DEFAULT_MODEL,
        system_instruction=system_instruction,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 2048,
            "response_mime_type": "application/json",
        },
    )
    resp = model.generate_content(prompt)

    texts = []

    # 1) direct text
    if getattr(resp, "text", None):
        texts.append(resp.text)

    # 2) candidates -> parts -> text
    try:
        for cand in getattr(resp, "candidates", []) or []:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) if content else None
            if parts:
                for p in parts:
                    t = getattr(p, "text", None)
                    if t:
                        texts.append(t)
    except Exception:
        pass

    # 3) deep walk of to_dict()
    try:
        d = resp.to_dict()
        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "text" and isinstance(v, str):
                        yield v
                    else:
                        yield from walk(v)
            elif isinstance(o, list):
                for it in o:
                    yield from walk(it)
        texts.extend(list(walk(d)))
    except Exception:
        pass

    # Extract first valid JSON object/array
    import re as _re, json as _json
    for t in texts:
        if not t:
            continue
        txt = t.strip()
        if txt.startswith("```"):
            # strip code fences
            txt = _re.sub(r"^```[a-zA-Z0-9_-]*", "", txt).strip()
            txt = txt.rstrip("`").strip()
        m = _re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", txt)
        if m:
            candidate = m.group(1).strip()
            try:
                return _json.loads(candidate)
            except Exception:
                continue

    # If nothing parsable, raise
    raise ValueError("Gemini returned no valid JSON payload")


def _fetchone_dict(cur) -> Optional[Dict[str, Any]]:
    row = cur.fetchone()
    if not row:
        return None
    colnames = [c[0] for c in cur.description]
    return dict(zip(colnames, row))

def _fetchall_dicts(cur) -> List[Dict[str, Any]]:
    rows = cur.fetchall()
    colnames = [c[0] for c in cur.description]
    return [dict(zip(colnames, r)) for r in rows]

# ---------------------------------------------------------------------------
#     
# ---------------------------------------------------------------------------

def create_project_and_generate_creatives(
    db_conn, user_id: str, user_input: Dict[str, Any]
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Create a project and generate 3 creative options.
    Returns: (project_id, creative_options)
    """
    cur = db_conn.cursor()
    try:
        project_title = user_input.get("project_title") or "Untitled Project"
        video_length_sec = int(user_input.get("video_length_sec") or 30)

        # 1)     
        cur.execute(
            """
            INSERT INTO projects (user_id, project_title, user_input, video_length_sec)
            VALUES (%s, %s, %s::jsonb, %s)
            RETURNING id
            """,
            (user_id, project_title, json.dumps(user_input), video_length_sec),
        )
        pid = str(cur.fetchone()[0])

        # 2)   AI       (   ImportError      )
        prompt = f"""
You are an advertising creative director. Based on the following project information, generate 3 distinctly different creative concepts for a 30-second commercial video.
For each option, output: title, logline, why_it_works. Return strictly JSON: {{"options":[...]}}
Project title: {project_title}
Duration (sec): {video_length_sec}
User input (JSON): {json.dumps(user_input, ensure_ascii=False)}
""".replace('{"options":[...]}', '{{"options":[...]}}').strip()

        try:
            data = _call_gemini_for_json(prompt)
            parsed = CreativeOptionsPayload.model_validate(data)
            opts = list(parsed.options or [])
        except Exception as e:
            log.warning("Gemini JSON parse/validation failed (creative options), falling back: %s", e)
            base = (project_title or "Your Project").strip()
            opts = [
                CreativeOption(title=f"Concept A: {base}", logline="A concise logline based on the project objective.", why_it_works="Clear message with a strong hook."),
                CreativeOption(title=f"Concept B: {base}", logline="An alternative angle with contrasting tone/mood.", why_it_works="Provides variety for comparison."),
                CreativeOption(title=f"Concept C: {base}", logline="CTA-oriented angle highlighting the key benefit.", why_it_works="Direct and conversion-focused."),
            ]

        # 2b) Normalize to exactly 3 options (English-only comments).
        if len(opts) > 3:
            opts = opts[:3]
        while len(opts) < 3:
            idx_pad = len(opts) + 1
            opts.append(CreativeOption(
                title=f"Option {idx_pad}",
                logline="(to be refined)",
                why_it_works="Provides variety among concepts."
            ))
        # 3)    creative_options
        options_out = []
        for idx, opt in enumerate(opts):  # 0-based to satisfy DB CHECK (0,1,2)
            cur.execute(
                """
                INSERT INTO creative_options (project_id, option_index, title, logline, why_it_works, is_selected)
                VALUES (%s, %s, %s, %s, %s, FALSE)
                ON CONFLICT (project_id, option_index)
                DO UPDATE SET title=EXCLUDED.title, logline=EXCLUDED.logline, why_it_works=EXCLUDED.why_it_works
                RETURNING id
                """,
                (pid, idx, opt.title, opt.logline, opt.why_it_works),
            )
            opt_id = str(cur.fetchone()[0])
            options_out.append({
                "id": opt_id,
                "option_index": idx,
                "title": opt.title,
                "logline": opt.logline,
                "why_it_works": opt.why_it_works,
                "is_selected": False
            })

        db_conn.commit()
        return pid, options_out

    except Exception:
        db_conn.rollback()
        raise
    finally:
        cur.close()

def select_creative_and_generate_storyboard(
    db_conn, project_id: str, selected_creative_id: str
) -> Tuple[Dict[str, Any], str]:
    """
    Mark a creative as selected, and generate a storyboard based on it(Storyboard) +    QA.
      : (storyboard_json, qa_critique_text)
    """
    cur = db_conn.cursor()
    try:
        # 1)          ;      
        cur.execute("SELECT id, title, logline, why_it_works FROM creative_options WHERE id=%s AND project_id=%s",
                    (selected_creative_id, project_id))
        co = cur.fetchone()
        if not co:
            raise ValueError("Selected creative option not found for this project")

        cur.execute("UPDATE creative_options SET is_selected = (id = %s) WHERE project_id=%s",
                    (selected_creative_id, project_id))

        # 2)   Prompt     
        co_title, co_logline, co_reason = co[1], co[2], co[3]
        prompt = f"""
You are a senior storyboard director. Using the selected creative, generate a storyboard for approximately 30 seconds consisting of 8-12 shots.
For each scene, output: number (sequence), title, description (shot content), visuals (key visuals), voiceover (narration/subtitle suggestions), duration_sec.
Return strictly JSON: {{"scenes":[...]}}.
Creative title: {co_title}
Logline: {co_logline}
Why it works: {co_reason}
Project ID: {project_id}
""".replace('{"scenes":[...]}', '{{"scenes":[...]}}').strip()

        data = _call_gemini_for_json(prompt)
        try:
            storyboard = StoryboardPayload.model_validate(data).model_dump()
        except ValidationError as e:
            log.warning("Validation Error from Gemini (storyboard): %s", e)
            storyboard = {"scenes": []}
            for i in range(1, 11):
                storyboard["scenes"].append({
                    "number": i,
                    "title": f"Shot {i}",
                    "description": "Placeholder scene generated as a fallback.",
                    "visuals": "Key subject appears, simple motion.",
                    "voiceover": "N/A",
                    "duration_sec": 3
                })

        # 3)  light QA (example: total duration / scene count)
        scenes = storyboard["scenes"]
        total_dur = sum(int(s.get("duration_sec") or 0) for s in scenes)
        qa_pass = 15 <= total_dur <= 45 and 6 <= len(scenes) <= 16
        qa_critique = f"Total duration ~{total_dur}s; Scenes={len(scenes)}; " \
                      f"{'OK' if qa_pass else 'Consider adjusting duration/scene count'}"

        # 4)    storyboards
        cur.execute(
            """
            INSERT INTO storyboards (project_id, creative_option_id, scenes, qa_status, qa_feedback)
            VALUES (%s, %s, %s::jsonb, %s, %s)
            RETURNING id
            """,
            (project_id, selected_creative_id, json.dumps(storyboard), 'passed' if qa_pass else 'failed', qa_critique),
        )
        sb_id = str(cur.fetchone()[0])

        db_conn.commit()
        return storyboard, qa_critique

    except ValidationError:
        db_conn.rollback()
        #       (main.py    502)
        raise
    except Exception:
        db_conn.rollback()
        raise
    finally:
        cur.close()

# ---------------------------------------------------------------------------
# Onboarding conversation flow (minimal viable)
# ---------------------------------------------------------------------------

def create_session(
    db_conn,
    user_id: str,
    user_input: Dict[str, Any],
) -> Dict[str, Any]:
    """
        (step=1),        +     (  ).
    Strategy: after creating the session, persist a project and creatives, then return to the client.
    """
    cur = db_conn.cursor()
    try:
        #         session
        cur.execute(
            """
            INSERT INTO sessions (user_id, state, selections, step, project_id)
            VALUES (%s, %s, '{}'::jsonb, 1, NULL)
            RETURNING id
            """,
            (user_id, "init"),
        )
        sid = str(cur.fetchone()[0])

        #         
        project_id, creative_options = create_project_and_generate_creatives(db_conn, user_id, user_input)

        #     session
        cur.execute("UPDATE sessions SET state=%s, step=%s, project_id=%s WHERE id=%s",
                    ("creative_options", 2, project_id, sid))

        db_conn.commit()
        return {
            "session_id": sid,
            "project_id": project_id,
            "step": 2,
            "state": "creative_options",
            "creative_options": creative_options
        }

    except Exception:
        db_conn.rollback()
        raise
    finally:
        cur.close()

def advance_session(
    db_conn,
    session_id: str,
    user_choice: Dict[str, Any]
) -> Dict[str, Any]:
    """
Advance session state machine:
    - step=2:      ->     
    - step=3: (      /    )
    """
    cur = db_conn.cursor()
    try:
        cur.execute("SELECT id, user_id, state, step, project_id FROM sessions WHERE id=%s", (session_id,))
        s = cur.fetchone()
        if not s:
            raise ValueError("Session not found")
        sid, user_id, state, step, project_id = s[0], s[1], s[2], int(s[3]), s[4]
        if not project_id:
            raise ValueError("Session has no project yet")

        if step == 2:
            creative_id = user_choice.get("creative_id")
            if not creative_id:
                raise ValueError("creative_id is required at step=2")
            storyboard, qa_critique = select_creative_and_generate_storyboard(db_conn, str(project_id), creative_id)
            cur.execute("UPDATE sessions SET state=%s, step=%s, selections = selections || %s::jsonb WHERE id=%s",
                        ("storyboard_ready", 3, json.dumps({"creative_id": creative_id}), sid))
            db_conn.commit()
            return {
                "next_step": 3,
                "state": "storyboard_ready",
                "storyboard": storyboard,
                "qa_critique": qa_critique
            }

        #     :  (    )
        return {"next_step": step, "state": state}

    except Exception:
        db_conn.rollback()
        raise
    finally:
        cur.close()

# ---------------------------------------------------------------------------
# Release Gate / Finalize(  )
# ---------------------------------------------------------------------------

def release_gate_finalize(db_conn, project_id: str) -> Dict[str, Any]:
    """
      storyboard     blueprints(   scene      blueprint),
      "    "   (         /     ).
    """
    cur = db_conn.cursor()
    try:
        cur.execute("SELECT id, scenes FROM storyboards WHERE project_id=%s ORDER BY created_at DESC LIMIT 1", (project_id,))
        r = cur.fetchone()
        if not r:
            raise ValueError("No storyboard to finalize for this project")
        storyboard = r[1]  # JSONB

        #    JSONB      str    
        if isinstance(storyboard, str):
            try:
                storyboard = json.loads(storyboard)
            except Exception:
                storyboard = {}

        scenes = storyboard.get("scenes") if isinstance(storyboard, dict) else None
        if not scenes:
            raise ValueError("Storyboard invalid (no scenes)")

        #      (  )
        cur.execute("DELETE FROM blueprints WHERE project_id=%s", (project_id,))

        #       blueprints
        for s in scenes:
            scene_no = int(s.get("number") or 0) or 1
            cur.execute(
                """
                INSERT INTO blueprints (project_id, storyboard_id, scene_number, content_json)
                VALUES (%s, (SELECT id FROM storyboards WHERE project_id=%s ORDER BY created_at DESC LIMIT 1), %s, %s::jsonb)
                """,
                (project_id, project_id, scene_no, json.dumps(s)),
            )

        db_conn.commit()
        return {"ok": True, "scenes": len(scenes)}

    except Exception:
        db_conn.rollback()
        raise
    finally:
        cur.close()

# ---------------------------------------------------------------------------
#    
# ---------------------------------------------------------------------------

def build_export_zip(db_conn, project_id: str) -> bytes:
    """
         +      ,    zip:
    - project.json
    - storyboard.json  (  :{"scenes":[...]})
    - readme.txt
    """
    cur = db_conn.cursor()
    try:
        # project
        cur.execute("SELECT id, user_id, project_title, user_input, video_length_sec, created_at FROM projects WHERE id=%s", (project_id,))
        proj = _fetchone_dict(cur)
        if not proj:
            raise ValueError("Project not found")

        # storyboard(    )
        cur.execute("SELECT id, scenes, qa_status, qa_feedback, created_at FROM storyboards WHERE project_id=%s ORDER BY created_at DESC LIMIT 1", (project_id,))
        sb = _fetchone_dict(cur)
        if not sb:
            raise ValueError("Storyboard not found for export")

        scenes = None
        sb_scenes = sb.get("scenes")
        #    JSONB   str/dict/list     
        if isinstance(sb_scenes, str):
            try:
                sb_scenes = json.loads(sb_scenes)
            except Exception:
                sb_scenes = {}
        if isinstance(sb_scenes, dict):
            scenes = sb_scenes.get("scenes")
        elif isinstance(sb_scenes, list):
            scenes = sb_scenes
        if scenes is None:
            scenes = []

        #       {"scenes":[...]}
        storyboard_out = {"scenes": scenes}

        #   
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("project.json", json.dumps(proj, ensure_ascii=False, indent=2))
            zf.writestr("storyboard.json", json.dumps(storyboard_out, ensure_ascii=False, indent=2))
            readme = (
                "PF Creative Studio Export\n"
                f"Project: {proj.get('project_title')}\n"
                f"Project ID: {project_id}\n"
                f"Storyboard Scenes: {len(scenes)}\n"
                f"QA: {sb.get('qa_status')} - {sb.get('qa_feedback')}\n"
            )
            zf.writestr("readme.txt", readme)

        return bio.getvalue()

    finally:
        cur.close()

# PF Director 2.0 — Orchestrator & Builders (APPEND-ONLY ADD-ON)
# This is an append-only add-on. It does not modify existing functions.
# All code/comments are in English. Safe to include in production.

import json, re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------- Director Steps ----------------------------
STEP_ORDER: List[str] = ["G0","G1","G2","G3","G4","G5","G6","G7","G8","G9","G10","G11","G12","G13"]
REQUIRED_SLOTS: List[str] = ["goal","audience","platform","duration_sec","key_message","cta"]

PLATFORM_ALIASES: Dict[str, List[str]] = {
    "tiktok": ["tiktok", "douyin", "抖音"],
    "instagram reels": ["instagram reels", "ig reels", "insta reels", "reels"],
    "youtube shorts": ["youtube shorts", "shorts", "yt shorts"],
    "facebook reels": ["facebook reels", "fb reels"],
    "wechat channels": ["wechat channels", "weixin video", "video accounts"],
}

RECOMMENDATIONS: Dict[str, str] = {
    "G1": "State one outcome, e.g., 'Drive store visits' or 'Launch a new product'.",
    "G2": "Think demographic + intent, e.g., 'Gen-Z in KL who love snacks'.",
    "G3": "Choose a platform and duration (e.g., TikTok 30s).",
    "G4": "Give a clear value proposition and a single CTA.",
    "G5": "Pick 1–2 tone words and 1 style word (e.g., playful + cinematic).",
    "G6": "Share any references, sample lines, or assets URLs.",
    "G7": "Budget limits? Legal/brand rules? Banned topics?",
    "G8": "Review the brief. Reply 'looks good' to proceed.",
    "G9": "Pick one creative option to continue.",
    "G10": "Confirm your selection to build a storyboard.",
    "G11": "Review the storyboard and ask for refinements if needed.",
    "G12": "Copy the generated VEO-3 prompt JSON.",
    "G13": "Export your package when ready.",
}

# ---------------------------- Slot Parsing ------------------------------
_DURATION_RE = re.compile(r"(\\b(\\d+)\\s*(s|sec|secs|second|seconds)\\b)|(\\b(\\d+)\\s*(m|min|mins|minute|minutes)\\b)")
_TONE_WORDS = {
    "playful","fun","warm","heartwarming","epic","dramatic","casual","professional",
    "authentic","inspiring","quirky","edgy","aspirational","minimal"
}
_STYLE_WORDS = {
    "cinematic","ugc","asmr","vlog","tutorial","comedy","interview","montage",
    "stop-motion","retro","surreal","documentary"
}
_URL_RE = re.compile(r"https?://[^\\s]+", re.I)

def _detect_platform(text: str) -> Optional[str]:
    t = (text or "").lower()
    for k, aliases in PLATFORM_ALIASES.items():
        for a in aliases:
            if a in t:
                return k
    return None

def _detect_duration_sec(text: str) -> Optional[int]:
    t = (text or "").lower()
    m = _DURATION_RE.search(t)
    if not m:
        m2 = re.search(r"\\b(\\d+)(s|m)\\b", t)
        if m2:
            val = int(m2.group(1)); unit = m2.group(2)
            return val if unit == "s" else val * 60
        return None
    if m.group(2) and m.group(3):
        return int(m.group(2))  # seconds
    if m.group(5) and m.group(6):
        return int(m.group(5)) * 60  # minutes
    return None

def _detect_tone_style(text: str) -> Tuple[Optional[str], Optional[str]]:
    t = (text or "").lower()
    tone = next((w for w in _TONE_WORDS if w in t), None)
    style = next((w for w in _STYLE_WORDS if w in t), None)
    return tone, style

def _detect_references(text: str) -> List[str]:
    return _URL_RE.findall(text or "")

def normalize_slots(partial: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if partial.get("platform"):
        out["platform"] = str(partial["platform"]).lower()
    if partial.get("duration_sec"):
        try:
            out["duration_sec"] = int(partial["duration_sec"])
        except Exception:
            pass
    for k in ["goal","audience","key_message","cta","tone","style","constraints"]:
        if partial.get(k):
            out[k] = str(partial[k]).strip()
    if partial.get("assets"):
        # de-duplicate
        seen = []
        for u in partial["assets"]:
            if u not in seen: seen.append(u)
        out["assets"] = seen
    return out

def _slot_present_for_step(step: str, slots: Dict[str, Any]) -> bool:
    mapping = {
        "G1": "goal",
        "G2": "audience",
        "G3": ("platform","duration_sec"),
        "G4": ("key_message","cta"),
        "G5": ("tone","style"),
        "G6": "assets",
        "G7": "constraints",
    }
    key = mapping.get(step)
    if key is None:
        return True
    if isinstance(key, tuple):
        return all(slots.get(k) for k in key)
    return bool(slots.get(key))

def _has_required(slots: Dict[str, Any]) -> bool:
    return all(bool(slots.get(k)) for k in REQUIRED_SLOTS)

def _brief_preview(slots: Dict[str, Any]) -> str:
    platform = slots.get("platform","—")
    duration = f"{slots.get('duration_sec','—')}s"
    tone = slots.get("tone","—"); style = slots.get("style","—")
    msg = (
        "Here is your brief:\\n\\n"
        f"Objective: {slots.get('goal','—')}\\n"
        f"Audience: {slots.get('audience','—')}\\n"
        f"Platform & Duration: {platform} | {duration}\\n"
        f"Tone & Style: {tone} | {style}\\n"
        f"Key Message: {slots.get('key_message','—')}\\n"
        f"CTA: {slots.get('cta','—')}\\n"
        f"Constraints: {slots.get('constraints','—')}\\n"
        f"Assets: {', '.join(slots.get('assets',[])) or '—'}"
    )
    return msg

def _determine_prompt(step: str, slots: Dict[str, Any]) -> Tuple[str,str,List[str]]:
    if step == "G1":
        return ("What is the main goal of this video?", RECOMMENDATIONS["G1"], ["Brand awareness","Drive conversions","App installs","Promote event"])
    if step == "G2":
        return ("Who is the target audience?", RECOMMENDATIONS["G2"], ["Gen-Z in KL","Young parents","Office workers","Budget shoppers"])
    if step == "G3":
        pf = slots.get("platform") or "—"
        du = f"{slots.get('duration_sec')}s" if slots.get("duration_sec") else "—"
        return (f"Which platform and duration? (current: {pf}, {du})", RECOMMENDATIONS["G3"], ["TikTok 15s","TikTok 30s","Instagram Reels 30s","YouTube Shorts 60s"])
    if step == "G4":
        return ("Give me your key message and a single CTA.", RECOMMENDATIONS["G4"], ["Key message: premium ingredients","CTA: Visit our store","CTA: Shop now"])
    if step == "G5":
        return ("Pick tone and style.", RECOMMENDATIONS["G5"], ["playful cinematic","authentic UGC","epic montage"])
    if step == "G6":
        return ("Any assets or reference links?", RECOMMENDATIONS["G6"], [])
    if step == "G7":
        return ("Any constraints (budget, legal, safety, brand rules)?", RECOMMENDATIONS["G7"], ["No on-screen text","No competitor logos","Budget under RM500"])
    if step == "G8":
        return (_brief_preview(slots), RECOMMENDATIONS["G8"], ["Looks good","Change tone","Make it 15s"])
    if step == "G9":
        return ("Generating three creative options…", RECOMMENDATIONS["G9"], [])
    if step == "G10":
        return ("Which option do you want to proceed with? (0/1/2)", RECOMMENDATIONS["G10"], ["Pick 0","Pick 1","Pick 2"])
    if step == "G11":
        return ("Storyboard is ready. Want to refine anything?", RECOMMENDATIONS["G11"], ["Tighten pacing","More product shots"])
    if step == "G12":
        return ("Your VEO-3 prompt is ready.", RECOMMENDATIONS["G12"], ["Copy prompt"])
    if step == "G13":
        return ("You can export your package now.", RECOMMENDATIONS["G13"], ["Export"])
    return ("Let's start with your goal.", RECOMMENDATIONS["G1"], [])

def _resp(msg: str, rec: str, slots: Dict[str, Any], next_state: str, flags: Dict[str, bool], quick: Optional[List[str]]=None) -> Dict[str, Any]:
    return {
        "assistant_message": msg,
        "director_recommendation": rec,
        "quick_replies": quick or [],
        "state_update": slots,
        "next_state": next_state,
        "ready_flags": flags,
    }

def slots_ready_flags(slots: Dict[str, Any], has_creatives: bool=False, has_storyboard: bool=False) -> Dict[str, bool]:
    return {
        "can_generate_creatives": _has_required(slots),
        "can_storyboard": has_creatives,
        "can_build_veo3_prompt": has_storyboard,
        "can_export": has_storyboard,
    }

# ---------------------------- Orchestrator -------------------------------
def director_orchestrator_chat(session_state: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    """
    Stateless orchestrator used by main.py director/chat route.
    Consumes `session_state` (keys: next_state, slots, project_id) and `user_text`,
    returns next message, recommendation, updated slots, and flags.
    """
    next_state = (session_state.get("next_state") or "G1")
    slots: Dict[str, Any] = dict(session_state.get("slots") or {})
    text = (user_text or "").strip()
    low = text.lower()

    # Extract from free text
    extracted: Dict[str, Any] = {}
    p = _detect_platform(text)
    if p: extracted["platform"] = p
    d = _detect_duration_sec(text)
    if d: extracted["duration_sec"] = d
    tone, style = _detect_tone_style(text)
    if tone and not slots.get("tone"): extracted["tone"] = tone
    if style and not slots.get("style"): extracted["style"] = style
    refs = _detect_references(text)
    if refs:
        existing = set(slots.get("assets") or [])
        extracted["assets"] = list(existing.union(refs))

    # Lightweight intent routing for key fields
    if "goal" in low or "objective" in low:
        parts = re.split(r"goal\\s*:\\s*", text, flags=re.I)
        if len(parts) > 1:
            extracted["goal"] = parts[1].strip()
    if "audience" in low or "target" in low:
        parts = re.split(r"(audience|target)\\s*:\\s*", text, flags=re.I)
        if len(parts) > 2:
            extracted["audience"] = parts[-1].strip()
    if "key message" in low or "value proposition" in low:
        parts = re.split(r"key\\s*message\\s*:\\s*", text, flags=re.I)
        if len(parts) > 1:
            extracted["key_message"] = parts[1].strip()
    if "cta" in low or "call to action" in low:
        parts = re.split(r"cta\\s*:\\s*", text, flags=re.I)
        if len(parts) > 1:
            extracted["cta"] = parts[1].strip()

    updates = normalize_slots(extracted)
    slots.update(updates)

    # current index
    cur_idx = STEP_ORDER.index(next_state) if next_state in STEP_ORDER else 1

    # Approval phrase at G8
    if next_state == "G8" and re.search(r"\\b(looks good|ok|okay|proceed|go ahead|confirm)\\b", low):
        next_state = "G9"
        msg = "Great. Generating three creative options for your brief."
        rec = "You can pick one to move forward to storyboard."
        return _resp(msg, rec, slots, next_state, slots_ready_flags(slots, has_creatives=True))

    # Determine next question
    ask, rec, quick = _determine_prompt(next_state, slots)

    # Auto-advance if slot already present
    while _slot_present_for_step(next_state, slots) and next_state in STEP_ORDER and next_state not in {"G8","G9","G10","G11","G12","G13"}:
        cur_idx = min(cur_idx + 1, len(STEP_ORDER)-1)
        next_state = STEP_ORDER[cur_idx]
        ask, rec, quick = _determine_prompt(next_state, slots)

    # If all required slots are present and we haven't reached G8, jump to brief review
    if _has_required(slots) and next_state not in {"G8","G9","G10","G11","G12","G13"}:
        next_state = "G8"
        ask = _brief_preview(slots)
        rec = "Reply 'looks good' to proceed, or tell me what to change."
        quick = ["Looks good","Change tone","Change platform","Make it 15s"]

    return _resp(ask, rec, slots, next_state, slots_ready_flags(slots))

# -------------------------- DB-Aware Helpers ----------------------------
def commit_brief_and_create_project_v2(db_conn, user_id: str, session_id: str, slots: Dict[str, Any]):
    """
    Create a project (using your existing helper) AFTER the brief is confirmed.
    Uses: create_project_and_generate_creatives(db_conn, user_id, user_input)
    Returns: (project_id, creative_options)
    Also attempts to persist selections into sessions.selections JSONB.
    """
    user_input = {
        "project_title": slots.get("goal") or "Untitled Project",
        "video_length_sec": int(slots.get("duration_sec") or 30),
        "platform": slots.get("platform"),
        "brief_text": _brief_preview(slots),
        "slots": slots,
        "session_id": session_id,
    }
    project_id, creative_options = create_project_and_generate_creatives(db_conn, user_id, user_input)  # type: ignore[name-defined]

    try:
        cur = db_conn.cursor()
        cur.execute(
            "UPDATE sessions SET state=%s, step=%s, project_id=%s, selections = selections || %s::jsonb WHERE id=%s",
            ("creative_options", 2, project_id, json.dumps(slots), session_id)
        )
        db_conn.commit()
        cur.close()
    except Exception:
        db_conn.rollback()

    return project_id, creative_options

def select_creative_and_make_storyboard_v2(db_conn, session_id: Optional[str], project_id: str, selected_creative_id: str):
    """
    Wrapper that uses your existing select_creative_and_generate_storyboard, then
    optionally updates sessions with the selected creative.
    Returns: (storyboard, qa_critique)
    """
    storyboard, qa_critique = select_creative_and_generate_storyboard(db_conn, project_id, selected_creative_id)  # type: ignore[name-defined]

    if session_id:
        try:
            cur = db_conn.cursor()
            cur.execute(
                "UPDATE sessions SET state=%s, step=%s, selections = selections || %s::jsonb WHERE id=%s",
                ("storyboard_ready", 3, json.dumps({"creative_id": selected_creative_id}), session_id)
            )
            db_conn.commit()
            cur.close()
        except Exception:
            db_conn.rollback()

    return storyboard, qa_critique

# -------------------------- VEO-3 Prompt Builder ------------------------
_ONSCREEN_RE = re.compile(r"(text on screen|subtitle|caption|logo|watermark)", re.I)

def _strip_on_screen_text(s: str) -> str:
    if not s: return s
    return _ONSCREEN_RE.sub("", s)

def _extract_scenes_from_db_storyboard(sb: Any) -> List[Dict[str, Any]]:
    scenes_raw: List[Any] = []
    if isinstance(sb, str):
        try:
            sb = json.loads(sb)
        except Exception:
            sb = {}
    if isinstance(sb, dict) and isinstance(sb.get("scenes"), list):
        scenes_raw = sb["scenes"]
    elif isinstance(sb, list):
        scenes_raw = sb

    out: List[Dict[str, Any]] = []
    for i, s in enumerate(scenes_raw, start=1):
        title = s.get("title") or s.get("name") or f"Scene {i}"
        visuals = s.get("visuals") or s.get("visual") or s.get("image") or ""
        voiceover = s.get("voiceover") or s.get("vo") or s.get("narration") or ""
        dur = s.get("duration_sec") or s.get("duration") or s.get("len") or 3
        try:
            dur = int(dur)
        except Exception:
            dur = 3
        visuals = _strip_on_screen_text(str(visuals))
        out.append({
            "number": i,
            "title": str(title)[:80],
            "visuals": visuals,
            "voiceover": str(voiceover),
            "duration_sec": dur
        })
    return out

def build_veo3_prompt_v2(db_conn, project_id: str) -> str:
    """
    Build a stable VEO-3 prompt JSON string from the latest storyboard in DB.
    Output JSON: {"scenes":[{"number":1,"title":"...","visuals":"...","voiceover":"...","duration_sec":3}, ...]}
    """
    cur = db_conn.cursor()
    try:
        cur.execute("SELECT scenes FROM storyboards WHERE project_id=%s ORDER BY created_at DESC LIMIT 1", (project_id,))
        r = cur.fetchone()
        if not r:
            raise ValueError("Storyboard not found")
        scenes_obj = r[0]
    finally:
        cur.close()

    scenes = _extract_scenes_from_db_storyboard(scenes_obj)
    veo_obj = {"scenes": scenes}
    return json.dumps(veo_obj, ensure_ascii=False)
