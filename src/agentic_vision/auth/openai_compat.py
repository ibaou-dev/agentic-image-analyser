"""OpenAI-compatible API authentication provider."""
from __future__ import annotations

import os

from agentic_vision.auth.base import AuthError, AuthProvider


class OpenAICompatProvider(AuthProvider):
    """Auth provider for OpenAI-compatible endpoints."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    @property
    def name(self) -> str:
        return "openai"

    @property
    def base_url(self) -> str:
        return self._base_url

    def is_available(self) -> bool:
        return bool(self._api_key)

    def get_access_token(self) -> str:
        if not self._api_key:
            raise AuthError("OPENAI_API_KEY not set.")
        return self._api_key
