from .costs import DEEPSEEK_CHAT_PRICING
from .openai_compatible import OpenAICompatibleClient
from .preflight_constants import PROVIDER_BASE_URLS


class DeepSeekClient(OpenAICompatibleClient):
    BASE_URL = PROVIDER_BASE_URLS["deepseek"]
    PRICING = DEEPSEEK_CHAT_PRICING
