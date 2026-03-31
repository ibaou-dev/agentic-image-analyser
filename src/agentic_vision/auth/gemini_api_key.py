"""Gemini API key authentication provider."""

from __future__ import annotations

import os

from agentic_vision.auth.base import AuthError, AuthProvider


class GeminiApiKeyProvider(AuthProvider):
    """Auth provider using a Gemini API key (GEMINI_API_KEY env var)."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    @property
    def name(self) -> str:
        return "gemini-api"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def get_access_token(self) -> str:
        if not self._api_key:
            raise AuthError(
                "GEMINI_API_KEY not set. Get an API key at https://aistudio.google.com/apikey"
            )
        return self._api_key
