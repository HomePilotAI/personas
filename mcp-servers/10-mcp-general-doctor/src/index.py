from __future__ import annotations
import os, sys
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python_common')))
from app_base import ResultResponse, attach_context_forge_routes, create_base_app

TOOLS = [{"name": "general_health_advice", "description": "Provides general health advice."}]
app = create_base_app("mcp-general-doctor", TOOLS)

class HealthAdviceRequest(BaseModel):
    concern: str = Field(default="sleep quality")
    age_group: str = Field(default="adult")

def _general_health_advice(payload: HealthAdviceRequest) -> dict:
    return {"concern": payload.concern, "guidance": ["Prioritize hydration, balanced nutrition, and regular movement.", "Track symptom patterns and triggers for two weeks.", "Seek urgent care for severe or rapidly worsening symptoms."], "disclaimer": f"General information only for {payload.age_group}; not a diagnosis."}

@app.post('/general_health_advice', response_model=ResultResponse)
async def general_health_advice(payload: HealthAdviceRequest) -> dict:
    return {"result": _general_health_advice(payload)}

def _run_tool(tool: str, arguments: dict) -> dict:
    if tool == 'general_health_advice':
        return _general_health_advice(HealthAdviceRequest.model_validate(arguments))
    raise ValueError(f"Unknown tool: {tool}")

attach_context_forge_routes(app, TOOLS, _run_tool)
