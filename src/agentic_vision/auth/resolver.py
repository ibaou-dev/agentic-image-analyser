"""
Auth resolver — tries providers in priority order and returns the first available one.

Priority:
  1. gemini-oauth  — Gemini CLI OAuth token (~/.gemini/oauth_creds.json)
  2. gemini-api    — GEMINI_API_KEY
  3. openai        — OPENAI_API_KEY
  4. anthropic     — ANTHROPIC_API_KEY

For Code Assist specifically, gemini-oauth is always used regardless of order
(it requires an OAuth token, not an API key).
"""
from __future__ import annotations

from agentic_vision.auth.anthropic_api import AnthropicApiProvider
from agentic_vision.auth.base import AuthError, AuthProvider
from agentic_vision.auth.gemini_api_key import GeminiApiKeyProvider
from agentic_vision.auth.gemini_oauth import GeminiOAuthProvider
from agentic_vision.auth.openai_compat import OpenAICompatProvider

_PROVIDER_ORDER: list[type[AuthProvider]] = [
    GeminiOAuthProvider,
    GeminiApiKeyProvider,
    OpenAICompatProvider,
    AnthropicApiProvider,
]


class AuthResolver:
    """Resolves the first available auth provider in priority order."""

    def resolve(self) -> AuthProvider:
        """Return the first available auth provider."""
        for cls in _PROVIDER_ORDER:
            provider = cls()
            if provider.is_available():
                return provider
        raise AuthError(
            "No auth provider configured. Set one of:\n"
            "  - Run: gemini auth login  (Gemini CLI OAuth)\n"
            "  - GEMINI_API_KEY env var\n"
            "  - OPENAI_API_KEY env var\n"
            "  - ANTHROPIC_API_KEY env var"
        )

    def resolve_by_name(self, name: str) -> AuthProvider:
        """Return the auth provider matching the given provider name."""
        name_to_cls: dict[str, type[AuthProvider]] = {
            "gemini-oauth": GeminiOAuthProvider,
            "gemini-api":   GeminiApiKeyProvider,
            "openai":       OpenAICompatProvider,
            "anthropic":    AnthropicApiProvider,
        }
        cls = name_to_cls.get(name)
        if cls is None:
            raise AuthError(f"Unknown provider name: {name!r}. Known: {list(name_to_cls)}")
        provider = cls()
        if not provider.is_available():
            raise AuthError(f"Provider {name!r} is not configured (missing credentials)")
        return provider

    def all_available(self) -> list[AuthProvider]:
        """Return all configured providers in priority order."""
        return [cls() for cls in _PROVIDER_ORDER if cls().is_available()]
