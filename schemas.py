# ======================================================================
# PF Director 2.0 — Schemas Add‑On (append-only)
# This block is designed to be appended to the END of your existing schemas.py.
# It does NOT remove or alter current models.
# All code/comments are in English.
# ======================================================================

from typing import List, Optional, Dict, Any
try:
    # pydantic v1/v2 compatible import style
    from pydantic import BaseModel, Field
except Exception:
    # If pydantic is unavailable or named differently in your project,
    # adjust the import accordingly.
    from pydantic import BaseModel, Field  # type: ignore

# ---------------------------- Core Slot Models --------------------------

class Slots(BaseModel):
    """Brief slots collected by the Director Orchestrator."""
    goal: Optional[str] = None
    audience: Optional[str] = None
    platform: Optional[str] = None
    duration_sec: Optional[int] = Field(default=None, gt=0, le=600, description="Target duration in seconds")
    tone: Optional[str] = None
    style: Optional[str] = None
    key_message: Optional[str] = None
    cta: Optional[str] = None
    constraints: Optional[str] = None
    assets: List[str] = Field(default_factory=list, description="Reference URLs or asset identifiers")

class ReadyFlags(BaseModel):
    """Front‑end switches to unlock actions in the UI."""
    can_generate_creatives: bool = False
    can_storyboard: bool = False
    can_build_veo3_prompt: bool = False
    can_export: bool = False

# ---------------------------- Director Chat I/O -------------------------

class DirectorChatRequest(BaseModel):
    """Request body for POST /v1/director/chat"""
    session_id: str
    user_text: str

class DirectorChatResponse(BaseModel):
    """Response body for POST /v1/director/chat"""
    assistant_message: str
    director_recommendation: Optional[str] = None
    quick_replies: List[str] = Field(default_factory=list)
    state_update: Slots = Field(default_factory=Slots)
    next_state: str = Field(default="G1", description="G1..G13 step code")
    ready_flags: ReadyFlags = Field(default_factory=ReadyFlags)

# ---------------------------- Commit Brief ------------------------------

class DirectorCommitBriefRequest(BaseModel):
    """Request body for POST /v1/director/commit-brief"""
    session_id: str
    slots: Optional[Slots] = None  # if omitted, server uses accumulated session slots

class CreativeOption(BaseModel):
    """One creative concept generated for the brief."""
    id: Optional[str] = None
    title: str
    logline: str
    why_it_works: Optional[str] = None
    scores: Optional[Dict[str, Any]] = None  # e.g., {"clarity":4.5,"emotion":4.0,...}

class DirectorCommitBriefResponse(BaseModel):
    project_id: str
    creative_options: List[CreativeOption]
    next_state: str = "G9"
    ready_flags: ReadyFlags = Field(default_factory=ReadyFlags)

# ---------------------------- Storyboard Step ---------------------------

class DirectorStoryboardRequest(BaseModel):
    """Request body for POST /v1/director/storyboard\n
    Support either selected_option_index (0/1/2) or selected_creative_id (string)."""
    session_id: Optional[str] = None
    project_id: str
    selected_option_index: Optional[int] = None
    selected_creative_id: Optional[str] = None

class StoryboardScene(BaseModel):
    number: int
    title: str
    visuals: str
    voiceover: str
    duration_sec: int = Field(gt=0, le=120)

class Storyboard(BaseModel):
    scenes: List[StoryboardScene]
    meta: Optional[Dict[str, Any]] = None

class DirectorStoryboardResponse(BaseModel):
    storyboard: Storyboard
    next_state: str = "G11"
    ready_flags: ReadyFlags = Field(default_factory=ReadyFlags)

# ---------------------------- VEO‑3 Prompt ------------------------------

class DirectorVeoPromptResponse(BaseModel):
    """Response body for GET /v1/director/veo3-prompt"""
    veo3_prompt: str  # JSON string like: {"scenes":[ ... ]}

# ---------------------------- Session State -----------------------------

class SessionState(BaseModel):
    """Cached state stored/returned by server for Orchestrator logic."""
    session_id: str
    next_state: str = "G1"
    slots: Slots = Field(default_factory=Slots)
    project_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None  # optional transcript storage
    # Optional progress hints for UI
    step: Optional[int] = None
    selections: Optional[Dict[str, Any]] = None