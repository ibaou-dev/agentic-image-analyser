"""Abstract base class for authentication providers."""
from __future__ import annotations

from abc import ABC, abstractmethod


class AuthProvider(ABC):
    """Abstract authentication provider."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider has the required credentials configured."""

    @abstractmethod
    def get_access_token(self) -> str:
        """
        Return a valid access token.

        For OAuth providers: refreshes if expired.
        For API-key providers: returns the key directly.

        Raises:
            AuthError: if credentials are missing or refresh fails.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""


class AuthError(Exception):
    """Raised when authentication fails or credentials are unavailable."""
