from __future__ import annotations
import os, sys
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python_common')))
from app_base import ResultResponse, attach_context_forge_routes, create_base_app

TOOLS = [{"name": "lead_meditation", "description": "Leads a meditation session."}]
app = create_base_app("mcp-mindfulness-coach", TOOLS)

class MeditationRequest(BaseModel):
    duration_minutes: int = Field(default=10, ge=1, le=60)
    focus: str = Field(default="breath")
    intensity: str = Field(default="gentle")

def _lead_meditation(payload: MeditationRequest) -> dict:
    return {"duration_minutes": payload.duration_minutes, "focus": payload.focus, "script": ["Settle your posture and soften the shoulders.", f"Bring attention to your {payload.focus} for {payload.duration_minutes} minutes.", "When distracted, gently label the thought and return to the anchor."], "close": f"End with a {payload.intensity} body scan and one intention for the next hour."}

@app.post('/lead_meditation', response_model=ResultResponse)
async def lead_meditation(payload: MeditationRequest) -> dict:
    return {"result": _lead_meditation(payload)}

def _run_tool(tool: str, arguments: dict) -> dict:
    if tool == 'lead_meditation':
        return _lead_meditation(MeditationRequest.model_validate(arguments))
    raise ValueError(f"Unknown tool: {tool}")

attach_context_forge_routes(app, TOOLS, _run_tool)
