from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes.datasets import router as datasets_router
from app.api.routes.galileo import router as galileo_router
from app.api.routes.models import router as models_router
from app.api.routes.runs import router as runs_router
from app.config import settings
from app.infra.db.session import init_db
from app.infra.logging_config import ShortPathFormatter, configure_logging

formatter = ShortPathFormatter(
    "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
)
configure_logging(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(settings.log_level_int)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Initialising database tables...")
        await init_db()

        logger.info("Loading datasets into Postgres...")
        from app.infra.db.session import async_session_factory
        from app.infra.dataset_loader import load_all_datasets

        async with async_session_factory() as session:
            await load_all_datasets(session)

        # wipe cache slots on startup so stale CACHE_RESULTS
        # changes don't serve outdated results
        from app.infra.db.repository import Repository

        async with async_session_factory() as session:
            repo = Repository(session)
            deleted = await repo.delete_all_cache_slots()
            await repo.commit()
            if deleted:
                logger.info("Cleared %d cached result slot(s) on startup.", deleted)

        # --- ML scoring model warm-up (optional) ---
        if settings.ml_scoring_enabled:
            try:
                from app.infra.ml.model_registry import ModelRegistry

                logger.info(
                    "Loading ONNX ML scoring models from '%s' ...",
                    settings.ml_models_dir,
                )
                ModelRegistry.warm_up()
                logger.info("ML scoring models ready (2 ONNX sessions).")
            except FileNotFoundError as e:
                logger.warning(
                    "ML_SCORING_ENABLED=true but ONNX models not found in '%s/'. "
                    "ML scoring will be disabled. Run the export script to enable: "
                    "python -m scripts.export_onnx_models --output-dir %s",
                    settings.ml_models_dir,
                    settings.ml_models_dir,
                )
                # Disable ML scoring for this session
                settings.ml_scoring_enabled = False
            except Exception as e:
                logger.error(
                    "Failed to load ML scoring models: %s. ML scoring will be disabled.",
                    e,
                    exc_info=True,
                )
                settings.ml_scoring_enabled = False

        # --- Freshness sweep scheduler (optional, skip in serverless) ---
        if not settings.serverless:
            from app.infra.scheduler import start_scheduler
            start_scheduler()
        else:
            logger.info("Serverless mode: scheduler disabled (no persistent process).")

        logger.info("Galileo Arena ready.")
    except asyncio.CancelledError:
        # Expected during hot reload - let it propagate so uvicorn can handle it
        logger.debug("Startup cancelled (likely due to hot reload)")
        raise
    except Exception:
        # Log unexpected errors during startup
        logger.exception("Error during application startup")
        raise

    try:
        yield
    finally:
        try:
            if not settings.serverless:
                from app.infra.scheduler import stop_scheduler
                stop_scheduler()
            logger.info("Shutting down.")
        except asyncio.CancelledError:
            logger.debug("Shutdown cancelled (likely due to hot reload)")
            raise


app = FastAPI(
    title="Galileo Arena",
    description="Multi-model agentic debate evaluation platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    detail = str(exc) if settings.debug else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


app.include_router(datasets_router)
app.include_router(galileo_router)
app.include_router(models_router)
app.include_router(runs_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
