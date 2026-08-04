"""
One-shot: run one evaluation per LLM provider, wait for completion, then verify analytics DB.
Uses POST /runs (background tasks) instead of /runs/start to avoid asyncio.create_task issues.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time

import httpx

from app.infra.llm.preflight_constants import API_KEY_ENV_NAMES

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s")
log = logging.getLogger("verify")

BASE = "http://localhost:8000"

MODELS = [
    {"provider": "openai",    "model_name": "gpt-4o",                   "api_key_env": API_KEY_ENV_NAMES["openai"]},
    {"provider": "anthropic", "model_name": "claude-sonnet-4-20250514",         "api_key_env": API_KEY_ENV_NAMES["anthropic"]},
    {"provider": "mistral",   "model_name": "mistral-large-latest",     "api_key_env": API_KEY_ENV_NAMES["mistral"]},
    {"provider": "deepseek",  "model_name": "deepseek-chat",            "api_key_env": API_KEY_ENV_NAMES["deepseek"]},
    {"provider": "gemini",    "model_name": "gemini-2.0-flash",         "api_key_env": API_KEY_ENV_NAMES["gemini"]},
    {"provider": "grok",      "model_name": "grok-3",                   "api_key_env": API_KEY_ENV_NAMES["grok"]},
]


def sync_get(url: str, params: dict | None = None, retries: int = 3) -> dict:
    """Simple synchronous GET with retries."""
    for attempt in range(retries):
        try:
            resp = httpx.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return {}


def sync_post(url: str, payload: dict, retries: int = 3) -> dict:
    """Simple synchronous POST with retries."""
    for attempt in range(retries):
        try:
            resp = httpx.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return {}


def get_first_case() -> str:
    data = sync_get(f"{BASE}/datasets/climate")
    cases = data.get("cases", [])
    if not cases:
        raise RuntimeError("No cases in climate dataset")
    c0 = cases[0]
    if isinstance(c0, dict):
        return c0.get("id") or c0.get("case_id") or str(list(c0.values())[0])
    return str(c0)


def start_run(model: dict, case_id: str) -> str:
    payload = {
        "dataset_id": "climate",
        "case_id": case_id,
        "models": [model],
    }
    data = sync_post(f"{BASE}/runs", payload)
    return data["run_id"]


def wait_for_completion(run_id: str, timeout_s: int = 180) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            data = sync_get(f"{BASE}/runs/{run_id}")
            status = data.get("status", "")
            if status in ("completed", "COMPLETED"):
                return data
            elif status in ("failed", "FAILED", "error", "ERROR"):
                return data
        except Exception as exc:
            log.warning("  poll error (retrying): %s", exc)
        time.sleep(3)
    raise TimeoutError(f"Run {run_id} did not complete within {timeout_s}s")


def main():
    case_id = get_first_case()
    log.info("Dataset: climate | Case: %s", case_id)

    results = []
    for model in MODELS:
        label = f"{model['provider']}/{model['model_name']}"
        log.info("Starting %s ...", label)
        try:
            run_id = start_run(model, case_id)
            log.info("  run_id=%s", run_id)
            run_data = wait_for_completion(run_id)
            status = run_data.get("status", "?")

            score_info = {}
            if status.upper() == "COMPLETED":
                try:
                    summary = sync_get(f"{BASE}/runs/{run_id}/summary")
                    score_info = {
                        "overall_score": summary.get("overall_score"),
                        "verdict": summary.get("verdict"),
                    }
                except Exception as exc:
                    log.warning("  Could not get summary: %s", exc)
            log.info("  => status=%s score=%s verdict=%s",
                     status, score_info.get("overall_score", "N/A"),
                     score_info.get("verdict", "N/A"))
            results.append({"model": label, "run_id": run_id, "status": status, **score_info})
        except Exception as exc:
            log.error("  %s FAILED: %s", label, exc)
            results.append({"model": label, "status": "ERROR", "error": str(exc)})

    # Check analytics
    log.info("")
    log.info("--- Analytics DB Check ---")
    try:
        analytics = sync_get(f"{BASE}/galileo/models/summary", params={"window": 30})
        db_models = analytics.get("models", [])
        log.info("Models in analytics DB: %d", len(db_models))
        for m in db_models:
            log.info("  %s/%s: avg=%.1f runs=%d",
                     m.get("provider", "?"), m.get("model_name", "?"),
                     m.get("all_time_avg") or 0, m.get("all_time_runs", 0))
    except Exception as exc:
        log.error("Analytics check failed: %s", exc)

    # Summary table
    print()
    print("=" * 75)
    print(f"{'Model':<40} {'Status':<12} {'Score':<8} {'Verdict'}")
    print("-" * 75)
    for r in results:
        print(f"{r['model']:<40} {r['status']:<12} "
              f"{str(r.get('overall_score', '-')):<8} "
              f"{r.get('verdict', '-')}")
    print("=" * 75)

    failures = [r for r in results if r.get("status", "").upper() not in ("COMPLETED",)]
    if failures:
        log.warning("%d model(s) did not complete successfully", len(failures))
        sys.exit(1)
    else:
        log.info("All %d models completed successfully!", len(results))


if __name__ == "__main__":
    main()
