"""
Gemini CLI OAuth authentication provider.

Reads the OAuth credentials written by `gemini auth login` from
~/.gemini/oauth_creds.json and auto-refreshes the access token when it
approaches expiry.

Credential file fields:
    access_token   str
    refresh_token  str
    expiry_date    int   (Unix timestamp in *milliseconds*)
    scope          str
    token_type     str
    id_token       str   (optional)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from agentic_vision.auth.base import AuthError, AuthProvider

_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_EXPIRY_BUFFER_MS = 60_000  # refresh 60 seconds before actual expiry


def _default_creds_path() -> Path:
    raw = os.environ.get("GEMINI_OAUTH_CREDS_PATH", "~/.gemini/oauth_creds.json")
    return Path(raw).expanduser()


def _extract_client_credentials() -> tuple[str, str] | None:
    """
    Return the OAuth client_id and client_secret for token refresh.

    Tries in order:
      1. Environment variables GEMINI_CLI_OAUTH_CLIENT_ID / GEMINI_CLI_OAUTH_CLIENT_SECRET
      2. Well-known Gemini CLI application credentials (same ones embedded in the
         CLI binary and published in community tools like opencode-gemini-auth)
    """
    client_id = os.environ.get("GEMINI_CLI_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GEMINI_CLI_OAUTH_CLIENT_SECRET")
    if client_id and client_secret:
        return client_id, client_secret

    # The Gemini CLI OAuth application credentials are semi-public (embedded in the
    # CLI binary, published in opencode-gemini-auth/src/constants.ts, etc.).
    # They identify the application, not the user.
    from agentic_vision.auth.gemini_login import _CLIENT_ID, _CLIENT_SECRET

    return _CLIENT_ID, _CLIENT_SECRET


class GeminiOAuthProvider(AuthProvider):
    """
    Auth provider backed by the Gemini CLI OAuth credentials file.

    Automatically refreshes the access token when it expires.
    """

    def __init__(self, creds_path: Path | None = None) -> None:
        self._creds_path = creds_path or _default_creds_path()
        self._cached_creds: dict[str, Any] | None = None

    @property
    def name(self) -> str:
        return "gemini-oauth"

    def is_available(self) -> bool:
        return self._creds_path.exists()

    def get_access_token(self) -> str:
        """Return a valid (possibly refreshed) access token."""
        creds = self._load_creds()
        if self._is_expired(creds):
            creds = self._refresh(creds)
        return str(creds["access_token"])

    # ── private ────────────────────────────────────────────────────────────────

    def _load_creds(self) -> dict[str, Any]:
        if not self._creds_path.exists():
            raise AuthError(
                f"Gemini OAuth credentials not found at {self._creds_path}. Run: gemini auth login"
            )
        with self._creds_path.open() as f:
            data: dict[str, Any] = json.load(f)
            return data

    @staticmethod
    def _is_expired(creds: dict[str, Any]) -> bool:
        expiry_ms = int(creds.get("expiry_date", 0))
        now_ms = int(time.time() * 1000)
        return (now_ms + _EXPIRY_BUFFER_MS) >= expiry_ms

    def _refresh(self, creds: dict[str, Any]) -> dict[str, Any]:
        pair = _extract_client_credentials()
        if not pair:
            raise AuthError(
                "Cannot refresh Gemini OAuth token: client credentials not found.\n"
                "Set GEMINI_CLI_OAUTH_CLIENT_ID and GEMINI_CLI_OAUTH_CLIENT_SECRET "
                "in your .env file."
            )
        client_id, client_secret = pair

        try:
            resp = httpx.post(
                _TOKEN_ENDPOINT,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": creds["refresh_token"],
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=15,
            )
        except httpx.HTTPError as exc:
            raise AuthError(f"Token refresh failed (network error): {exc}") from exc

        if not resp.is_success:
            # Parse Google's error response to give a specific message
            try:
                err_body = resp.json()
                err_code = err_body.get("error", "")
                err_desc = err_body.get("error_description", resp.text[:200])
            except Exception:
                err_code, err_desc = "", resp.text[:200]

            if err_code == "invalid_grant":
                raise AuthError(
                    "Refresh token has expired or been revoked. "
                    "Run 'agentic-vision login' to re-authenticate."
                )
            raise AuthError(f"Token refresh failed ({resp.status_code}): {err_desc}")

        data = resp.json()
        updated = creds.copy()
        updated["access_token"] = data["access_token"]
        updated["expiry_date"] = int((time.time() + data.get("expires_in", 3600)) * 1000)
        if "refresh_token" in data:
            updated["refresh_token"] = data["refresh_token"]

        self._write_creds(updated)
        return updated

    def _write_creds(self, creds: dict[str, Any]) -> None:
        """Atomically write updated credentials back to disk."""
        tmp = self._creds_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(creds, indent=2), encoding="utf-8")
        tmp.rename(self._creds_path)
