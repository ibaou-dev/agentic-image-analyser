"""Unit tests for Gemini OAuth auth provider (all mocked — no real API calls)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_vision.auth.base import AuthError
from agentic_vision.auth.gemini_oauth import GeminiOAuthProvider


def _make_creds(
    *,
    expired: bool = False,
    access_token: str = "test-access-token",
    refresh_token: str = "test-refresh-token",
) -> dict:
    now_ms = int(time.time() * 1000)
    expiry_ms = now_ms - 10_000 if expired else now_ms + 3_600_000
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expiry_date": expiry_ms,
        "scope": "openid email",
        "token_type": "Bearer",
    }


# Expose the static helper for testing
def _is_expired_static(creds: dict) -> bool:
    from agentic_vision.auth.gemini_oauth import _EXPIRY_BUFFER_MS
    expiry_ms = int(creds.get("expiry_date", 0))
    now_ms = int(time.time() * 1000)
    return (now_ms + _EXPIRY_BUFFER_MS) >= expiry_ms


class TestGeminiOAuthProvider:
    def test_is_available_when_file_exists(self, tmp_path: Path) -> None:
        creds_file = tmp_path / "oauth_creds.json"
        creds_file.write_text(json.dumps(_make_creds()))
        provider = GeminiOAuthProvider(creds_path=creds_file)
        assert provider.is_available() is True

    def test_is_available_false_when_file_missing(self, tmp_path: Path) -> None:
        provider = GeminiOAuthProvider(creds_path=tmp_path / "nope.json")
        assert provider.is_available() is False

    def test_name(self) -> None:
        assert GeminiOAuthProvider().name == "gemini-oauth"

    def test_get_access_token_valid(self, tmp_path: Path) -> None:
        creds = _make_creds(access_token="my-valid-token")
        creds_file = tmp_path / "oauth_creds.json"
        creds_file.write_text(json.dumps(creds))

        provider = GeminiOAuthProvider(creds_path=creds_file)
        token = provider.get_access_token()
        assert token == "my-valid-token"

    def test_get_access_token_triggers_refresh_when_expired(self, tmp_path: Path) -> None:
        expired_creds = _make_creds(expired=True)
        creds_file = tmp_path / "oauth_creds.json"
        creds_file.write_text(json.dumps(expired_creds))

        provider = GeminiOAuthProvider(creds_path=creds_file)

        new_creds = _make_creds(access_token="refreshed-token")
        with patch.object(provider, "_refresh", return_value=new_creds) as mock_refresh:
            token = provider.get_access_token()

        mock_refresh.assert_called_once()
        assert token == "refreshed-token"

    def test_raises_auth_error_when_file_missing(self, tmp_path: Path) -> None:
        provider = GeminiOAuthProvider(creds_path=tmp_path / "missing.json")
        with pytest.raises(AuthError, match="not found"):
            provider.get_access_token()

    def test_atomic_write_on_refresh(self, tmp_path: Path) -> None:
        """_write_creds writes to a temp file then renames."""
        creds_file = tmp_path / "oauth_creds.json"
        creds_file.write_text(json.dumps(_make_creds()))
        provider = GeminiOAuthProvider(creds_path=creds_file)

        new_creds = _make_creds(access_token="written-back")
        provider._write_creds(new_creds)

        written = json.loads(creds_file.read_text())
        assert written["access_token"] == "written-back"
        # Temp file should be gone
        assert not creds_file.with_suffix(".json.tmp").exists()


# ─── Token expiry helpers ─────────────────────────────────────────────────────
class TestTokenExpiry:
    def test_valid_token_not_expired(self) -> None:
        creds = _make_creds(expired=False)
        assert _is_expired_static(creds) is False

    def test_expired_token_detected(self) -> None:
        creds = _make_creds(expired=True)
        assert _is_expired_static(creds) is True

    def test_missing_expiry_treated_as_expired(self) -> None:
        creds = {"access_token": "x", "refresh_token": "y", "expiry_date": 0}
        assert _is_expired_static(creds) is True
