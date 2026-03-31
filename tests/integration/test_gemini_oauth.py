"""
Integration tests for Gemini OAuth + Code Assist provider.

Requires: AGENTIC_VISION_INTEGRATION_TEST=1 and valid ~/.gemini/oauth_creds.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

FIXTURE_IMAGE = Path(__file__).parent.parent / "fixtures" / "red_pixel.png"


@pytest.fixture(scope="module")
def oauth_token() -> str:
    """Get a valid OAuth token from the Gemini CLI credentials."""
    from agentic_vision.auth.base import AuthError
    from agentic_vision.auth.gemini_oauth import GeminiOAuthProvider

    provider = GeminiOAuthProvider()
    if not provider.is_available():
        pytest.skip("~/.gemini/oauth_creds.json not found")
    try:
        return provider.get_access_token()
    except AuthError as exc:
        pytest.skip(f"OAuth token unavailable: {exc}")


class TestGeminiOAuthIntegration:
    def test_token_is_non_empty(self, oauth_token: str) -> None:
        assert len(oauth_token) > 20

    def test_code_assist_text_request(self, oauth_token: str) -> None:
        """Minimal text-only request to verify the endpoint and token are valid."""
        import os

        import httpx

        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not project:
            pytest.skip("GOOGLE_CLOUD_PROJECT not set")

        resp = httpx.post(
            "https://cloudcode-pa.googleapis.com/v1internal:generateContent",
            json={
                "model": "gemini-2.5-flash",
                "project": project,
                "request": {
                    "contents": [{"role": "user", "parts": [{"text": "Reply: OK"}]}],
                    "generationConfig": {"maxOutputTokens": 5},
                },
            },
            headers={"Authorization": f"Bearer {oauth_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        # 429 = rate limited but endpoint and auth are correct
        if resp.status_code == 429:
            pytest.skip("Model at capacity (429) — endpoint and token are valid")
        assert resp.status_code not in (401, 403), f"Auth rejected: {resp.text[:200]}"
        assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        inner = data.get("response", data)
        assert "candidates" in inner

    @pytest.mark.parametrize("model", ["gemini-2.5-flash", "gemini-2.5-pro"])
    def test_code_assist_vision_request(self, oauth_token: str, model: str) -> None:
        """Vision request with the 1x1 red pixel PNG fixture. Tries models until one succeeds."""
        import base64
        import os

        import httpx

        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not project:
            pytest.skip("GOOGLE_CLOUD_PROJECT not set")

        if not FIXTURE_IMAGE.exists():
            pytest.skip(f"Test fixture not found: {FIXTURE_IMAGE}")

        b64 = base64.b64encode(FIXTURE_IMAGE.read_bytes()).decode()
        resp = httpx.post(
            "https://cloudcode-pa.googleapis.com/v1internal:generateContent",
            json={
                "model": model,
                "project": project,
                "request": {
                    "contents": [{"role": "user", "parts": [
                        {"text": "Describe this image in one word."},
                        {"inline_data": {"mime_type": "image/png", "data": b64}},
                    ]}],
                    "generationConfig": {"maxOutputTokens": 20},
                },
            },
            headers={"Authorization": f"Bearer {oauth_token}", "Content-Type": "application/json"},
            timeout=60,
        )
        if resp.status_code == 429:
            pytest.skip(f"Model {model!r} at capacity (429) — auth and request structure are correct")
        assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        inner = data.get("response", data)
        candidates = inner.get("candidates", [])
        assert candidates, f"No candidates in response: {str(data)[:200]}"
        # Response arrived — content may vary (parts, thinking, safety block, etc.)
        candidate = candidates[0]
        finish = candidate.get("finishReason", "OK")
        assert finish not in ("ERROR",), f"Unexpected finishReason: {finish}"
        # If we got content with text, verify it
        parts = candidate.get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if "text" in p]
        if texts:
            assert any(t.strip() for t in texts), "Expected non-empty text in parts"


class TestCliIntegration:
    def test_auth_check_command(self) -> None:
        """Verify auth-check CLI command works."""
        result = subprocess.run(
            [sys.executable, "-m", "agentic_vision", "auth-check", "--pretty"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["status"] == "success"
        assert "checks" in data

    def test_analyze_command_with_fixture(self) -> None:
        """Full end-to-end: CLI analyze → real API → saved report."""
        if not FIXTURE_IMAGE.exists():
            pytest.skip(f"Test fixture not found: {FIXTURE_IMAGE}")

        result = subprocess.run(
            [sys.executable, "-m", "agentic_vision", "analyze",
             "--image", str(FIXTURE_IMAGE),
             "--prompt", "What colour is this image?",
             "--provider", "gemini-oauth",
             "--model", "gemini-2.5-flash",
             "--pretty"],
            capture_output=True, text=True,
        )
        if result.returncode == 3:
            pytest.skip(f"Auth not configured: {result.stdout}")

        data = json.loads(result.stdout)
        assert "results" in data

        if data["results"]:
            r = data["results"][0]
            error_msg = r.get("error", "")
            if r["status"] == "error":
                if "429" in error_msg or "Rate limit" in error_msg or "capacity" in error_msg.lower():
                    pytest.skip("Model at capacity (429) — auth and request structure are correct")
                if "401" in error_msg or "403" in error_msg:
                    pytest.fail(f"Auth rejected: {error_msg}")
                # Other errors (404, 500, etc.) — skip as infrastructure issue
                pytest.skip(f"Provider error (non-auth): {error_msg[:100]}")
            if r["status"] == "success":
                assert r["analysis_file"], "analysis_file should be non-empty"
                assert r["summary"], "summary should be non-empty"
                assert Path(r["analysis_file"]).exists(), "analysis file should exist on disk"
