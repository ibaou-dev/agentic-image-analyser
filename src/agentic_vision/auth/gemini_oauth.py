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
import re
import shutil
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
    Extract OAuth client_id and client_secret from the installed Gemini CLI.

    Tries in order:
      1. Environment variables GEMINI_CLI_OAUTH_CLIENT_ID / GEMINI_CLI_OAUTH_CLIENT_SECRET
      2. Searching for oauth2.js in the Gemini CLI package tree
    """
    client_id = os.environ.get("GEMINI_CLI_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GEMINI_CLI_OAUTH_CLIENT_SECRET")
    if client_id and client_secret:
        return client_id, client_secret

    gemini_bin = shutil.which("gemini")
    if not gemini_bin:
        return None

    search_root = Path(gemini_bin).resolve().parent.parent
    for oauth_js in search_root.rglob("oauth2.js"):
        try:
            text = oauth_js.read_text(errors="ignore")
        except OSError:
            continue
        ids = re.findall(r"(\d+-[a-z0-9]+\.apps\.googleusercontent\.com)", text)
        secrets = re.findall(r"(GOCSPX-[A-Za-z0-9_-]+)", text)
        if ids and secrets:
            return ids[0], secrets[0]

    return None


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
                f"Gemini OAuth credentials not found at {self._creds_path}. "
                "Run: gemini auth login"
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
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise AuthError(f"Token refresh failed: {exc}") from exc

        data = resp.json()
        updated = creds.copy()
        updated["access_token"] = data["access_token"]
        updated["expiry_date"] = int(
            (time.time() + data.get("expires_in", 3600)) * 1000
        )
        if "refresh_token" in data:
            updated["refresh_token"] = data["refresh_token"]

        self._write_creds(updated)
        return updated

    def _write_creds(self, creds: dict[str, Any]) -> None:
        """Atomically write updated credentials back to disk."""
        tmp = self._creds_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(creds, indent=2), encoding="utf-8")
        tmp.rename(self._creds_path)
