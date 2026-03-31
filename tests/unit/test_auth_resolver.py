"""Unit tests for auth resolver and simple auth providers."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from agentic_vision.auth.anthropic_api import AnthropicApiProvider
from agentic_vision.auth.base import AuthError
from agentic_vision.auth.gemini_api_key import GeminiApiKeyProvider
from agentic_vision.auth.openai_compat import OpenAICompatProvider
from agentic_vision.auth.resolver import AuthResolver


class TestGeminiApiKeyProvider:
    def test_is_available_with_key(self) -> None:
        p = GeminiApiKeyProvider(api_key="AIza-test")
        assert p.is_available() is True

    def test_is_available_without_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            p = GeminiApiKeyProvider(api_key=None)
            # Ensure env var is not set
            p._api_key = ""
            assert p.is_available() is False

    def test_get_token_returns_key(self) -> None:
        p = GeminiApiKeyProvider(api_key="AIza-mykey")
        assert p.get_access_token() == "AIza-mykey"

    def test_raises_when_no_key(self) -> None:
        p = GeminiApiKeyProvider(api_key="")
        with pytest.raises(AuthError, match="GEMINI_API_KEY"):
            p.get_access_token()

    def test_name(self) -> None:
        assert GeminiApiKeyProvider().name == "gemini-api"


class TestOpenAICompatProvider:
    def test_is_available(self) -> None:
        p = OpenAICompatProvider(api_key="sk-test")
        assert p.is_available() is True

    def test_base_url_default(self) -> None:
        p = OpenAICompatProvider(api_key="sk-test")
        assert "openai.com" in p.base_url

    def test_custom_base_url(self) -> None:
        p = OpenAICompatProvider(api_key="sk-test", base_url="http://localhost:11434/v1")
        assert p.base_url == "http://localhost:11434/v1"

    def test_raises_when_no_key(self) -> None:
        p = OpenAICompatProvider(api_key="")
        with pytest.raises(AuthError):
            p.get_access_token()


class TestAnthropicApiProvider:
    def test_is_available(self) -> None:
        p = AnthropicApiProvider(api_key="sk-ant-test")
        assert p.is_available() is True

    def test_raises_when_no_key(self) -> None:
        p = AnthropicApiProvider(api_key="")
        with pytest.raises(AuthError):
            p.get_access_token()

    def test_name(self) -> None:
        assert AnthropicApiProvider().name == "anthropic"


class TestAuthResolver:
    def test_resolve_by_name_unknown_raises(self) -> None:
        resolver = AuthResolver()
        with pytest.raises(AuthError, match="Unknown provider"):
            resolver.resolve_by_name("nonexistent-provider")

    def test_resolve_by_name_gemini_api_when_key_set(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-test"}):
            resolver = AuthResolver()
            provider = resolver.resolve_by_name("gemini-api")
            assert provider.name == "gemini-api"

    def test_resolve_by_name_raises_when_not_configured(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            resolver = AuthResolver()
            # Force no key by patching is_available
            with (
                patch(
                    "agentic_vision.auth.gemini_api_key.GeminiApiKeyProvider.is_available",
                    return_value=False,
                ),
                pytest.raises(AuthError, match="not configured"),
            ):
                resolver.resolve_by_name("gemini-api")

    def test_all_available_empty_when_no_auth(self, tmp_path: object) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "GEMINI_API_KEY": "",
                    "OPENAI_API_KEY": "",
                    "ANTHROPIC_API_KEY": "",
                },
            ),
            patch(
                "agentic_vision.auth.gemini_oauth.GeminiOAuthProvider.is_available",
                return_value=False,
            ),
            patch(
                "agentic_vision.auth.gemini_api_key.GeminiApiKeyProvider.is_available",
                return_value=False,
            ),
            patch(
                "agentic_vision.auth.openai_compat.OpenAICompatProvider.is_available",
                return_value=False,
            ),
            patch(
                "agentic_vision.auth.anthropic_api.AnthropicApiProvider.is_available",
                return_value=False,
            ),
        ):
            resolver = AuthResolver()
            assert resolver.all_available() == []
