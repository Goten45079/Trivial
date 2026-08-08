from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "src"

ModelName = Literal["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]
Environment = Literal["Production", "Staging", "Development"]

MODEL_RATES = {"gpt-4.1": 0.0075, "gpt-4.1-mini": 0.0016, "gpt-4.1-nano": 0.00045}

CALLS = [
    {"id": "req_7fa1", "time": "09:05", "model": "gpt-4.1", "env": "Production", "prompt": 1280, "completion": 640, "latency": 920, "status": "success", "endpoint": "/chat/respond"},
    {"id": "req_81bd", "time": "09:20", "model": "gpt-4.1-mini", "env": "Production", "prompt": 820, "completion": 280, "latency": 510, "status": "success", "endpoint": "/support/summarize"},
    {"id": "req_92ac", "time": "10:00", "model": "gpt-4.1-mini", "env": "Staging", "prompt": 460, "completion": 190, "latency": 440, "status": "success", "endpoint": "/qa/classify"},
    {"id": "req_13cc", "time": "10:35", "model": "gpt-4.1", "env": "Production", "prompt": 2400, "completion": 970, "latency": 1380, "status": "error", "endpoint": "/chat/respond"},
    {"id": "req_56ed", "time": "11:15", "model": "gpt-4.1-nano", "env": "Development", "prompt": 360, "completion": 90, "latency": 220, "status": "success", "endpoint": "/dev/extract"},
    {"id": "req_66aa", "time": "12:10", "model": "gpt-4.1-mini", "env": "Production", "prompt": 1360, "completion": 420, "latency": 690, "status": "success", "endpoint": "/support/summarize"},
    {"id": "req_34be", "time": "13:35", "model": "gpt-4.1", "env": "Staging", "prompt": 1760, "completion": 880, "latency": 1120, "status": "success", "endpoint": "/batch/generate"},
    {"id": "req_09df", "time": "14:50", "model": "gpt-4.1-mini", "env": "Production", "prompt": 720, "completion": 310, "latency": 530, "status": "error", "endpoint": "/qa/classify"},
]

class BudgetConfig(BaseModel):
    monthly: float = Field(1200, ge=0)
    warning: float = Field(75, ge=0, le=100)
    errorRate: float = Field(3, ge=0, le=100)
    latency: int = Field(900, ge=0)

budget_config = BudgetConfig()
app = FastAPI(title="LLM Lens API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/src", StaticFiles(directory=STATIC_DIR), name="src")


def call_cost(call: dict) -> float:
    return ((call["prompt"] + call["completion"]) / 1000) * MODEL_RATES[call["model"]]


def filtered_calls(model: str = "All", env: str = "All") -> list[dict]:
    return [c for c in CALLS if (model == "All" or c["model"] == model) and (env == "All" or c["env"] == env)]


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/observability")
def observability(model: str = Query("All"), env: str = Query("All")) -> dict:
    rows = filtered_calls(model, env)
    tokens = sum(c["prompt"] + c["completion"] for c in rows)
    spend = sum(call_cost(c) for c in rows)
    errors = sum(1 for c in rows if c["status"] == "error")
    avg_latency = round(sum(c["latency"] for c in rows) / max(len(rows), 1))
    error_rate = errors / max(len(rows), 1) * 100
    return {
        "calls": [{**c, "tokens": c["prompt"] + c["completion"], "cost": call_cost(c)} for c in rows],
        "metrics": {"tokens": tokens, "spend": spend, "projectedMonthlySpend": spend * 30, "avgLatency": avg_latency, "errorRate": error_rate},
        "modelRates": MODEL_RATES,
        "environments": ["Production", "Staging", "Development"],
    }


@app.get("/api/budget")
def get_budget() -> BudgetConfig:
    return budget_config


@app.put("/api/budget")
def update_budget(config: BudgetConfig) -> BudgetConfig:
    global budget_config
    budget_config = config
    return budget_config


@app.get("/api/optimizations")
def optimizations() -> list[dict]:
    return [
        {"title": "Route classification traffic to nano", "impact": "Save ~72% on low-complexity QA calls", "text": "The /qa/classify endpoint has short completions and predictable outputs. Use gpt-4.1-nano with stricter schemas."},
        {"title": "Trim prompt context for chat", "impact": "Reduce 1.2k prompt tokens per slow call", "text": "Chat requests above 2k prompt tokens correlate with latency spikes. Summarize older turns before sending."},
        {"title": "Cache support summaries", "impact": "Avoid repeated summarization spend", "text": "Production summary calls share similar endpoint patterns. Cache by ticket revision and invalidate on updates."},
    ]
