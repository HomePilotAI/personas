from __future__ import annotations

import os
import re
import sys
import time
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python_common')))
from app_base import ResultResponse, attach_context_forge_routes, create_base_app

TOOLS = [
    {"name": "describe_session_vibe", "description": "Creates a concise vibe prompt for a live persona play session (teasing, playful, romantic, cinematic, etc.)."},
    {"name": "build_branching_video_project", "description": "Builds a production-ready branching AI video project with scenes, choices, and multiple endings centered around a selected persona."},
    {"name": "suggest_live_play_examples", "description": "Returns high-quality example project ideas for persona live play sessions."},
]
ALLOWED_VIBES = ["teasing", "playful", "romantic", "mysterious", "cinematic", "comedic", "dramatic", "cozy", "high-energy"]
EXAMPLE_IDEAS = [
    "teach beginners basic Spanish conversation practice",
    "walk new sales reps through our 3 pricing tiers with quizzes",
    "explain photosynthesis with a short branching story",
    "compliance onboarding for a new hire — 4 decisions, 3 endings",
]
app = create_base_app("mcp-storyteller", TOOLS)

def _pick(arr: list[str], seed: int) -> str:
    return arr[abs(seed) % len(arr)]

def _slugify(text: str) -> str:
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", (text or "").lower()))[:60]

def _normalize_vibe(vibe: str) -> str:
    return vibe.strip().lower() if vibe and vibe.strip().lower() in ALLOWED_VIBES else "playful"

def _build_session_vibe(persona: str = "Lina", vibe: str = "playful", idea: str = "") -> dict:
    normalized = _normalize_vibe(vibe)
    return {"persona": persona, "vibe": normalized, "short_prompt": f"{normalized} {persona} live-play session with flirty tension, clear stakes, and escalating choices.{f' Theme: {idea}.' if idea else ''}".strip(), "notes": ["Keep prompts short and visual so video clips stay coherent.", "Each branch should reveal personality, not just information.", "Escalate emotional stakes across choices to improve retention."]}

def _build_branching_video_project(payload: 'BranchRequest') -> dict:
    normalized = _normalize_vibe(payload.vibe)
    scenes = []
    for index in range(payload.scene_count):
        scene_number = index + 1
        focus = "hook" if scene_number == 1 else "resolution" if scene_number == payload.scene_count else "decision"
        scenes.append({"id": f"scene_{scene_number}", "title": f"{payload.persona} {focus} {scene_number}", "purpose": f"Open with {payload.persona}'s core charm and establish the user's goal." if focus == "hook" else "Resolve consequences and route to one of the endings." if focus == "resolution" else f"Present branching choice {scene_number - 1} with emotional tradeoffs.", "video_prompt": f"{normalized} tone, {payload.persona} in focus{f' with {payload.companion}' if payload.companion else ''}, cinematic framing, crisp dialogue beats.", "choices": [] if focus == "resolution" else [{"id": f"scene_{scene_number}_choice_a", "label": "Lean in", "outcome": "Increases intimacy and narrative risk."}, {"id": f"scene_{scene_number}_choice_b", "label": "Play it safe", "outcome": "Keeps trust high but reduces dramatic payoff."}]})

    project_id = f"liveplay-{_slugify(payload.persona)}-{str(int(time.time()))[-6:]}"
    return {"project_id": project_id, "mode": "persona-live-play", "persona": payload.persona, "companion": payload.companion or None, "render_media": "image" if payload.render_mode == "image" else "video", "idea": payload.idea or _pick(EXAMPLE_IDEAS, len(payload.persona)), "vibe_prompt": _build_session_vibe(payload.persona, normalized, payload.idea)["short_prompt"], "format": {"type": "branching-ai-video", "has_scenes": True, "has_choices": True, "has_endings": True}, "scenes": scenes, "endings": [{"id": "ending_growth", "title": "Growth Arc", "summary": "User unlocks confident mastery."}, {"id": "ending_balance", "title": "Balanced Arc", "summary": "User succeeds with stable trust."}, {"id": "ending_chaos", "title": "Chaos Arc", "summary": "Bold risks create a memorable twist."}], "production_readiness": {"status": "ready-for-production", "checks": ["Scene-to-choice continuity included", "3 unique endings provided", "Video prompts are concise and reusable", "Supports fast image mode fallback"]}}

class VibeRequest(BaseModel):
    persona: str = "Lina"
    vibe: str = "playful"
    idea: str = ""

class BranchRequest(BaseModel):
    persona: str = "Lina"
    companion: str = ""
    idea: str = ""
    vibe: str = "playful"
    render_mode: str = "video"
    scene_count: int = Field(default=4, ge=3, le=6)

@app.post('/describe_session_vibe', response_model=ResultResponse)
async def describe_session_vibe(payload: VibeRequest) -> dict:
    return {"result": _build_session_vibe(payload.persona, payload.vibe, payload.idea)}

@app.post('/build_branching_video_project', response_model=ResultResponse)
async def build_branching_video_project(payload: BranchRequest) -> dict:
    return {"result": _build_branching_video_project(payload)}

@app.post('/suggest_live_play_examples', response_model=ResultResponse)
async def suggest_live_play_examples() -> dict:
    return {"result": {"examples": EXAMPLE_IDEAS, "guidance": "Choose a concrete audience and a measurable outcome for best branching quality."}}

def _run_tool(tool: str, arguments: dict) -> dict:
    if tool == 'describe_session_vibe':
        req = VibeRequest.model_validate(arguments)
        return _build_session_vibe(req.persona, req.vibe, req.idea)
    if tool == 'build_branching_video_project':
        return _build_branching_video_project(BranchRequest.model_validate(arguments))
    if tool == 'suggest_live_play_examples':
        return {"examples": EXAMPLE_IDEAS, "guidance": "Choose a concrete audience and a measurable outcome for best branching quality."}
    raise ValueError(f"Unknown tool: {tool}")

attach_context_forge_routes(app, TOOLS, _run_tool)
