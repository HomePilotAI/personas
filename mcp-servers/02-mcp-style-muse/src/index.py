from __future__ import annotations
import os, sys
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python_common')))
from app_base import ResultResponse, attach_context_forge_routes, create_base_app

TOOLS = [{"name": "suggest_style", "description": "Suggests style and fashion ideas."}]
app = create_base_app("mcp-style-muse", TOOLS)

class StyleRequest(BaseModel):
    occasion: str = Field(default="casual day")
    palette: str = Field(default="neutral")
    climate: str = Field(default="mild")

def _suggest_style(payload: StyleRequest) -> dict:
    layering = "add a light jacket" if payload.climate.lower() in {"cold", "chilly"} else "keep layers breathable"
    return {
        "occasion": payload.occasion,
        "outfit": [
            f"Base: {payload.palette} top with tailored bottoms.",
            f"Accent: one statement accessory aligned to {payload.occasion}.",
            f"Footwear: comfort-first shoes suitable for {payload.climate} weather.",
        ],
        "styling_note": layering,
    }

@app.post('/suggest_style', response_model=ResultResponse)
async def suggest_style(payload: StyleRequest) -> dict:
    return {"result": _suggest_style(payload)}

def _run_tool(tool: str, arguments: dict) -> dict:
    if tool == 'suggest_style':
        return _suggest_style(StyleRequest.model_validate(arguments))
    raise ValueError(f"Unknown tool: {tool}")

attach_context_forge_routes(app, TOOLS, _run_tool)
