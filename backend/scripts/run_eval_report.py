"""
Daily LLM eval report: run evals → fetch 7-day history → graphs → social posts.

Generates:
  reports/YYYY-MM-DD/
    leaderboard.png        – horizontal bar chart of 7-day avg scores
    trend.png              – 7-day daily score trend lines per model
    linkedin_option_1.txt  – creative post option 1
    linkedin_option_2.txt  – creative post option 2
    linkedin_option_3.txt  – creative post option 3
    twitter_thread.txt     – 3-6 tweets, each ≤280 chars
    summary.json           – raw data for programmatic use

Usage:
    cd backend
    python scripts/run_eval_report.py --base http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ── Reuse core eval logic ─────────────────────────────────────────────────
from run_24h_evals import MODELS, list_datasets, run_one_round, log


# ---------------------------------------------------------------------------
# Galileo API helpers
# ---------------------------------------------------------------------------

def fetch_7day_summary(base: str) -> list[dict]:
    """GET /galileo/models/summary?window=7 → list of model summaries."""
    resp = httpx.get(f"{base}/galileo/models/summary", params={"window": 7}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("models", [])


def fetch_7day_trend(base: str) -> dict:
    """GET /galileo/models/trend?window=7&bucket=1 → {llm_id: [{bucket, score_avg, n}]}."""
    resp = httpx.get(
        f"{base}/galileo/models/trend",
        params={"window": 7, "bucket": 1},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    result: dict[str, list[dict]] = {}
    for series in data.get("series", []):
        result[series["llm_id"]] = series.get("buckets", [])
    return result


# ---------------------------------------------------------------------------
# Graph generation
# ---------------------------------------------------------------------------

def generate_leaderboard_chart(models: list[dict], out_path: Path) -> None:
    """Horizontal bar chart: models ranked by 7-day avg score."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Filter models with data and sort by window_avg
    scored = [m for m in models if m.get("window_avg") is not None]
    scored.sort(key=lambda m: m["window_avg"])

    if not scored:
        log.warning("No scored models for leaderboard chart")
        return

    names = [m.get("display_name", m["model_name"]) for m in scored]
    scores = [m["window_avg"] for m in scored]

    # Color palette
    colors = ["#FF6B6B", "#FFA07A", "#FFD93D", "#6BCB77", "#4D96FF", "#9B59B6"]
    bar_colors = [colors[i % len(colors)] for i in range(len(names))]

    fig, ax = plt.subplots(figsize=(10, max(5, len(names) * 0.7)))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    bars = ax.barh(names, scores, color=bar_colors, height=0.6, edgecolor="white", linewidth=0.5)

    # Add score labels
    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{score:.1f}", va="center", ha="left",
            fontsize=11, fontweight="bold", color="white",
        )

    ax.set_xlabel("7-Day Average Score", fontsize=12, color="white")
    ax.set_title("🏆 AI Galileo Arena — 7-Day Leaderboard", fontsize=14, fontweight="bold", color="white", pad=15)
    ax.tick_params(colors="white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#444")
    ax.spines["left"].set_color("#444")
    ax.set_xlim(0, max(scores) * 1.15)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    log.info("Leaderboard chart saved: %s", out_path)


