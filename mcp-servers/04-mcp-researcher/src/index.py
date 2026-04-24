from __future__ import annotations
import os, sys
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'python_common')))
from app_base import ResultResponse, attach_context_forge_routes, create_base_app

TOOLS = [
    {"name": "search_arxiv", "description": "Searches the arXiv repository."},
    {"name": "read_paper", "description": "Retrieves and returns paper metadata."},
    {"name": "summarize_paper", "description": "Summarises a given paper."},
    {"name": "compare_papers", "description": "Compares multiple papers."},
    {"name": "build_literature_brief", "description": "Builds a literature brief."},
]
app = create_base_app("mcp-researcher", TOOLS)

class QueryReq(BaseModel):
    query: str = Field(default="large language models")

class PaperReq(BaseModel):
    paper_id: str = Field(default="arXiv:1706.03762")

class SummReq(BaseModel):
    title: str = "Attention Is All You Need"
    abstract: str = "Transformer architecture for sequence modeling."

class CompareReq(BaseModel):
    papers: list[dict] = Field(default_factory=list)

class BriefReq(BaseModel):
    topic: str = "AI safety"
    papers: list[dict] = Field(default_factory=list)

def _search_arxiv(payload: QueryReq) -> dict:
    return {"query": payload.query, "results": [{"paper_id": "arXiv:1706.03762", "title": "Attention Is All You Need"}, {"paper_id": "arXiv:2005.14165", "title": "Language Models are Few-Shot Learners"}]}

def _read_paper(payload: PaperReq) -> dict:
    return {"paper_id": payload.paper_id, "title": "Sample Paper", "authors": ["A. Researcher"], "year": 2024}

def _summarize_paper(payload: SummReq) -> dict:
    return {"title": payload.title, "summary": f"This work studies: {payload.abstract[:180]}", "key_points": ["Method proposal", "Empirical evaluation", "Limitations discussed"]}

def _compare_papers(payload: CompareReq) -> dict:
    papers = payload.papers or [{"title": "Paper A"}, {"title": "Paper B"}]
    return {"count": len(papers), "comparison": [{"dimension": "method", "note": "Different modeling assumptions"}, {"dimension": "evaluation", "note": "Benchmarks partially overlap"}]}

def _build_literature_brief(payload: BriefReq) -> dict:
    return {"topic": payload.topic, "sections": ["Landscape", "Leading methods", "Gaps", "Open questions"], "recommended_next_step": "Run a focused replication study on the most cited method."}

@app.post('/search_arxiv', response_model=ResultResponse)
async def search_arxiv(payload: QueryReq) -> dict:
    return {"result": _search_arxiv(payload)}

@app.post('/read_paper', response_model=ResultResponse)
async def read_paper(payload: PaperReq) -> dict:
    return {"result": _read_paper(payload)}

@app.post('/summarize_paper', response_model=ResultResponse)
async def summarize_paper(payload: SummReq) -> dict:
    return {"result": _summarize_paper(payload)}

@app.post('/compare_papers', response_model=ResultResponse)
async def compare_papers(payload: CompareReq) -> dict:
    return {"result": _compare_papers(payload)}

@app.post('/build_literature_brief', response_model=ResultResponse)
async def build_literature_brief(payload: BriefReq) -> dict:
    return {"result": _build_literature_brief(payload)}

def _run_tool(tool: str, arguments: dict) -> dict:
    if tool == 'search_arxiv':
        return _search_arxiv(QueryReq.model_validate(arguments))
    if tool == 'read_paper':
        return _read_paper(PaperReq.model_validate(arguments))
    if tool == 'summarize_paper':
        return _summarize_paper(SummReq.model_validate(arguments))
    if tool == 'compare_papers':
        return _compare_papers(CompareReq.model_validate(arguments))
    if tool == 'build_literature_brief':
        return _build_literature_brief(BriefReq.model_validate(arguments))
    raise ValueError(f"Unknown tool: {tool}")

attach_context_forge_routes(app, TOOLS, _run_tool)
