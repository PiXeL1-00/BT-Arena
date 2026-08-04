import pytest

from app.core.domain.model_identity import (
    InvalidModelKeyError,
    ModelIdentity,
    build_model_key,
    parse_model_key,
)


class TestParseModelKey:
    def test_basic(self):
        identity = parse_model_key("openai/gpt-4o")
        assert identity.provider == "openai"
        assert identity.model_name == "gpt-4o"
        assert identity.version is None

    def test_with_version(self):
        identity = parse_model_key("anthropic/claude-3@v2")
        assert identity.provider == "anthropic"
        assert identity.model_name == "claude-3"
        assert identity.version == "v2"

    def test_provider_lowercased(self):
        identity = parse_model_key("OpenAI/gpt-4o")
        assert identity.provider == "openai"

    def test_model_name_preserves_case(self):
        identity = parse_model_key("deepseek/DeepSeek-R1")
        assert identity.model_name == "DeepSeek-R1"

    def test_version_with_dots(self):
        identity = parse_model_key("gemini/flash@2.0.1")
        assert identity.version == "2.0.1"

    def test_empty_version_treated_as_none(self):
        identity = parse_model_key("openai/gpt-4o@")
        assert identity.version is None

    def test_no_slash_raises(self):
        with pytest.raises(InvalidModelKeyError):
            parse_model_key("openai-gpt-4o")

    def test_empty_string_raises(self):
        with pytest.raises(InvalidModelKeyError):
            parse_model_key("")

    def test_missing_provider_raises(self):
        with pytest.raises(InvalidModelKeyError):
            parse_model_key("/gpt-4o")

    def test_missing_model_raises(self):
        with pytest.raises(InvalidModelKeyError):
            parse_model_key("openai/")

    def test_error_preserves_model_key(self):
        with pytest.raises(InvalidModelKeyError) as exc_info:
            parse_model_key("bad")
        assert exc_info.value.model_key == "bad"


class TestBuildModelKey:
    def test_without_version(self):
        identity = ModelIdentity(provider="openai", model_name="gpt-4o")
        assert build_model_key(identity) == "openai/gpt-4o"

    def test_with_version(self):
        identity = ModelIdentity(provider="anthropic", model_name="claude-3", version="v2")
        assert build_model_key(identity) == "anthropic/claude-3@v2"

    def test_roundtrip(self):
        original = "deepseek/chat@v1.5"
        rebuilt = build_model_key(parse_model_key(original))
        assert rebuilt == original

    def test_roundtrip_no_version(self):
        original = "gemini/flash"
        rebuilt = build_model_key(parse_model_key(original))
        assert rebuilt == original


class TestModelIdentityFrozen:
    def test_immutable(self):
        identity = parse_model_key("openai/gpt-4o")
        with pytest.raises(AttributeError):
            identity.provider = "changed"  # type: ignore[misc]

    def test_hashable(self):
        a = parse_model_key("openai/gpt-4o")
        b = parse_model_key("OpenAI/gpt-4o")
        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_different_models_not_equal(self):
        a = parse_model_key("openai/gpt-4o")
        b = parse_model_key("openai/gpt-4o-mini")
        assert a != b
