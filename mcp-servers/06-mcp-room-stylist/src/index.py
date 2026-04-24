from __future__ import annotations
import os, sys
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python_common')))
from app_base import ResultResponse, attach_context_forge_routes, create_base_app

TOOLS = [{"name": "suggest_room_decor", "description": "Suggests room décor and layout ideas."}]
app = create_base_app("mcp-room-stylist", TOOLS)

class DecorRequest(BaseModel):
    room_type: str = Field(default="living room")
    style: str = Field(default="modern")
    budget: str = Field(default="medium")

def _suggest_room_decor(payload: DecorRequest) -> dict:
    return {"room_type": payload.room_type, "style": payload.style, "layout": ["Anchor seating to one focal point.", "Use layered lighting: ambient + task + accent."], "shopping_list": [f"{payload.style} area rug", "Statement lamp", "Textured throw pillows"], "budget_band": payload.budget}

@app.post('/suggest_room_decor', response_model=ResultResponse)
async def suggest_room_decor(payload: DecorRequest) -> dict:
    return {"result": _suggest_room_decor(payload)}

def _run_tool(tool: str, arguments: dict) -> dict:
    if tool == 'suggest_room_decor':
        return _suggest_room_decor(DecorRequest.model_validate(arguments))
    raise ValueError(f"Unknown tool: {tool}")

attach_context_forge_routes(app, TOOLS, _run_tool)
