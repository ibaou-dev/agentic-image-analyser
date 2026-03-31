"""
Gemini direct provider using the google-generativeai SDK and an API key.

Uses generativelanguage.googleapis.com via the official SDK — no OAuth needed.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from agentic_vision.auth.gemini_api_key import GeminiApiKeyProvider
from agentic_vision.providers.base import (
    AuthFailureError,
    InvalidImageError,
    ModelInfo,
    ModelUnavailableError,
    ProviderError,
    RateLimitError,
    VisionProvider,
)

_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_DEFAULT_MODELS = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]


class GeminiDirectProvider(VisionProvider):
    """Vision provider using the Gemini API key path (google-generativeai SDK)."""

    def __init__(self, auth: GeminiApiKeyProvider | None = None) -> None:
        self._auth = auth or GeminiApiKeyProvider()

    @property
    def name(self) -> str:
        return "gemini-api"

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        model: str,
        *,
        timeout: int = 120,
    ) -> str:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ProviderError("google-generativeai not installed: uv sync") from exc

        img = Path(image_path)
        if not img.exists():
            raise InvalidImageError(f"Image not found: {image_path}")
        if img.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            raise InvalidImageError(f"Unsupported format: {img.suffix}")

        api_key = self._auth.get_access_token()
        genai.configure(api_key=api_key)

        mime, _ = mimetypes.guess_type(str(img))
        if not mime or not mime.startswith("image/"):
            mime = "image/png"

        image_data = {"mime_type": mime, "data": base64.b64encode(img.read_bytes()).decode()}

        try:
            client = genai.GenerativeModel(model)
            response = client.generate_content([prompt, image_data])
            return response.text or ""
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower():
                raise RateLimitError(msg) from exc
            if "401" in msg or "403" in msg or "API_KEY_INVALID" in msg:
                raise AuthFailureError(msg) from exc
            if "404" in msg or "not found" in msg.lower():
                raise ModelUnavailableError(msg) from exc
            raise ProviderError(msg) from exc

    def list_models(self) -> list[ModelInfo]:
        try:
            import google.generativeai as genai

            api_key = self._auth.get_access_token()
            genai.configure(api_key=api_key)
            models = [
                ModelInfo(name=m.name.split("/")[-1], provider=self.name, supports_vision=True)
                for m in genai.list_models()
                if "generateContent" in getattr(m, "supported_generation_methods", [])
                and "vision" in getattr(m, "description", "").lower()
            ]
            return models or [
                ModelInfo(name=m, provider=self.name, supports_vision=True) for m in _DEFAULT_MODELS
            ]
        except Exception:
            return [
                ModelInfo(name=m, provider=self.name, supports_vision=True) for m in _DEFAULT_MODELS
            ]
