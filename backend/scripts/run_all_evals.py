"""
Batch eval: 5 LLMs × 6 datasets × 3 random cases.

Requires the backend API to be reachable.
Usage:
    cd backend
    python scripts/run_all_evals.py --base https://galileo.masxai.com/api
    python scripts/run_all_evals.py [--base URL] [--datasets N] [--cases N] [--timeout S]
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
import time

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s")
log = logging.getLogger("run_all_evals")

MODELS = [
    {"provider": "openai",    "model_name": "gpt-4o",                   "api_key_env": "OPENAI_API_KEY"},
    {"provider": "anthropic", "model_name": "claude-sonnet-4-20250514", "api_key_env": "ANTHROPIC_API_KEY"},
    {"provider": "mistral",   "model_name": "mistral-large-latest",     "api_key_env": "MISTRAL_API_KEY"},
    {"provider": "deepseek",  "model_name": "deepseek-chat",            "api_key_env": "DEEPSEEK_API_KEY"},
    {"provider": "grok",      "model_name": "grok-3",                   "api_key_env": "GROK_API_KEY"},
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(base: str, path: str, params: dict | None = None, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            resp = httpx.get(f"{base}{path}", params=params, timeout=15)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                log.error("GET %s%s returned non-JSON: %s", base, path, resp.text[:200])
                raise
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return {}


def _post(base: str, path: str, payload: dict, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            resp = httpx.post(f"{base}{path}", json=payload, timeout=15)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                log.error("POST %s%s returned non-JSON: %s", base, path, resp.text[:200])
                raise
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return {}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def list_datasets(base: str) -> list[dict]:
    """Fetch all datasets from the API."""
    return _get(base, "/datasets")


def get_cases(base: str, dataset_id: str) -> list[str]:
    """Return list of case_id strings for a dataset."""
    data = _get(base, f"/datasets/{dataset_id}")
    cases = data.get("cases", [])
    result = []
    for c in cases:
        if isinstance(c, dict):
            result.append(c.get("case_id") or c.get("id") or str(list(c.values())[0]))
        else:
            result.append(str(c))
    return result


def start_run(base: str, dataset_id: str, case_id: str, model: dict) -> str:
    """POST /runs and return the run_id."""
    payload = {
        "dataset_id": dataset_id,
        "case_id": case_id,
        "models": [model],
    }
    data = _post(base, "/runs", payload)
    return data["run_id"]


def wait_for_completion(base: str, run_id: str, timeout_s: int = 300) -> dict:
    """Poll GET /runs/{run_id} until completed or failed."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            data = _get(base, f"/runs/{run_id}")
            status = (data.get("status") or "").upper()
            if status == "COMPLETED":
                return data
            if status in ("FAILED", "ERROR"):
                return data
        except Exception as exc:
            log.warning("  poll error: %s", exc)
        time.sleep(3)
    raise TimeoutError(f"Run {run_id} did not complete within {timeout_s}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch eval: 5 LLMs × N datasets × M random cases")
    parser.add_argument("--base", default="http://localhost:8000", help="Backend API base URL (e.g. https://galileo.masxai.com/api)")
    parser.add_argument("--datasets", type=int, default=6, help="Max datasets to use")
    parser.add_argument("--cases", type=int, default=3, help="Random cases per dataset")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per run (seconds)")
    args = parser.parse_args()

    base = args.base.rstrip("/")

    # ------------------------------------------------------------------
    # 1) Discover datasets
    # ------------------------------------------------------------------
    all_datasets = list_datasets(base)
    if not all_datasets:
        log.error("No datasets found at %s/datasets", base)
        sys.exit(1)

    n_ds = min(args.datasets, len(all_datasets))
    selected_ds = random.sample(all_datasets, n_ds) if len(all_datasets) > n_ds else all_datasets
    ds_names = [d["id"] if isinstance(d, dict) else str(d) for d in selected_ds]
    log.info("Selected %d dataset(s): %s", n_ds, ds_names)

    # ------------------------------------------------------------------
    # 2) For each dataset, pick random cases
    # ------------------------------------------------------------------
    ds_cases: dict[str, list[str]] = {}
    for ds in selected_ds:
        ds_id = ds["id"] if isinstance(ds, dict) else str(ds)
        cases = get_cases(base, ds_id)
        if not cases:
            log.warning("Dataset %s has no cases, skipping", ds_id)
            continue
        chosen = random.sample(cases, min(args.cases, len(cases)))
        ds_cases[ds_id] = chosen
        log.info("  %s: %d case(s) → %s", ds_id, len(chosen), chosen)

    if not ds_cases:
        log.error("No valid datasets with cases found.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3) Run all combinations
    # ------------------------------------------------------------------
    total_expected = sum(len(c) for c in ds_cases.values()) * len(MODELS)
    log.info(
        "Running %d evals total: %d dataset(s) × %d case(s) × %d model(s)",
        total_expected, len(ds_cases), args.cases, len(MODELS),
    )

    results: list[dict] = []
    completed = 0
    errors = 0
    t0 = time.time()

    for ds_id, cases in ds_cases.items():
        for case_id in cases:
            for model in MODELS:
                label = f"{model['provider']}/{model['model_name']}"
                log.info(
                    "[%d/%d] %s | %s | %s",
                    completed + errors + 1, total_expected, ds_id, case_id, label,
                )
                try:
                    run_id = start_run(base, ds_id, case_id, model)
                    log.info("  run_id=%s — waiting ...", run_id)
                    run_data = wait_for_completion(base, run_id, timeout_s=args.timeout)
                    status = (run_data.get("status") or "?").upper()

                    score_info: dict = {}
                    if status == "COMPLETED":
                        try:
                            summary = _get(base, f"/runs/{run_id}/summary")
                            score_info = {
                                "score": summary.get("overall_score"),
                                "verdict": summary.get("verdict"),
                                "cost": summary.get("total_llm_cost"),
                            }
                        except Exception:
                            pass
                        completed += 1
                    else:
                        errors += 1

                    log.info(
                        "  → %s  score=%s  verdict=%s",
                        status,
                        score_info.get("score", "-"),
                        score_info.get("verdict", "-"),
                    )
                    results.append({
                        "dataset": ds_id, "case": case_id, "model": label,
                        "run_id": run_id, "status": status, **score_info,
                    })
                except Exception as exc:
                    errors += 1
                    log.error("  FAILED: %s", exc)
                    results.append({
                        "dataset": ds_id, "case": case_id, "model": label,
                        "status": "ERROR", "error": str(exc),
                    })

    elapsed = time.time() - t0

    # ------------------------------------------------------------------
    # 4) Summary table
    # ------------------------------------------------------------------
    print()
    print("=" * 100)
    print(f"{'Dataset':<18} {'Case':<14} {'Model':<35} {'Status':<12} {'Score':<7} {'Verdict'}")
    print("-" * 100)
    for r in results:
        print(
            f"{r['dataset']:<18} "
            f"{r['case']:<14} "
            f"{r['model']:<35} "
            f"{r['status']:<12} "
            f"{str(r.get('score', '-')):<7} "
            f"{r.get('verdict', '-')}"
        )
    print("=" * 100)

    total_cost = sum(float(r.get("cost") or 0) for r in results)
    print(f"\nCompleted: {completed}/{total_expected}  |  Errors: {errors}  |  "
          f"Elapsed: {elapsed:.0f}s  |  Est. cost: ${total_cost:.4f}")

    if errors:
        log.warning("%d eval(s) failed", errors)
        sys.exit(1)
    else:
        log.info("All %d evals completed successfully!", completed)


if __name__ == "__main__":
    main()
