"""OpenAI-compatible vision provider (OpenAI, local LLMs, proxies)."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from agentic_vision.auth.openai_compat import OpenAICompatProvider as OpenAICompatAuth
from agentic_vision.providers.base import (
    AuthFailureError,
    InvalidImageError,
    ModelInfo,
    ModelUnavailableError,
    ProviderError,
    RateLimitError,
    VisionProvider,
)

_DEFAULT_MODELS = ["gpt-4o", "gpt-4o-mini"]


class OpenAICompatVisionProvider(VisionProvider):
    """Vision provider for OpenAI-compatible APIs."""

    def __init__(self, auth: OpenAICompatAuth | None = None) -> None:
        self._auth = auth or OpenAICompatAuth()

    @property
    def name(self) -> str:
        return "openai"

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        model: str,
        *,
        timeout: int = 120,
    ) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError("openai not installed: uv sync") from exc

        img = Path(image_path)
        if not img.exists():
            raise InvalidImageError(f"Image not found: {image_path}")

        api_key = self._auth.get_access_token()
        mime, _ = mimetypes.guess_type(str(img))
        if not mime or not mime.startswith("image/"):
            mime = "image/png"
        b64 = base64.b64encode(img.read_bytes()).decode()
        data_url = f"data:{mime};base64,{b64}"

        try:
            client = OpenAI(api_key=api_key, base_url=self._auth.base_url, timeout=timeout)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            msg = str(exc)
            if "429" in msg:
                raise RateLimitError(msg) from exc
            if "401" in msg or "403" in msg:
                raise AuthFailureError(msg) from exc
            if "404" in msg:
                raise ModelUnavailableError(msg) from exc
            raise ProviderError(msg) from exc

    def list_models(self) -> list[ModelInfo]:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._auth.get_access_token(), base_url=self._auth.base_url)
            models = client.models.list()
            return [
                ModelInfo(name=m.id, provider=self.name, supports_vision=True) for m in models.data
            ]
        except Exception:
            return [ModelInfo(name=m, provider=self.name) for m in _DEFAULT_MODELS]
