"""Anthropic Claude vision provider."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from agentic_vision.auth.anthropic_api import AnthropicApiProvider
from agentic_vision.providers.base import (
    AuthFailureError,
    InvalidImageError,
    ModelInfo,
    ModelUnavailableError,
    ProviderError,
    RateLimitError,
    VisionProvider,
)

_DEFAULT_MODELS = ["claude-sonnet-4-6", "claude-haiku-4-5"]


class AnthropicVisionProvider(VisionProvider):
    """Vision provider using the Anthropic (Claude) API."""

    def __init__(self, auth: AnthropicApiProvider | None = None) -> None:
        self._auth = auth or AnthropicApiProvider()

    @property
    def name(self) -> str:
        return "anthropic"

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        model: str,
        *,
        timeout: int = 120,
    ) -> str:
        try:
            import anthropic as ant
        except ImportError as exc:
            raise ProviderError("anthropic not installed: uv sync") from exc

        img = Path(image_path)
        if not img.exists():
            raise InvalidImageError(f"Image not found: {image_path}")

        api_key = self._auth.get_access_token()
        mime, _ = mimetypes.guess_type(str(img))
        if not mime or not mime.startswith("image/"):
            mime = "image/png"
        b64 = base64.b64encode(img.read_bytes()).decode()

        try:
            client = ant.Anthropic(api_key=api_key, timeout=float(timeout))
            message = client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {  # type: ignore[list-item]
                                "type": "image",
                                "source": {"type": "base64", "media_type": mime, "data": b64},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            return "".join(block.text for block in message.content if hasattr(block, "text"))
        except Exception as exc:
            msg = str(exc)
            if "529" in msg or "overloaded" in msg.lower():
                raise RateLimitError(msg) from exc
            if "401" in msg or "403" in msg or "authentication" in msg.lower():
                raise AuthFailureError(msg) from exc
            if "404" in msg:
                raise ModelUnavailableError(msg) from exc
            raise ProviderError(msg) from exc

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(name=m, provider=self.name, supports_vision=True) for m in _DEFAULT_MODELS
        ]
