"""Domain exceptions -- catch specific, re-raise with context."""


class GalileoError(Exception):
    """Root for all domain errors."""


class DatasetNotFoundError(GalileoError):
    def __init__(self, dataset_id: str) -> None:
        super().__init__(f"Dataset not found: {dataset_id}")
        self.dataset_id = dataset_id


class RunNotFoundError(GalileoError):
    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run not found: {run_id}")
        self.run_id = run_id


class CaseNotFoundError(GalileoError):
    def __init__(self, run_id: str, case_id: str) -> None:
        super().__init__(f"Case {case_id} not found in run {run_id}")
        self.run_id = run_id
        self.case_id = case_id


class JudgeOutputError(GalileoError):
    """Judge produced invalid / unparseable output."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Judge output error: {reason}")
        self.reason = reason


class LLMClientError(GalileoError):
    """Wraps provider-specific LLM failures."""

    def __init__(self, provider: str, detail: str) -> None:
        super().__init__(f"[{provider}] {detail}")
        self.provider = provider
        self.detail = detail


class QuotaExhaustedError(LLMClientError):
    """Provider quota or billing limit reached — retrying won't help."""

    def __init__(self, provider: str, detail: str, *, retry_after: float | None = None) -> None:
        super().__init__(provider, detail)
        self.retry_after = retry_after


class ModelNotAllowedError(GalileoError):
    """Model is not enabled in current environment mode."""

    def __init__(self, model_key: str) -> None:
        super().__init__(f"Model not allowed in prod mode: {model_key}")
        self.model_key = model_key


class DailyCapExceededError(GalileoError):
    """Daily debate call cap reached for a model."""

    def __init__(self, model_key: str, *, cap: int) -> None:
        super().__init__(f"Daily cap ({cap}) exceeded for model: {model_key}")
        self.model_key = model_key
        self.cap = cap

