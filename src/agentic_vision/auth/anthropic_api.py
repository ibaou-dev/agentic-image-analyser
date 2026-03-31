"""Anthropic API authentication provider."""

from __future__ import annotations

import os

from agentic_vision.auth.base import AuthError, AuthProvider


class AnthropicApiProvider(AuthProvider):
    """Auth provider using an Anthropic API key (ANTHROPIC_API_KEY env var)."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def get_access_token(self) -> str:
        if not self._api_key:
            raise AuthError("ANTHROPIC_API_KEY not set.")
        return self._api_key
