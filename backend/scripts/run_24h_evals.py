"""
24-hour continuous eval: 6 LLMs × 2 random datasets × 2 random cases per round.

Each round picks 2 fresh random datasets and 2 random cases per dataset,
then runs all 6 models against every combination.  Repeats until --hours
has elapsed (default 24).

Requires the backend API to be reachable.

Usage:
    cd backend
    python scripts/run_24h_evals.py
    python scripts/run_24h_evals.py --base http://localhost:8000 --hours 24
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Add backend to sys.path so we can import app modules
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.core.model_registry import get_scheduler_models  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-5s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run_24h")

# Load models from LLM_* env vars (auto-derived from .env)
MODELS = get_scheduler_models(settings.registered_models)

N_DATASETS = 2
N_CASES = 2


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(base: str, path: str, params: dict | None = None, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            resp = httpx.get(f"{base}{path}", params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
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
            return resp.json()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return {}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def list_datasets(base: str) -> list[dict]:
    return _get(base, "/datasets")


def get_cases(base: str, dataset_id: str) -> list[str]:
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
    payload = {
        "dataset_id": dataset_id,
        "case_id": case_id,
        "models": [model],
    }
    data = _post(base, "/runs", payload)
    return data["run_id"]


def wait_for_completion(base: str, run_id: str, timeout_s: int = 300) -> dict:
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


def run_one_round(
    base: str,
    all_datasets: list[dict],
    round_num: int,
    timeout_s: int,
) -> tuple[list[dict], int, int]:
    """Run one full round: pick datasets/cases, iterate models. Returns (results, ok, err)."""

    # Pick random datasets
    n_ds = min(N_DATASETS, len(all_datasets))
    selected_ds = random.sample(all_datasets, n_ds)
    ds_names = [d["id"] if isinstance(d, dict) else str(d) for d in selected_ds]
    log.info("Round %d — datasets: %s", round_num, ds_names)

    # Collect cases per dataset
    ds_cases: dict[str, list[str]] = {}
    for ds in selected_ds:
        ds_id = ds["id"] if isinstance(ds, dict) else str(ds)
        cases = get_cases(base, ds_id)
        if not cases:
            log.warning("  %s has no cases, skipping", ds_id)
            continue
        chosen = random.sample(cases, min(N_CASES, len(cases)))
        ds_cases[ds_id] = chosen
        log.info("  %s → cases %s", ds_id, chosen)

    if not ds_cases:
        log.warning("Round %d: no usable datasets", round_num)
        return [], 0, 0

    total_expected = sum(len(c) for c in ds_cases.values()) * len(MODELS)
    log.info(
        "Round %d: %d evals (%d datasets × %d cases × %d models)",
        round_num, total_expected, len(ds_cases), N_CASES, len(MODELS),
    )

    results: list[dict] = []
    completed = 0
    errors = 0
    idx = 0

    for ds_id, cases in ds_cases.items():
        for case_id in cases:
            for model in MODELS:
                idx += 1
                label = f"{model['provider']}/{model['model_name']}"
                log.info(
                    "  [%d/%d] %s | %s | %s",
                    idx, total_expected, ds_id, case_id, label,
                )
                try:
                    run_id = start_run(base, ds_id, case_id, model)
                    log.info("    run_id=%s — waiting …", run_id)
                    run_data = wait_for_completion(base, run_id, timeout_s=timeout_s)
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
                        "    → %s  score=%s  verdict=%s",
                        status,
                        score_info.get("score", "-"),
                        score_info.get("verdict", "-"),
                    )
                    results.append({
                        "round": round_num,
                        "dataset": ds_id, "case": case_id, "model": label,
                        "run_id": run_id, "status": status, **score_info,
                    })
                except Exception as exc:
                    errors += 1
                    log.error("    FAILED: %s", exc)
                    results.append({
                        "round": round_num,
                        "dataset": ds_id, "case": case_id, "model": label,
                        "status": "ERROR", "error": str(exc),
                    })

    return results, completed, errors


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="24h continuous eval: 6 LLMs × 2 datasets × 2 cases, looping",
    )
    parser.add_argument("--base", default="http://localhost:8000", help="Backend API base URL")
    parser.add_argument("--hours", type=float, default=24, help="Duration in hours (default 24)")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per run (seconds)")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    duration_s = args.hours * 3600
    t_start = time.time()
    deadline = t_start + duration_s

    log.info("=" * 80)
    log.info(
        "24h eval run — %d models × %d datasets × %d cases/dataset | until %s",
        len(MODELS), N_DATASETS, N_CASES,
        datetime.fromtimestamp(deadline, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    log.info("=" * 80)

    # Discover datasets once
    all_datasets = list_datasets(base)
    if not all_datasets:
        log.error("No datasets found at %s/datasets", base)
        sys.exit(1)
    log.info("Available datasets (%d): %s", len(all_datasets),
             [d["id"] for d in all_datasets])

    all_results: list[dict] = []
    total_completed = 0
    total_errors = 0
    round_num = 0

    while time.time() < deadline:
        round_num += 1
        remaining_h = (deadline - time.time()) / 3600
        log.info("")
        log.info("━" * 70)
        log.info("ROUND %d  (%.1fh remaining)", round_num, remaining_h)
        log.info("━" * 70)

        round_results, ok, err = run_one_round(
            base, all_datasets, round_num, args.timeout,
        )
        all_results.extend(round_results)
        total_completed += ok
        total_errors += err

        elapsed_h = (time.time() - t_start) / 3600
        log.info(
            "Round %d done — ok=%d err=%d | totals: %d ok, %d err in %.1fh",
            round_num, ok, err, total_completed, total_errors, elapsed_h,
        )

        # Small inter-round cooldown
        if time.time() < deadline:
            log.info("Cooldown 10s before next round …")
            time.sleep(10)

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    elapsed = time.time() - t_start
    print()
    print("=" * 110)
    print(f"{'Rnd':>3} {'Dataset':<18} {'Case':<14} {'Model':<35} {'Status':<12} {'Score':<7} {'Verdict'}")
    print("-" * 110)
    for r in all_results:
        print(
            f"{r.get('round', '?'):>3} "
            f"{r['dataset']:<18} "
            f"{r['case']:<14} "
            f"{r['model']:<35} "
            f"{r['status']:<12} "
            f"{str(r.get('score', '-')):<7} "
            f"{r.get('verdict', '-')}"
        )
    print("=" * 110)

    total_cost = sum(float(r.get("cost") or 0) for r in all_results)
    print(
        f"\nRounds: {round_num}  |  Completed: {total_completed}  |  "
        f"Errors: {total_errors}  |  Elapsed: {elapsed / 3600:.1f}h  |  "
        f"Est. cost: ${total_cost:.4f}"
    )

    if total_errors:
        log.warning("%d eval(s) failed across all rounds", total_errors)
    else:
        log.info("All %d evals completed successfully!", total_completed)


if __name__ == "__main__":
    main()
