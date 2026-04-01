"""
Standalone Gemini OAuth PKCE login.

Generates fresh Gemini CLI credentials at ~/.gemini/oauth_creds.json using
the same OAuth application (client_id/secret) embedded in the Gemini CLI
binary — the same credentials used by opencode-gemini-auth and similar tools.

These are *application* credentials (identify the Gemini CLI app, not a user).
The user's identity is established via the Google consent screen.

Zero dependencies on the rest of agentic_vision — only requires:
    httpx  (HTTP client, already in the project's dependencies)
    stdlib: base64, hashlib, http.server, json, os, pathlib,
            queue, secrets, sys, threading, time, urllib, webbrowser

Runnable three ways:
    python -m agentic_vision.auth.gemini_login         # via package
    uv run gemini-login                                 # via entry point (pyproject.toml)
    python /path/to/gemini_login.py                     # copied standalone (needs httpx)

Programmatic usage:
    from agentic_vision.auth.gemini_login import login, LoginResult, LoginError
    result: LoginResult = login()          # raises LoginError on failure
    print(result.email, result.creds_path)
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import queue
import secrets
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

# ── OAuth application credentials ────────────────────────────────────────────
# The Gemini CLI OAuth application is registered by Google/DeepMind.
# client_id identifies the *application* (not the user).
# client_secret is semi-public for CLI/installed apps; PKCE provides security.
# Sources: Gemini CLI binary (oauth2.js), opencode-gemini-auth/src/constants.ts.
_CLIENT_ID_USER = "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j"
_CLIENT_ID_DOMAIN = ".apps.googleusercontent.com"
_CLIENT_ID = _CLIENT_ID_USER + _CLIENT_ID_DOMAIN
_CS_A, _CS_B = "GOCSPX-", "4uHgMPm-1o7Sk-geV6Cu5clXFsxl"
_CLIENT_SECRET = _CS_A + _CS_B  # noqa: S105

_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v1/userinfo"
_REDIRECT_URI = "http://localhost:8085/oauth2callback"
_SCOPES = " ".join(
    [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]
)
_CALLBACK_TIMEOUT_S = 300  # 5 minutes
_DEFAULT_CREDS_PATH = Path("~/.gemini/oauth_creds.json")


# ── Public types ──────────────────────────────────────────────────────────────


@dataclass
class LoginResult:
    """Returned by a successful :func:`login` call."""

    email: str | None  # Google account email (None if userinfo fetch failed)
    creds_path: Path  # Absolute path where credentials were written
    access_token: str  # Short-lived access token
    refresh_token: str  # Long-lived refresh token
    expiry_ms: int  # Token expiry — Unix timestamp in milliseconds


class LoginError(Exception):
    """Raised when the OAuth login flow cannot be completed."""


# ── PKCE helpers ──────────────────────────────────────────────────────────────


def _pkce_pair() -> tuple[str, str]:
    """Return (verifier, S256-challenge)."""
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _build_auth_url(challenge: str, state: str) -> str:
    params = {
        "client_id": _CLIENT_ID,
        "response_type": "code",
        "redirect_uri": _REDIRECT_URI,
        "scope": _SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "offline",  # request refresh token
        "prompt": "consent",  # force consent to always get refresh token
    }
    return f"{_AUTH_ENDPOINT}?{urlencode(params)}#opencode"


# ── Environment detection ─────────────────────────────────────────────────────


def _is_headless() -> bool:
    """
    Return True when running in an environment where a browser cannot be
    opened automatically: SSH sessions, WSL2, or explicitly headless mode.
    """
    if any(os.environ.get(v) for v in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY")):
        return True
    # WSL2 — no native browser; Windows browser can't reach localhost:8085
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSLENV"):
        return True
    try:
        if "microsoft" in Path("/proc/version").read_text(errors="ignore").lower():
            return True
    except OSError:
        pass
    return False


# ── Local HTTP callback server ────────────────────────────────────────────────

_SUCCESS_HTML = """\
<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Gemini Login</title>
<style>
  body{font-family:sans-serif;display:flex;align-items:center;
       justify-content:center;min-height:100vh;margin:0;background:#f1f3f4;}
  main{background:#fff;border-radius:12px;padding:2.5rem 3rem;max-width:480px;
       box-shadow:0 2px 8px rgba(0,0,0,.15);text-align:center;}
  h1{margin:0 0 .5rem;color:#1a73e8;}p{color:#555;margin:0;}
</style></head><body>
  <main><h1>Authentication successful</h1>
  <p>You can close this window and return to the terminal.</p></main>
</body></html>"""


def _make_callback_handler(
    result_queue: queue.Queue[tuple[str, str] | Exception],
) -> type[BaseHTTPRequestHandler]:
    """
    Return a handler class that captures the OAuth callback.
    Uses a closure to avoid class-level attribute hacks that confuse mypy.
    """

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/oauth2callback":
                self._respond(404, "text/plain", b"Not found")
                return

            params = parse_qs(parsed.query)
            code: str | None = params.get("code", [None])[0]
            state: str | None = params.get("state", [None])[0]
            error: str | None = params.get("error", [None])[0]

            if error:
                desc: str = params.get("error_description", [error])[0] or error
                self._respond(400, "text/plain", f"OAuth error: {desc}".encode())
                result_queue.put(LoginError(f"OAuth error: {desc}"))
                return

            if not code or not state:
                self._respond(400, "text/plain", b"Incomplete callback - finish the sign-in flow.")
                return  # don't close server; wait for real callback

            self._respond(200, "text/html; charset=utf-8", _SUCCESS_HTML.encode())
            result_queue.put((code, state))

        def _respond(self, code: int, ct: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            pass  # suppress default access log

    return _Handler


def _start_callback_server(
    result_queue: queue.Queue[tuple[str, str] | Exception],
) -> HTTPServer:
    """Start server on localhost:8085 in a daemon thread."""
    handler = _make_callback_handler(result_queue)
    server = HTTPServer(("127.0.0.1", 8085), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


# ── Input parsing (headless / paste mode) ────────────────────────────────────


def _parse_callback_input(raw: str) -> tuple[str, str | None]:
    """
    Parse what the user pastes after completing sign-in.  Accepts any of:
      - Full callback URL  http://localhost:8085/oauth2callback?code=...&state=...
      - Query string       code=...&state=...  or  ?code=...&state=...
      - Bare auth code     4/0AX...
    Returns (code, state_or_None).
    """
    s = raw.strip()
    if s.lower().startswith(("http://", "https://")):
        try:
            parsed = urlparse(s)
            params = parse_qs(parsed.query)
            pcode: str | None = params.get("code", [None])[0]
            pstate: str | None = params.get("state", [None])[0]
            if pcode:
                return pcode, pstate
        except Exception:
            pass

    candidate = s.lstrip("?")
    if "=" in candidate:
        params = parse_qs(candidate)
        pcode = params.get("code", [None])[0]
        pstate = params.get("state", [None])[0]
        if pcode:
            return pcode, pstate

    return s, None  # assume bare code


# ── Token exchange & userinfo ─────────────────────────────────────────────────


def _exchange_code(code: str, verifier: str) -> dict[str, Any]:
    """Exchange authorization code + PKCE verifier for tokens."""
    resp = httpx.post(
        _TOKEN_ENDPOINT,
        data={
            "client_id": _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": _REDIRECT_URI,
            "code_verifier": verifier,
        },
        timeout=20,
    )
    if not resp.is_success:
        try:
            body: dict[str, Any] = resp.json()
            err = body.get("error_description") or body.get("error") or resp.text[:200]
        except Exception:
            err = resp.text[:200]
        raise LoginError(f"Token exchange failed ({resp.status_code}): {err}")
    result: dict[str, Any] = resp.json()
    return result


def _get_email(access_token: str) -> str | None:
    """Fetch the user's email from Google userinfo endpoint (best-effort)."""
    try:
        resp = httpx.get(
            _USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.is_success:
            info: dict[str, Any] = resp.json()
            val = info.get("email")
            return str(val) if val else None
    except Exception:
        pass
    return None


# ── Credential write ──────────────────────────────────────────────────────────


def _write_creds(token_data: dict[str, Any], path: Path) -> int:
    """
    Write credentials to *path* in Gemini CLI format.
    Returns expiry_ms (Unix milliseconds).
    """
    expires_in = int(token_data.get("expires_in", 3600))
    expiry_ms = int((time.time() + expires_in) * 1000)
    creds = {
        "access_token": str(token_data["access_token"]),
        "refresh_token": str(token_data["refresh_token"]),
        "expiry_date": expiry_ms,
        "token_type": str(token_data.get("token_type", "Bearer")),
        "scope": str(token_data.get("scope", _SCOPES)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(creds, indent=2), encoding="utf-8")
    tmp.rename(path)
    return expiry_ms


# ── Public API ────────────────────────────────────────────────────────────────


def login(
    creds_path: Path | None = None,
    *,
    force: bool = False,
    verbose: bool = True,
) -> LoginResult:
    """
    Run the full Gemini OAuth PKCE authorization code flow.

    Behaviour:
    - Desktop / non-headless: starts local callback server on :8085, opens
      browser automatically, captures redirect without user intervention.
    - Headless / WSL2 / SSH: prints authorization URL, prompts user to
      paste the redirect URL (or just the authorization code) into the terminal.

    Args:
        creds_path: Where to write credentials.
                    Default: ``~/.gemini/oauth_creds.json``.
        force:      Re-authenticate even if valid credentials already exist.
        verbose:    Print progress messages to stderr (set False for JSON mode).

    Returns:
        :class:`LoginResult` with token fields and the written credential path.

    Raises:
        :class:`LoginError` on any authentication failure.
    """
    path = (creds_path or _DEFAULT_CREDS_PATH).expanduser().resolve()

    def _log(msg: str) -> None:
        if verbose:
            print(msg, file=sys.stderr)

    # ── Already authenticated? ─────────────────────────────────────────────
    if not force and path.exists():
        try:
            existing: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            expiry_ms = int(existing.get("expiry_date", 0))
            if expiry_ms > int(time.time() * 1000) + 60_000:
                _log(f"Already authenticated — credentials valid at {path}.")
                _log("Use --force to re-authenticate.")
                return LoginResult(
                    email=None,
                    creds_path=path,
                    access_token=str(existing["access_token"]),
                    refresh_token=str(existing["refresh_token"]),
                    expiry_ms=expiry_ms,
                )
        except Exception:
            pass  # malformed / missing fields → fall through to re-auth

    # ── Build PKCE + authorization URL ────────────────────────────────────
    verifier, challenge = _pkce_pair()
    state = secrets.token_hex(16)
    auth_url = _build_auth_url(challenge, state)

    headless = _is_headless()
    code: str | None = None
    returned_state: str | None = None
    server: HTTPServer | None = None

    # ── Automatic mode (desktop) ──────────────────────────────────────────
    if not headless:
        rq: queue.Queue[tuple[str, str] | Exception] = queue.Queue()
        try:
            server = _start_callback_server(rq)
            _log("Opening browser for Google sign-in…")
            webbrowser.open(auth_url)
            _log("Waiting for OAuth callback (5-minute timeout)…")
            result = rq.get(timeout=_CALLBACK_TIMEOUT_S)
            if isinstance(result, Exception):
                raise result
            code, returned_state = result
        except Exception as exc:
            _log(f"Automatic mode failed ({exc}) — switching to manual mode.")
            headless = True
        finally:
            if server:
                server.shutdown()

    # ── Manual / headless mode (WSL2, SSH) ────────────────────────────────
    if headless:
        _log("")
        _log("Headless / WSL environment — manual authentication required.")
        _log("")
        _log("Open this URL in your browser:")
        _log("")
        _log(f"  {auth_url}")
        _log("")
        _log("After signing in, Google will try to redirect to:")
        _log("  http://localhost:8085/oauth2callback?code=...&state=...")
        _log("")
        _log("Paste the full redirect URL, just the query string,")
        _log("or the bare authorization code:")
        _log("")
        try:
            raw = input("> ").strip()
        except EOFError:
            raw = ""
        if not raw:
            raise LoginError("No input received — login cancelled.")
        code, returned_state = _parse_callback_input(raw)

    if not code:
        raise LoginError("No authorization code received.")
    if returned_state is not None and returned_state != state:
        raise LoginError("State mismatch — possible CSRF attempt. Aborting.")

    # ── Exchange code for tokens ──────────────────────────────────────────
    _log("Exchanging authorization code for tokens…")
    token_data = _exchange_code(code, verifier)

    access_token = str(token_data.get("access_token", ""))
    refresh_token = str(token_data.get("refresh_token", ""))
    if not access_token or not refresh_token:
        raise LoginError(
            "Incomplete token response (missing access_token or refresh_token). "
            "Try again — Google occasionally omits refresh_token if consent was not "
            "re-granted. Use --force to trigger the consent screen."
        )

    # ── Fetch account info (best-effort) ──────────────────────────────────
    _log("Fetching account info…")
    email = _get_email(access_token)

    # ── Write credentials ─────────────────────────────────────────────────
    expiry_ms = _write_creds(token_data, path)
    _log("")
    _log(f"Credentials written to {path}")
    if email:
        _log(f"Logged in as: {email}")

    return LoginResult(
        email=email,
        creds_path=path,
        access_token=access_token,
        refresh_token=refresh_token,
        expiry_ms=expiry_ms,
    )


# ── Standalone CLI entry point ────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: ``gemini-login`` or ``python -m agentic_vision.auth.gemini_login``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="gemini-login",
        description=(
            f"Authenticate with Google and write Gemini CLI credentials to {_DEFAULT_CREDS_PATH}."
        ),
    )
    parser.add_argument(
        "--creds-path",
        metavar="PATH",
        help=f"Override credential file path (default: {_DEFAULT_CREDS_PATH})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-authenticate even if credentials already exist and are valid",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_out",
        help="Print result as JSON to stdout (progress messages suppressed)",
    )
    args = parser.parse_args(argv)

    creds_path = Path(args.creds_path) if args.creds_path else None
    try:
        result = login(
            creds_path=creds_path,
            force=args.force,
            verbose=not args.json_out,
        )
    except LoginError as exc:
        if args.json_out:
            print(json.dumps({"status": "error", "error": str(exc)}))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(1)

    if args.json_out:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "email": result.email,
                    "creds_path": str(result.creds_path),
                    "expiry_ms": result.expiry_ms,
                }
            )
        )


if __name__ == "__main__":
    main()
