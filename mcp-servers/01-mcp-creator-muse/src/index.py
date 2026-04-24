from __future__ import annotations
import os, sys
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python_common')))
from app_base import ResultResponse, attach_context_forge_routes, create_base_app

TOOLS = [{"name": "creator_muse_inspire", "description": "Generates creative ideas."}]
app = create_base_app("mcp-creator-muse", TOOLS)

class InspireRequest(BaseModel):
    topic: str = Field(default="social campaign")
    medium: str = Field(default="short video")
    audience: str = Field(default="general")

def _creator_muse_inspire(payload: InspireRequest) -> dict:
    return {
        "hook": f"Start with a surprising {payload.topic} contradiction.",
        "concepts": [
            f"Behind-the-scenes {payload.medium} diary for {payload.audience}.",
            f"Myth vs fact carousel focused on {payload.topic}.",
            f"Audience challenge with 7-day {payload.topic} prompts.",
        ],
        "cta": "End with one concrete audience action and a measurable success metric.",
    }

@app.post('/creator_muse_inspire', response_model=ResultResponse)
async def creator_muse_inspire(payload: InspireRequest) -> dict:
    return {"result": _creator_muse_inspire(payload)}

def _run_tool(tool: str, arguments: dict) -> dict:
    if tool == 'creator_muse_inspire':
        return _creator_muse_inspire(InspireRequest.model_validate(arguments))
    raise ValueError(f"Unknown tool: {tool}")

attach_context_forge_routes(app, TOOLS, _run_tool)