def generate_trend_chart(
    trend_data: dict, model_lookup: dict[str, str], out_path: Path
) -> None:
    """Line chart: 7-day daily score trends per model."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    if not trend_data:
        log.warning("No trend data for trend chart")
        return

    colors = ["#FF6B6B", "#4D96FF", "#6BCB77", "#FFD93D", "#FFA07A", "#9B59B6", "#00CEC9", "#E17055"]

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    for i, (llm_id, buckets) in enumerate(trend_data.items()):
        dates = []
        scores = []
        for b in buckets:
            if b.get("score_avg") is not None:
                try:
                    dt = datetime.fromisoformat(b["bucket"].replace("Z", "+00:00"))
                    dates.append(dt)
                    scores.append(b["score_avg"])
                except (ValueError, KeyError):
                    pass
        if dates and scores:
            label = model_lookup.get(llm_id, llm_id[:12])
            ax.plot(
                dates, scores,
                marker="o", markersize=5, linewidth=2,
                color=colors[i % len(colors)], label=label,
            )

    ax.set_xlabel("Date", fontsize=11, color="white")
    ax.set_ylabel("Average Score", fontsize=11, color="white")
    ax.set_title("📈 7-Day Performance Trend", fontsize=14, fontweight="bold", color="white", pad=15)
    ax.tick_params(colors="white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#444")
    ax.spines["left"].set_color("#444")
    ax.legend(fontsize=8, loc="lower left", facecolor="#16213e", edgecolor="#444", labelcolor="white")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.grid(axis="y", alpha=0.2, color="white")

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    log.info("Trend chart saved: %s", out_path)


# ---------------------------------------------------------------------------
# Social post drafters
# ---------------------------------------------------------------------------

def _leaderboard_text(ranked: list[tuple[str, float, int]]) -> str:
    """Format ranked models as emoji leaderboard lines."""
    lines = []
    for i, (name, avg, runs) in enumerate(ranked, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        lines.append(f"{medal} {name} — {avg:.1f}")
    return "\n".join(lines)


def draft_linkedin_options(ranked: list[tuple[str, float, int]], today: str) -> list[str]:
    """Generate 2-3 creative LinkedIn post options."""
    lb = _leaderboard_text(ranked)
    top_name = ranked[0][0] if ranked else "N/A"
    top_score = ranked[0][1] if ranked else 0

    # Option 1: Data-driven professional
    opt1 = f"""🏆 Daily AI Arena Results — {today}

We pit 6 leading LLMs against each other daily in head-to-head evaluations across randomized datasets. Here's this week's leaderboard:

{lb}

The race for AI supremacy is tighter than ever. {top_name} leads with {top_score:.1f} — but the margins are razor-thin.

📊 Full trend analysis and methodology at AI Galileo Arena.

#ArtificialIntelligence #LLM #MachineLearning #AIBenchmark"""

    # Option 2: Storytelling / provocative
    opt2 = f"""The AI models have spoken. 🎤

Every day, we throw the hardest challenges at 6 top LLMs and let the scores decide who's king.

Today's verdict ({today}):

{lb}

No cherry-picking. No marketing spin. Just raw performance.

Tomorrow, everything could change. That's the beauty of the arena.

🔬 AI Galileo Arena — Where LLMs prove their worth.

#AI #LLMEvaluation #DeepLearning #TechInnovation"""

    # Option 3: Visual / minimal
    opt3 = f"""📊 Weekly AI Leaderboard Update

{lb}

6 models. Randomized datasets. Zero bias. Daily results.

{top_name} takes the crown this week at {top_score:.1f}.

Follow for daily AI performance tracking.
🔗 AI Galileo Arena

#AI #LLM #Benchmark #GPT4 #Claude #Gemini"""

    return [opt1.strip(), opt2.strip(), opt3.strip()]


