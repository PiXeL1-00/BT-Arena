from .costs import GROK_2_PRICING
from .openai_compatible import OpenAICompatibleClient
from .preflight_constants import PROVIDER_BASE_URLS


class GrokClient(OpenAICompatibleClient):
    BASE_URL = PROVIDER_BASE_URLS["grok"]
    PRICING = GROK_2_PRICING
