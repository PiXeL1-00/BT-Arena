"""APScheduler wrapper for scheduled jobs.

Jobs:
- Freshness sweep (daily, when sweep_enabled)
- Monthly eval (1st of month, prod mode only)
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

_SWEEP_JOB_ID = "galileo_freshness_sweep"
_EVAL_JOB_ID = "galileo_monthly_eval"


async def _sweep_job() -> None:
    from app.infra.db.session import async_session_factory
    from app.usecases.freshness_sweep import run_freshness_sweep

    try:
        async with async_session_factory() as session:
            result = await run_freshness_sweep(session)
            logger.info("Scheduled sweep result: %s", result.get("message", "done"))
    except Exception:
        logger.exception("Scheduled sweep failed")


async def _monthly_eval_job() -> None:
    from app.infra.db.session import async_session_factory
    from app.usecases.scheduled_eval import run_scheduled_eval

    try:
        async with async_session_factory() as session:
            result = await run_scheduled_eval(session)
            logger.info("Monthly eval result: %s", result)
    except Exception:
        logger.exception("Monthly eval job failed")


def start_scheduler() -> None:
    global _scheduler
    has_sweep = settings.sweep_enabled
    has_eval = settings.eval_scheduler_enabled and not settings.debug

    if not has_sweep and not has_eval:
        logger.info("All schedulers disabled")
        return
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()

    if has_sweep:
        _scheduler.add_job(
            _sweep_job,
            trigger=CronTrigger(hour=settings.sweep_cron_hour, minute=0),
            id=_SWEEP_JOB_ID,
            replace_existing=True,
            max_instances=1,
        )
        logger.info(
            "Sweep scheduler started (daily at %02d:00 UTC)",
            settings.sweep_cron_hour,
        )

    if has_eval:
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(settings.app_timezone)
        except (ImportError, KeyError):
            from datetime import timezone
            tz = timezone.utc
        _scheduler.add_job(
            _monthly_eval_job,
            trigger=CronTrigger(
                day=settings.eval_scheduler_cron_day,
                hour=settings.eval_scheduler_cron_hour,
                minute=0,
                timezone=tz,
            ),
            id=_EVAL_JOB_ID,
            replace_existing=True,
            max_instances=1,
        )
        logger.info(
            "Monthly eval scheduler started (day %d at %02d:00 %s)",
            settings.eval_scheduler_cron_day,
            settings.eval_scheduler_cron_hour,
            settings.app_timezone,
        )

    _scheduler.start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
