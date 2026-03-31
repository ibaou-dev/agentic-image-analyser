"""Abstract base class and shared data structures for vision providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelInfo:
    """Metadata about a model available from a provider."""

    name: str
    provider: str
    supports_vision: bool = True
    description: str = ""


class ProviderError(Exception):
    """Base class for provider-level errors."""


class RateLimitError(ProviderError):
    """Raised when the provider returns a 429 or quota-exceeded response."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class AuthFailureError(ProviderError):
    """Raised when the provider rejects credentials (401/403)."""


class ModelUnavailableError(ProviderError):
    """Raised when the requested model is not available."""


class TimeoutError(ProviderError):
    """Raised when the provider request times out."""


class InvalidImageError(ProviderError):
    """Raised when the image file is missing, unreadable, or in an unsupported format."""


class VisionProvider(ABC):
    """Abstract base for all vision analysis providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'gemini-oauth', 'gemini-api')."""

    @abstractmethod
    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        model: str,
        *,
        timeout: int = 120,
    ) -> str:
        """
        Analyse a local image file and return the full analysis text.

        Args:
            image_path:  Absolute path to a PNG, JPEG, WEBP, or GIF file.
            prompt:      The analysis instruction.
            model:       Model name to use (provider-specific).
            timeout:     Request timeout in seconds.

        Returns:
            Full analysis text from the model.

        Raises:
            InvalidImageError:    Image file missing or unreadable.
            RateLimitError:       Provider rate limit hit.
            AuthFailureError:     Auth rejected.
            ModelUnavailableError: Requested model not available.
            TimeoutError:         Request timed out.
            ProviderError:        Any other provider-level error.
        """

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """Return available vision models for this provider."""
