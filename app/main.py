from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.settings import Settings, get_settings
from app.store import DEFAULT_RATES, TelemetryStore

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "src"

CallStatus = Literal["success", "error"]


class BudgetConfig(BaseModel):
    monthly: float = Field(1200, ge=0)
    warning: float = Field(75, ge=0, le=100)
    errorRate: float = Field(3, ge=0, le=100)
    latency: int = Field(900, ge=0)


class CallTelemetry(BaseModel):
    id: str = Field(default_factory=lambda: f"req_{uuid4().hex[:10]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    model: str = Field(..., min_length=1)
    env: str = Field(..., min_length=1)
    prompt: int = Field(..., ge=0)
    completion: int = Field(..., ge=0)
    latency: int = Field(..., ge=0)
    status: CallStatus
    endpoint: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    accepted: int
    ids: list[str]


settings = get_settings()
store = TelemetryStore(settings.database_path)
app = FastAPI(title="LLM Lens API", version="1.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
app.mount("/src", StaticFiles(directory=STATIC_DIR), name="src")


def require_api_key(x_api_key: str = Header(default=""), config: Settings = Depends(get_settings)) -> None:
    if config.api_key and x_api_key != config.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")


def serialize_call(call: CallTelemetry) -> dict:
    payload = call.model_dump()
    payload["timestamp"] = call.timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return payload


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}


@app.get("/api/observability")
def observability(model: str = Query("All"), env: str = Query("All"), limit: int = Query(500, ge=1, le=5000)) -> dict:
    rows = store.list_calls(model, env, limit)
    tokens = sum(c["tokens"] for c in rows)
    spend = sum(c["cost"] for c in rows)
    errors = sum(1 for c in rows if c["status"] == "error")
    avg_latency = round(sum(c["latency"] for c in rows) / max(len(rows), 1))
    error_rate = errors / max(len(rows), 1) * 100
    return {
        "calls": rows,
        "metrics": {"tokens": tokens, "spend": spend, "projectedMonthlySpend": spend * 30, "avgLatency": avg_latency, "errorRate": error_rate},
        "modelRates": DEFAULT_RATES,
        "models": store.list_models(),
        "environments": store.list_environments(),
    }


@app.post("/api/calls", response_model=IngestResponse, dependencies=[Depends(require_api_key)])
def ingest_call(call: CallTelemetry) -> IngestResponse:
    payload = serialize_call(call)
    store.record_call(payload)
    return IngestResponse(accepted=1, ids=[payload["id"]])


@app.post("/api/calls/batch", response_model=IngestResponse, dependencies=[Depends(require_api_key)])
def ingest_calls(calls: list[CallTelemetry]) -> IngestResponse:
    payloads = [serialize_call(call) for call in calls]
    store.record_many(payloads)
    return IngestResponse(accepted=len(payloads), ids=[call["id"] for call in payloads])


@app.get("/api/budget")
def get_budget() -> BudgetConfig:
    return BudgetConfig(**store.get_budget())


@app.put("/api/budget", dependencies=[Depends(require_api_key)])
def update_budget(config: BudgetConfig) -> BudgetConfig:
    return BudgetConfig(**store.update_budget(config.model_dump()))


@app.get("/api/optimizations")
def optimizations() -> list[dict]:
    rows = store.list_calls(limit=5000)
    chat_tokens = sum(c["tokens"] for c in rows if c["endpoint"] == "/chat/respond")
    errors = [c for c in rows if c["status"] == "error"]
    slow = [c for c in rows if c["latency"] >= store.get_budget()["latency"]]
    return [
        {"title": "Route classification traffic to nano", "impact": "Save on low-complexity QA calls", "text": "Calls to /qa/classify are short and schema-like. Route them to a smaller model and enforce structured outputs."},
        {"title": "Summarize long chat context", "impact": f"Target {chat_tokens:,} chat tokens", "text": "Chat traffic is the largest token bucket. Summarize older turns before forwarding context to premium models."},
        {"title": "Investigate reliability hot spots", "impact": f"{len(errors)} errors and {len(slow)} slow calls in scope", "text": "Review endpoints with repeated errors or latency breaches before increasing spend limits."},
    ]