def draft_twitter_thread(ranked: list[tuple[str, float, int]], today: str) -> list[str]:
    """Draft a Twitter thread where each tweet is ≤280 chars (free tier)."""
    top = ranked[:3] if len(ranked) >= 3 else ranked

    # Tweet 1: Headline
    t1 = f"🏆 Daily AI Arena Results ({today})\n\n"
    for i, (name, avg, _) in enumerate(top):
        medal = {0: "🥇", 1: "🥈", 2: "🥉"}[i]
        t1 += f"{medal} {name}: {avg:.1f}\n"
    t1 += "\n6 LLMs tested daily. No bias. 🧵👇"

    # Tweet 2: Methodology
    t2 = (
        "How it works:\n\n"
        "• 2 random datasets picked daily\n"
        "• 2 cases per dataset\n"
        "• All 6 models run on identical inputs\n"
        "• Scored on correctness, grounding, calibration\n\n"
        "No cherry-picking. Pure performance."
    )

    # Tweet 3: Key insight
    if len(ranked) >= 2:
        gap = ranked[0][1] - ranked[1][1]
        t3 = (
            f"Key insight: {ranked[0][0]} leads by just {gap:.1f} points "
            f"over {ranked[1][0]}.\n\n"
            "The gap between top models keeps shrinking. "
            "Competition is driving real improvement. 📈"
        )
    else:
        t3 = "The competition between top AI models keeps getting tighter every week. 📈"

    # Tweet 4: CTA
    t4 = (
        "Follow for daily AI performance updates.\n\n"
        "AI Galileo Arena — Where LLMs prove their worth. 🔬\n\n"
        "#AI #LLM #Benchmark #GPT4o #Claude #Gemini"
    )

    tweets = [t1.strip(), t2.strip(), t3.strip(), t4.strip()]

    # Validate lengths
    for i, t in enumerate(tweets):
        if len(t) > 280:
            log.warning("Tweet %d is %d chars (over 280), truncating", i + 1, len(t))
            tweets[i] = t[:277] + "..."

    return tweets


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run eval round + generate social media report")
    parser.add_argument("--base", default="http://localhost:8000", help="Backend API base URL")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per run (seconds)")
    parser.add_argument("--skip-eval", action="store_true", help="Skip running evals, just fetch data and generate")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    today = datetime.now(tz=timezone.utc).strftime("%b %d, %Y")
    today_dir = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    reports_dir = Path(__file__).resolve().parent.parent / "reports" / today_dir
    reports_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Run today's evals ────────────────────────────────────
    if not args.skip_eval:
        all_datasets = list_datasets(base)
        if not all_datasets:
            log.error("No datasets found at %s/datasets", base)
            sys.exit(1)
        log.info("Running eval round: %d models × 2 datasets × 2 cases", len(MODELS))
        results, ok, err = run_one_round(base, all_datasets, round_num=1, timeout_s=args.timeout)
        log.info("Eval round done: %d ok, %d errors", ok, err)
    else:
        log.info("Skipping eval round (--skip-eval)")

    # ── Step 2: Fetch 7-day historical data ──────────────────────────
    log.info("Fetching 7-day summary from Galileo API...")
    try:
        summary_models = fetch_7day_summary(base)
    except Exception as e:
        log.error("Failed to fetch summary: %s", e)
        summary_models = []

    log.info("Fetching 7-day trend from Galileo API...")
    try:
        trend_data = fetch_7day_trend(base)
    except Exception as e:
        log.error("Failed to fetch trend: %s", e)
        trend_data = {}

    if not summary_models:
        log.error("No model summary data available")
        sys.exit(1)

    # Build lookup: llm_id → display_name
    model_lookup = {
        m["llm_id"]: m.get("display_name", m.get("model_name", m["llm_id"]))
        for m in summary_models
    }

    # Build ranked list (by window_avg descending)
    scored = [m for m in summary_models if m.get("window_avg") is not None]
    scored.sort(key=lambda m: m["window_avg"], reverse=True)
    ranked = [
        (m.get("display_name", m["model_name"]), m["window_avg"], m.get("window_runs", 0))
        for m in scored
    ]

    # ── Step 3: Generate graphs ──────────────────────────────────────
    log.info("Generating graphs...")
    generate_leaderboard_chart(summary_models, reports_dir / "leaderboard.png")
    generate_trend_chart(trend_data, model_lookup, reports_dir / "trend.png")

    # ── Step 4: Draft social posts ───────────────────────────────────
    log.info("Drafting social media posts...")

    linkedin_options = draft_linkedin_options(ranked, today)
    for i, opt in enumerate(linkedin_options, 1):
        path = reports_dir / f"linkedin_option_{i}.txt"
        path.write_text(opt, encoding="utf-8")
        log.info("LinkedIn option %d saved: %s (%d chars)", i, path, len(opt))

    tweets = draft_twitter_thread(ranked, today)
    thread_text = "\n\n---\n\n".join(f"[Tweet {i+1}/{len(tweets)}]\n{t}" for i, t in enumerate(tweets))
    thread_path = reports_dir / "twitter_thread.txt"
    thread_path.write_text(thread_text, encoding="utf-8")
    log.info("Twitter thread saved: %s (%d tweets)", thread_path, len(tweets))

    # Save raw data as JSON
    summary_json = {
        "date": today_dir,
        "ranked": [{"name": n, "avg": a, "runs": r} for n, a, r in ranked],
        "tweet_lengths": [len(t) for t in tweets],
    }
    (reports_dir / "summary.json").write_text(json.dumps(summary_json, indent=2), encoding="utf-8")

    # ── Print summary ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"📁 Report directory: {reports_dir}")
    print(f"📊 Graphs: leaderboard.png, trend.png")
    print(f"📝 LinkedIn: 3 options (linkedin_option_1/2/3.txt)")
    print(f"🐦 Twitter: {len(tweets)} tweets (twitter_thread.txt)")
    for i, t in enumerate(tweets):
        print(f"   Tweet {i+1}: {len(t)} chars {'✅' if len(t) <= 280 else '⚠️ OVER 280'}")
    print(f"{'='*60}\n")

    log.info("Done!")


if __name__ == "__main__":
    main()
