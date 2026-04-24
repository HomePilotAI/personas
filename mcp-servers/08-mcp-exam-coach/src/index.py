from __future__ import annotations
import os, sys
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python_common')))
from app_base import ResultResponse, attach_context_forge_routes, create_base_app

TOOLS = [{"name": "generate_exam_questions", "description": "Generates practice questions."}]
app = create_base_app("mcp-exam-coach", TOOLS)

class ExamRequest(BaseModel):
    topic: str = Field(default="algebra")
    difficulty: str = Field(default="medium")
    count: int = Field(default=5, ge=1, le=20)

def _generate_exam_questions(payload: ExamRequest) -> dict:
    questions = [{"id": i + 1, "question": f"[{payload.difficulty}] {payload.topic} practice question {i + 1}", "type": "short-answer" if i % 2 else "multiple-choice"} for i in range(payload.count)]
    return {"topic": payload.topic, "difficulty": payload.difficulty, "questions": questions}

@app.post('/generate_exam_questions', response_model=ResultResponse)
async def generate_exam_questions(payload: ExamRequest) -> dict:
    return {"result": _generate_exam_questions(payload)}

def _run_tool(tool: str, arguments: dict) -> dict:
    if tool == 'generate_exam_questions':
        return _generate_exam_questions(ExamRequest.model_validate(arguments))
    raise ValueError(f"Unknown tool: {tool}")

attach_context_forge_routes(app, TOOLS, _run_tool)
