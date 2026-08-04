"""App settings -- all config from env vars via pydantic-settings."""

from __future__ import annotations

import logging
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from app.core.model_registry import RegisteredModel

_BACKEND_ROOT = Path(__file__).parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"


# Debate-mode defaults (prod)
DEFAULT_DEBATE_ENABLED_PRODUCTION_MODELS = "mistral/mistral-large-latest,deepseek/deepseek-chat"
DEFAULT_DEBATE_DAILY_PRODUCTION_CAP = 3
DEFAULT_EVAL_SCHEDULER_CRON_DAY = 1
DEFAULT_EVAL_SCHEDULER_CRON_HOUR = 2
DEFAULT_EVAL_SCHEDULER_DATASETS = 6
DEFAULT_EVAL_SCHEDULER_CASES = 1
DEFAULT_TIMEZONE = "Europe/Berlin"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://galileo:galileo_pass@localhost:5432/galileo_arena",
    )
    database_url_migrations: str = Field(
        default="",
        description="Separate connection string for Alembic migrations (postgres role). Falls back to database_url if empty.",
    )
    database_require_ssl: bool = Field(
        default=False,
        description="Require SSL for database connections (enable for Supabase / cloud-hosted Postgres)",
    )
    db_pool_size: int = Field(
        default=10, ge=1, le=50,
        description="SQLAlchemy async engine pool_size (persistent connections)",
    )
    db_max_overflow: int = Field(
        default=15, ge=0, le=100,
        description="SQLAlchemy async engine max_overflow (burst connections above pool_size)",
    )
    db_pool_timeout: int = Field(
        default=30, ge=5, le=120,
        description="Seconds to wait for a connection from the pool before timeout",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key from OPENAI_API_KEY env var",
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key from ANTHROPIC_API_KEY env var",
    )
    mistral_api_key: Optional[str] = Field(
        default=None,
        description="Mistral API key from MISTRAL_API_KEY env var",
    )
    deepseek_api_key: Optional[str] = Field(
        default=None,
        description="DeepSeek API key from DEEPSEEK_API_KEY env var",
    )
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Gemini API key from GEMINI_API_KEY env var",
    )
    grok_api_key: Optional[str] = Field(
        default=None,
        description="Grok API key from GROK_API_KEY env var",
    )
    moonshotai_api_key: Optional[str] = Field(
        default=None,
        description="MoonshotAI API key from MOONSHOTAI_API_KEY env var",
    )

    # --- LLM model registry (LLM_<PROVIDER>=model_name|Label|context_window) ---
    llm_openai: Optional[str] = Field(
        default=None,
        description="OpenAI model definition: model_name|Label|context_window",
    )
    llm_anthropic: Optional[str] = Field(
        default=None,
        description="Anthropic model definition: model_name|Label|context_window",
    )
    llm_mistral: Optional[str] = Field(
        default=None,
        description="Mistral model definition: model_name|Label|context_window",
    )
    llm_deepseek: Optional[str] = Field(
        default=None,
        description="DeepSeek model definition: model_name|Label|context_window",
    )
    llm_gemini: Optional[str] = Field(
        default=None,
        description="Gemini model definition: model_name|Label|context_window",
    )
    llm_grok: Optional[str] = Field(
        default=None,
        description="Grok model definition: model_name|Label",
    )
    llm_moonshotai: Optional[str] = Field(
        default=None,
        description="Moonshotai model definition: model_name|Label",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level from LOG_LEVEL env var",
    )

    # prompt versioning
    prompt_version: str = Field(
        default="v1",
        description="Prompt template version directory to use (e.g. v1, v2)",
    )

    # cache / replay
    store_result: bool = Field(
        default=False,
        description="Persist LLM results as cache slots and serve from cache when available",
    )
    
    cache_results: int = Field(
        default=4,
        ge=1,
        description="Number of cache slots per (dataset, model, case) triple",
    )

    # --- ML scoring (ONNX) ---
    ml_scoring_enabled: bool = Field(
        default=True,
        description="Enable ONNX ML-enhanced scoring (requires models in ml_models_dir)",
    )
    ml_models_dir: str = Field(
        default="models",
        description="Directory containing exported ONNX models (relative to backend root)",
    )
    onnx_intra_threads: int = Field(
        default=2, ge=1,
        description="ONNX Runtime intra-op thread count (leave cores for uvicorn)",
    )
    ml_max_workers: int = Field(
        default=2, ge=1,
        description="Max concurrent ML scoring threads in the bounded executor",
    )
    ml_nli_max_tokens: int = Field(
        default=384, ge=64, le=512,
        description="Max token length for NLI cross-encoder inputs (truncation limit)",
    )
    ml_falsifiable_threshold: float = Field(
        default=0.45, ge=0.0, le=1.0,
        description="Cosine-sim threshold for semantic falsifiability exemplar match",
    )
    ml_deference_threshold_low: float = Field(
        default=0.4,
        description="NLI entailment below this = no deference penalty",
    )
    ml_deference_threshold_mid: float = Field(
        default=0.6,
        description="NLI entailment below this = -5 deference penalty",
    )
    ml_deference_threshold_high: float = Field(
        default=0.8,
        description="NLI entailment below this = -10; above = -15 deference penalty",
    )
    ml_refusal_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="NLI entailment threshold above which refusal penalty is applied",
    )

    # --- AutoGen debate mode ---
    use_autogen_debate: bool = Field(
        default=False,
        description="Use AutoGen-powered debate orchestration instead of FSM controller",
    )
    autogen_max_cross_exam_messages: int = Field(
        default=2, ge=1, le=20,
        description="Max agent turns in AutoGen cross-examination phase",
    )
    autogen_enable_tools: bool = Field(
        default=False,
        description="Enable evidence retrieval tools for AutoGen debate agents",
    )

    _LOG_LEVEL_MAP: dict[str, int] = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    @property
    def log_level_int(self) -> int:
        return self._LOG_LEVEL_MAP.get(self.log_level.upper(), logging.INFO)

    # --- environment mode ---
    debug: bool = Field(
        default=True,
        description="Debug mode: all models enabled, no daily caps, no scheduler restrictions",
    )

    @property
    def debug_mode(self) -> bool:
        return self.debug

    # --- security ---
    allowed_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated allowed CORS origins",
    )
    trusted_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated trusted hostnames for TrustedHostMiddleware",
    )
    admin_api_key: Optional[str] = Field(
        default=None,
        description="Secret key for admin endpoints (X-Admin-Key header)",
    )
    rate_limit_default: str = Field(
        default="60/minute",
        description="Default global rate limit (slowapi format)",
    )
    rate_limit_runs: str = Field(
        default="10/minute",
        description="Rate limit for POST /runs endpoints",
    )
    max_concurrent_runs: int = Field(
        default=20, ge=1, le=100,
        description="Max concurrent background LLM tasks",
    )
    uvicorn_workers: int = Field(
        default=4, ge=1, le=16,
        description="Uvicorn worker count for production (UVICORN_WORKERS env var)",
    )
    serverless: bool = Field(
        default=False,
        description="Enable serverless mode: NullPool, no scheduler, 1 worker. "
                    "Set SERVERLESS=true on Railway for scale-to-zero.",
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def trusted_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]

    # --- debate mode (prod only, ignored when DEBUG=true) ---
    debate_daily_production_cap: int = Field(
        default=DEFAULT_DEBATE_DAILY_PRODUCTION_CAP,
        ge=1,
        description="Max debate calls per model per calendar day (prod only, ignored in debug)",
    )
    debate_enabled_production_models: str = Field(
        default=DEFAULT_DEBATE_ENABLED_PRODUCTION_MODELS,
        description="Comma-separated provider/model_name pairs allowed in production debate mode",
    )
    app_timezone: str = Field(
        default=DEFAULT_TIMEZONE,
        description="Timezone for daily cap resets and scheduler triggers",
    )

    @property
    def debate_enabled_production_model_keys(self) -> list[str]:
        return [m.strip() for m in self.debate_enabled_production_models.split(",") if m.strip()]

    @cached_property
    def registered_models(self) -> list[RegisteredModel]:
        """Parse LLM_* env vars into RegisteredModel list (cached)."""
        from app.core.model_registry import build_registry_from_settings
        return build_registry_from_settings(self)

    # --- monthly eval scheduler (prod) ---
    eval_scheduler_enabled: bool = Field(
        default=False,
        description="Enable monthly evaluation scheduler (prod only, ignored in debug)",
    )
    eval_scheduler_cron_day: int = Field(
        default=DEFAULT_EVAL_SCHEDULER_CRON_DAY,
        ge=1, le=28,
        description="Day of month for scheduled eval (1-28)",
    )
    eval_scheduler_cron_hour: int = Field(
        default=DEFAULT_EVAL_SCHEDULER_CRON_HOUR,
        ge=0, le=23,
        description="Hour (in app_timezone) for scheduled eval",
    )
    eval_scheduler_datasets: int = Field(
        default=DEFAULT_EVAL_SCHEDULER_DATASETS,
        ge=1,
        description="Number of datasets to evaluate per scheduled run",
    )
    eval_scheduler_cases: int = Field(
        default=DEFAULT_EVAL_SCHEDULER_CASES,
        ge=1,
        description="Random cases per dataset per scheduled run",
    )

    def get_api_key(self, provider: str) -> str | None:
        """Explicit provider → key mapping. No getattr."""
        key_map: dict[str, str | None] = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "mistral": self.mistral_api_key,
            "deepseek": self.deepseek_api_key,
            "gemini": self.gemini_api_key,
            "grok": self.grok_api_key,
            "moonshotai": self.moonshotai_api_key,
        }
        return key_map.get(provider.lower())

    # --- galileo sweep ---
    sweep_enabled: bool = False
    sweep_cron_hour: int = 3
    sweep_cases_count: int = 5
    sweep_include_baseline: bool = True
    sweep_max_evals_per_run: int = 50
    sweep_max_parallel: int = 3
    sweep_max_cost_usd: float = 5.0

    # --- analytics query timeouts (seconds) ---
    analytics_timeout_summary_s: int = 5
    analytics_timeout_trend_s: int = 5
    analytics_timeout_heatmap_s: int = 15
    analytics_timeout_distribution_s: int = 10
    analytics_timeout_default_s: int = 10
    analytics_cache_ttl_s: int = 60


settings = Settings()
