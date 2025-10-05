from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="Faculty Evaluation Server (Mock)")

# results folder under server/
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class Notify(BaseModel):
    sha: str
    pages_url: HttpUrl


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _save_result(kind: Literal["static", "dynamic", "llm"], payload: dict) -> str:
    """Persist a result JSON file and return its path (string)."""
    out = {
        "kind": kind,
        "received_at": _now_stamp(),
        **payload,
    }
    name = f"{_now_stamp()}__{kind}__{payload.get('sha','no_sha')}.json"
    path = RESULTS_DIR / name
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return str(path)


@app.get("/health")
async def health():
    return {"ok": True, "service": "faculty-server", "time": _now_stamp()}


@app.post("/evaluate/static")
async def evaluate_static(n: Notify):
    # pretend checks
    checks = [
        {"name": "license_present", "pass": True},
        {"name": "secret_scan", "pass": True},
        {"name": "readme_present", "pass": True},
    ]
    saved = _save_result(
        "static",
        {"sha": n.sha, "pages_url": str(n.pages_url), "checks": checks, "score": 3},
    )
    return {"ok": True, "saved": saved, "score": 3}


@app.post("/evaluate/dynamic")
async def evaluate_dynamic(n: Notify):
    # pretend Playwright run
    metrics = {"lcp_ms": 1400, "status_code": 200}
    saved = _save_result(
        "dynamic",
        {"sha": n.sha, "pages_url": str(n.pages_url), "metrics": metrics, "score": 5},
    )
    return {"ok": True, "saved": saved, "score": 5}


@app.post("/evaluate/llm")
async def evaluate_llm(n: Notify):
    # pretend rubric result
    rubric = [
        {"criterion": "readability", "score": 4},
        {"criterion": "structure", "score": 4},
        {"criterion": "docs_quality", "score": 3},
    ]
    total = sum(item["score"] for item in rubric)
    saved = _save_result(
        "llm",
        {"sha": n.sha, "pages_url": str(n.pages_url), "rubric": rubric, "score": total},
    )
    return {"ok": True, "saved": saved, "score": total}
