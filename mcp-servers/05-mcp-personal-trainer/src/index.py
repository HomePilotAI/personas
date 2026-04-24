from __future__ import annotations
import os, sys
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python_common')))
from app_base import ResultResponse, attach_context_forge_routes, create_base_app

TOOLS = [{"name": "generate_workout_plan", "description": "Generates a workout plan."}]
app = create_base_app("mcp-personal-trainer", TOOLS)

class WorkoutRequest(BaseModel):
    goal: str = Field(default="general fitness")
    days_per_week: int = Field(default=3, ge=1, le=7)
    level: str = Field(default="beginner")

def _generate_workout_plan(payload: WorkoutRequest) -> dict:
    sessions = [{"day": index + 1, "focus": "strength" if index % 2 == 0 else "conditioning", "duration_minutes": 45 if payload.level == "beginner" else 60} for index in range(payload.days_per_week)]
    return {"goal": payload.goal, "level": payload.level, "plan": sessions, "recovery": "At least one full rest day weekly."}

@app.post('/generate_workout_plan', response_model=ResultResponse)
async def generate_workout_plan(payload: WorkoutRequest) -> dict:
    return {"result": _generate_workout_plan(payload)}

def _run_tool(tool: str, arguments: dict) -> dict:
    if tool == 'generate_workout_plan':
        return _generate_workout_plan(WorkoutRequest.model_validate(arguments))
    raise ValueError(f"Unknown tool: {tool}")

attach_context_forge_routes(app, TOOLS, _run_tool)
