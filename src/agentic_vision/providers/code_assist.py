"""
Code Assist (Antigravity) vision provider.

Uses the Google Cloud Code Assist endpoint with an OAuth Bearer token.
The request wraps the standard Gemini content format in a project envelope:

    POST https://cloudcode-pa.googleapis.com/v1internal:generateContent
    Authorization: Bearer {oauth_token}

    {
      "model": "gemini-2.5-pro",
      "project": "{project_id}",
      "request": {
        "contents": [{"role": "user", "parts": [
          {"text": "..."},
          {"inline_data": {"mime_type": "image/png", "data": "<base64>"}}
        ]}],
        "generationConfig": {}
      }
    }

Response is wrapped in {"response": {...}} — unwrapped before parsing.
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from agentic_vision.auth.code_assist import resolve_project_id
from agentic_vision.auth.gemini_oauth import GeminiOAuthProvider
from agentic_vision.providers.base import (
    AuthFailureError,
    InvalidImageError,
    ModelInfo,
    ModelUnavailableError,
    ProviderError,
    RateLimitError,
    VisionProvider,
)
from agentic_vision.providers.base import TimeoutError as ProviderTimeoutError

_BASE_URL = "https://cloudcode-pa.googleapis.com"
_GENERATE_ENDPOINT = f"{_BASE_URL}/v1internal:generateContent"
_MODELS_ENDPOINT = f"{_BASE_URL}/v1internal:fetchAvailableModels"

# Models known to support vision via Code Assist (Antigravity endpoint).
# Note: gemini-2.0-* models return 404 on this endpoint — only 2.5+ are supported.
_KNOWN_VISION_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
]

_SUPPORTED_MIME_TYPES = {
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif":  "image/gif",
}


def _image_mime_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _SUPPORTED_MIME_TYPES:
        return _SUPPORTED_MIME_TYPES[ext]
    # Fallback: let mimetypes guess
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed and guessed.startswith("image/"):
        return guessed
    raise InvalidImageError(
        f"Unsupported image format: {ext!r}. "
        f"Supported: {', '.join(_SUPPORTED_MIME_TYPES)}"
    )


def _encode_image(path: Path) -> str:
    try:
        return base64.b64encode(path.read_bytes()).decode()
    except OSError as exc:
        raise InvalidImageError(f"Cannot read image file {path}: {exc}") from exc


def _parse_response(data: dict[str, Any]) -> str:
    """Extract text from the Code Assist response envelope."""
    # Unwrap {"response": {...}} envelope
    inner = data.get("response", data)
    try:
        candidates = inner.get("candidates", [])
        if not candidates:
            raise ProviderError("Provider returned empty candidates list")

        candidate = candidates[0]
        finish_reason = candidate.get("finishReason", "")

        # Check for blocked/safety responses
        if finish_reason in ("SAFETY", "BLOCKED", "PROHIBITED_CONTENT"):
            raise ProviderError(f"Response blocked by safety filters: {finish_reason}")

        content = candidate.get("content", {})
        parts = content.get("parts", [])

        # Filter out pure thinking parts; collect text parts
        texts = [
            p["text"]
            for p in parts
            if "text" in p and not p.get("thought", False)
        ]

        if texts:
            return "\n".join(texts)

        # If only thinking parts (unlikely for vision tasks), include them
        all_texts = [p["text"] for p in parts if "text" in p]
        if all_texts:
            return "\n".join(all_texts)

        raise ProviderError(
            f"No text in response (finishReason={finish_reason!r}): {str(data)[:300]}"
        )

    except ProviderError:
        raise
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(f"Unexpected response structure: {str(data)[:300]}") from exc


class CodeAssistProvider(VisionProvider):
    """
    Vision provider using the Google Code Assist endpoint with OAuth.

    Typically paired with GeminiOAuthProvider for authentication.
    """

    def __init__(
        self,
        auth: GeminiOAuthProvider | None = None,
        project_id: str | None = None,
    ) -> None:
        self._auth = auth or GeminiOAuthProvider()
        self._project_id = project_id  # cached after first resolution

    @property
    def name(self) -> str:
        return "gemini-oauth"

    def _get_project(self) -> str:
        if self._project_id is None:
            token = self._auth.get_access_token()
            self._project_id = resolve_project_id(access_token=token)
        return self._project_id

    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        model: str,
        *,
        timeout: int = 120,
    ) -> str:
        img = Path(image_path)
        if not img.exists():
            raise InvalidImageError(f"Image file not found: {image_path}")

        mime_type = _image_mime_type(img)
        b64_data = _encode_image(img)
        token = self._auth.get_access_token()
        project = self._get_project()

        body = {
            "model": model,
            "project": project,
            "request": {
                "contents": [{
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                    ],
                }],
                "generationConfig": {},
            },
        }

        try:
            resp = httpx.post(
                _GENERATE_ENDPOINT,
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=float(timeout),
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"Request timed out after {timeout}s") from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"Network error: {exc}") from exc

        self._raise_for_status(resp)
        return _parse_response(resp.json())

    def list_models(self) -> list[ModelInfo]:
        """
        Return the list of available models.

        Tries to fetch from the API; falls back to the built-in known list.
        """
        try:
            token = self._auth.get_access_token()
            project = self._get_project()
            resp = httpx.get(
                _MODELS_ENDPOINT,
                params={"project": project},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models") or data.get("availableModels") or []
            if models:
                return [
                    ModelInfo(
                        name=m.get("name", m) if isinstance(m, dict) else str(m),
                        provider=self.name,
                        supports_vision=True,
                    )
                    for m in models
                ]
        except Exception:
            pass

        # Fallback to known list
        return [
            ModelInfo(name=m, provider=self.name, supports_vision=True)
            for m in _KNOWN_VISION_MODELS
        ]

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code == 200:
            return
        body = resp.text[:300]
        if resp.status_code == 429:
            import contextlib
            retry_after: float | None = None
            with contextlib.suppress(ValueError):
                retry_after = float(resp.headers.get("retry-after", 0))
            raise RateLimitError(f"Rate limit exceeded: {body}", retry_after=retry_after)
        if resp.status_code in (401, 403):
            raise AuthFailureError(f"Auth rejected ({resp.status_code}): {body}")
        if resp.status_code == 404:
            raise ModelUnavailableError(f"Model not found: {body}")
        raise ProviderError(f"HTTP {resp.status_code}: {body}")
