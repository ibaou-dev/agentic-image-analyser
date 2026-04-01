#!/usr/bin/env python3
"""
verify_auth.py — Phase 0 endpoint verification.

Validates that the Gemini CLI OAuth token is valid and that the
Code Assist and/or Gemini API endpoints respond correctly.

Intentionally minimal: stdlib + httpx only. No Pydantic, no engine abstractions.

Usage:
    uv run python scripts/verify_auth.py
    uv run python scripts/verify_auth.py --refresh        # force token refresh
    uv run python scripts/verify_auth.py --vision PATH    # test with a real image
    uv run python scripts/verify_auth.py --api-key        # test GEMINI_API_KEY instead
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# httpx is our only non-stdlib dep — installed via uv before running
try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: uv sync --dev", file=sys.stderr)
    sys.exit(1)

# ─── Colours ──────────────────────────────────────────────────────────────────
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def err(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {BOLD}·{RESET} {msg}")


# ─── OAuth helpers ─────────────────────────────────────────────────────────────
OAUTH_CREDS_PATH = Path(
    os.environ.get("GEMINI_OAUTH_CREDS_PATH", "~/.gemini/oauth_creds.json")
).expanduser()

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
EXPIRY_BUFFER_MS = 60_000  # refresh 60s before actual expiry


def load_creds() -> dict:
    if not OAUTH_CREDS_PATH.exists():
        raise FileNotFoundError(f"OAuth creds not found at {OAUTH_CREDS_PATH}")
    with OAUTH_CREDS_PATH.open() as f:
        return json.load(f)


def is_expired(creds: dict) -> bool:
    expiry_ms = creds.get("expiry_date", 0)
    now_ms = int(time.time() * 1000)
    return (now_ms + EXPIRY_BUFFER_MS) >= expiry_ms


def seconds_until_expiry(creds: dict) -> int:
    expiry_ms = creds.get("expiry_date", 0)
    now_ms = int(time.time() * 1000)
    return max(0, (expiry_ms - now_ms) // 1000)


def extract_client_credentials() -> tuple[str, str] | None:
    """Try to extract client_id/secret from the installed Gemini CLI package."""
    # Env override (fastest path)
    client_id = os.environ.get("GEMINI_CLI_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GEMINI_CLI_OAUTH_CLIENT_SECRET")
    if client_id and client_secret:
        return client_id, client_secret

    # Walk from gemini binary to find oauth2.js
    import re
    import shutil

    gemini_bin = shutil.which("gemini")
    if not gemini_bin:
        return None
    # Typical path: .../bin/gemini → .../node_modules/@google/gemini-cli-core/dist/...
    search_root = Path(gemini_bin).resolve().parent.parent
    for oauth_js in search_root.rglob("oauth2.js"):
        text = oauth_js.read_text(errors="ignore")
        ids = re.findall(r"(\d+-[a-z0-9]+\.apps\.googleusercontent\.com)", text)
        secrets = re.findall(r"(GOCSPX-[A-Za-z0-9_-]+)", text)
        if ids and secrets:
            return ids[0], secrets[0]
    return None


def refresh_token(creds: dict) -> dict:
    """Refresh the access token using the refresh_token."""
    pair = extract_client_credentials()
    if not pair:
        raise RuntimeError(
            "Cannot find Gemini CLI OAuth client credentials.\n"
            "Set GEMINI_CLI_OAUTH_CLIENT_ID and GEMINI_CLI_OAUTH_CLIENT_SECRET in your .env"
        )
    client_id, client_secret = pair

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": creds["refresh_token"],
        "client_id": client_id,
        "client_secret": client_secret,
    }
    response = httpx.post(TOKEN_ENDPOINT, data=payload, timeout=15)
    if response.status_code != 200:
        raise RuntimeError(f"Token refresh failed {response.status_code}: {response.text[:200]}")

    data = response.json()
    creds = creds.copy()
    creds["access_token"] = data["access_token"]
    creds["expiry_date"] = int((time.time() + data.get("expires_in", 3600)) * 1000)
    if "refresh_token" in data:
        creds["refresh_token"] = data["refresh_token"]

    # Atomic write back
    tmp = OAUTH_CREDS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(creds, indent=2))
    tmp.rename(OAUTH_CREDS_PATH)
    return creds


# ─── API test helpers ──────────────────────────────────────────────────────────
CODE_ASSIST_BASE = "https://cloudcode-pa.googleapis.com"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com"


def test_code_assist_text(token: str, project: str) -> str:
    """Send a minimal text-only request to the Code Assist endpoint."""
    url = f"{CODE_ASSIST_BASE}/v1internal:generateContent"
    body = {
        "model": "gemini-2.5-flash",
        "project": project,
        "request": {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": "Reply with exactly: OK"}],
                }
            ],
            "generationConfig": {"maxOutputTokens": 10},
        },
    }
    resp = httpx.post(
        url,
        json=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    # Code Assist wraps response in {"response": {...}} envelope
    if "response" in data:
        data = data["response"]
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        return str(data)[:200]


def test_code_assist_vision(token: str, project: str, image_path: str) -> str:
    """Send a vision request with a real local image."""
    img = Path(image_path)
    if not img.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    mime = "image/png" if img.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(img.read_bytes()).decode()

    url = f"{CODE_ASSIST_BASE}/v1internal:generateContent"
    body = {
        "model": "gemini-2.5-flash",
        "project": project,
        "request": {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": "Describe this image in one sentence."},
                        {"inline_data": {"mime_type": mime, "data": b64}},
                    ],
                }
            ],
            "generationConfig": {"maxOutputTokens": 100},
        },
    }
    resp = httpx.post(
        url,
        json=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if "response" in data:
        data = data["response"]
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        return str(data)[:300]


def test_gemini_api_key_text(api_key: str) -> str:
    """Test GEMINI_API_KEY with a minimal text request via the generativeai REST API."""
    url = f"{GEMINI_API_BASE}/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": "Reply with exactly: OK"}]}],
        "generationConfig": {"maxOutputTokens": 10},
    }
    resp = httpx.post(url, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        return str(data)[:200]


# ─── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Verify agentic-vision auth and endpoints")
    parser.add_argument("--refresh", action="store_true", help="Force token refresh before testing")
    parser.add_argument(
        "--vision", metavar="PATH", help="Also test a vision request with this image"
    )
    parser.add_argument(
        "--api-key", action="store_true", help="Test GEMINI_API_KEY instead of OAuth"
    )
    args = parser.parse_args()

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    print(f"\n{BOLD}═══ agentic-vision auth verification ══════════════════════{RESET}")
    print(f"  Time:    {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"  Project: {project or '(not set)'}")
    print()

    failures = 0

    # ── API key path ──────────────────────────────────────────────────────────
    if args.api_key:
        print(f"{BOLD}[1] GEMINI_API_KEY path{RESET}")
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            err("GEMINI_API_KEY not set")
            failures += 1
        else:
            ok(f"API key found: {api_key[:8]}…")
            try:
                reply = test_gemini_api_key_text(api_key)
                ok(f"Text request succeeded → {reply!r}")
            except Exception as e:
                err(f"Text request failed: {e}")
                failures += 1
        print()
        return failures

    # ── OAuth path ────────────────────────────────────────────────────────────
    print(f"{BOLD}[1] OAuth credentials file{RESET}")
    try:
        creds = load_creds()
        ok(f"Found: {OAUTH_CREDS_PATH}")
        ok(f"Fields: {', '.join(creds.keys())}")
    except FileNotFoundError as e:
        err(str(e))
        err("Run: gemini auth login")
        return 1

    # ── Token expiry ──────────────────────────────────────────────────────────
    print(f"\n{BOLD}[2] Token expiry{RESET}")
    expired = is_expired(creds)
    ttl = seconds_until_expiry(creds)

    if expired or args.refresh:
        if expired:
            warn(f"Token expired (TTL: {ttl}s). Attempting refresh…")
        else:
            info("Forcing refresh as requested…")
        try:
            creds = refresh_token(creds)
            ok(f"Token refreshed. New TTL: {seconds_until_expiry(creds)}s")
        except Exception as e:
            err(f"Token refresh failed: {e}")
            failures += 1
    else:
        ok(f"Token valid. Expires in {ttl}s ({ttl // 60}m {ttl % 60}s)")

    # ── Project ID ────────────────────────────────────────────────────────────
    print(f"\n{BOLD}[3] Google Cloud project{RESET}")
    if not project:
        err("GOOGLE_CLOUD_PROJECT not set. Set it in .env or your shell.")
        failures += 1
    else:
        ok(f"GOOGLE_CLOUD_PROJECT={project}")

    # ── Text request to Code Assist ───────────────────────────────────────────
    print(f"\n{BOLD}[4] Code Assist endpoint — text request{RESET}")
    if failures > 0:
        warn("Skipping (fix auth failures above first)")
    else:
        info(f"POST {CODE_ASSIST_BASE}/v1internal:generateContent")
        info("Model: gemini-2.5-flash (text only, minimal)")
        try:
            reply = test_code_assist_text(creds["access_token"], project)
            ok(f"Response: {reply!r}")
        except httpx.HTTPStatusError as e:
            err(f"HTTP {e.response.status_code}: {e.response.text[:300]}")
            failures += 1
        except Exception as e:
            err(f"Request failed: {e}")
            failures += 1

    # ── Vision request (optional) ─────────────────────────────────────────────
    if args.vision:
        print(f"\n{BOLD}[5] Code Assist endpoint — vision request{RESET}")
        info(f"Image: {args.vision}")
        if failures > 0:
            warn("Skipping (fix failures above first)")
        else:
            try:
                reply = test_code_assist_vision(creds["access_token"], project, args.vision)
                ok(f"Vision response: {reply}")
            except httpx.HTTPStatusError as e:
                err(f"HTTP {e.response.status_code}: {e.response.text[:300]}")
                failures += 1
            except Exception as e:
                err(f"Vision request failed: {e}")
                failures += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═' * 55}{RESET}")
    if failures == 0:
        print(f"  {GREEN}{BOLD}All checks passed.{RESET} Auth is working correctly.")
        print("  You can proceed to Phase 1 implementation.\n")
    else:
        print(
            f"  {RED}{BOLD}{failures} check(s) failed.{RESET} Fix the issues above before building the engine.\n"
        )

    return failures


if __name__ == "__main__":
    sys.exit(main())
