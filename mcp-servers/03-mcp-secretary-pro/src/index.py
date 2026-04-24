from __future__ import annotations
import os, sys
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python_common')))
from app_base import ResultResponse, attach_context_forge_routes, create_base_app

TOOLS = [{"name": "manage_schedule", "description": "Manages schedules and reminders."}]
app = create_base_app("mcp-secretary-pro", TOOLS)

class ScheduleItem(BaseModel):
    title: str
    duration_minutes: int = Field(default=30, ge=5, le=240)
    priority: str = Field(default="medium")

class ScheduleRequest(BaseModel):
    day: str = Field(default="Monday")
    tasks: list[ScheduleItem] = Field(default_factory=list)

def _manage_schedule(payload: ScheduleRequest) -> dict:
    tasks = payload.tasks or [ScheduleItem(title="Inbox triage")]
    planned, cursor = [], 9 * 60
    for task in tasks:
        start_h, start_m = divmod(cursor, 60)
        cursor += task.duration_minutes
        end_h, end_m = divmod(cursor, 60)
        planned.append({
            "title": task.title,
            "priority": task.priority,
            "slot": f"{start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d}",
        })
    return {"day": payload.day, "schedule": planned, "reminder_policy": "15-minute pre-event reminders"}

@app.post('/manage_schedule', response_model=ResultResponse)
async def manage_schedule(payload: ScheduleRequest) -> dict:
    return {"result": _manage_schedule(payload)}

def _run_tool(tool: str, arguments: dict) -> dict:
    if tool == 'manage_schedule':
        return _manage_schedule(ScheduleRequest.model_validate(arguments))
    raise ValueError(f"Unknown tool: {tool}")

attach_context_forge_routes(app, TOOLS, _run_tool)
