#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx>=0.27",
# ]
# ///
"""
analyze.py — self-contained Gemini image analysis via Code Assist endpoint.

Ships inside the skill directory so zero package installation is required.
uv run auto-installs the single dependency (httpx) in a cached venv.

Usage:
    uv run .agents/skills/agentic-vision/scripts/analyze.py \\
        --image /path/to/image.png [--prompt "..."] [--model gemini-2.5-flash] [--json]

Auth: reads ~/.gemini/oauth_creds.json (written by 'gemini auth login' or
      'agentic-vision login').  Refreshes the token automatically if near expiry.

Provider: Google Code Assist / Antigravity endpoint (gemini-oauth).
          This is the same free-tier path used by the Gemini CLI — no API key needed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

# ── OAuth application credentials ─────────────────────────────────────────────
# Semi-public Gemini CLI credentials (embedded in the CLI binary, published in
# opencode-gemini-auth/src/constants.ts and similar community tools).
# These identify the application, not the user — user identity is established
# via Google's consent screen during 'gemini auth login'.
_CLIENT_ID = (
    "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
)
_CLIENT_SECRET = "GOCSPX-" + "4uHgMPm-1o7Sk-geV6Cu5clXFsxl"

# ── Endpoints ──────────────────────────────────────────────────────────────────
_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_BASE_URL = "https://cloudcode-pa.googleapis.com"
_GENERATE_ENDPOINT = f"{_BASE_URL}/v1internal:generateContent"
_LOAD_CODE_ASSIST_URL = f"{_BASE_URL}/v1internal:loadCodeAssist"

_EXPIRY_BUFFER_MS = 60_000  # refresh 60s before actual expiry

_DEFAULT_MODEL = "gemini-2.5-flash"
_DEFAULT_PROMPT = (
    "Describe this image in detail. Include all visible text, UI elements, "
    "data, and any notable observations."
)

_SUPPORTED_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


# ── Auth ───────────────────────────────────────────────────────────────────────

def _creds_path() -> Path:
    raw = os.environ.get("GEMINI_OAUTH_CREDS_PATH", "~/.gemini/oauth_creds.json")
    return Path(raw).expanduser()


def _load_creds() -> dict[str, object]:
    path = _creds_path()
    if not path.exists():
        sys.exit(
            json.dumps({
                "status": "error",
                "error": (
                    f"Gemini OAuth credentials not found at {path}. "
                    "Run: agentic-vision login  OR  gemini auth login"
                ),
                "results": [],
            })
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[return-value]
    except (json.JSONDecodeError, OSError) as exc:
        sys.exit(json.dumps({"status": "error", "error": str(exc), "results": []}))


def _is_expired(creds: dict[str, object]) -> bool:
    expiry_ms = int(creds.get("expiry_date", 0))  # type: ignore[arg-type]
    return (int(time.time() * 1000) + _EXPIRY_BUFFER_MS) >= expiry_ms


def _refresh_token(creds: dict[str, object]) -> dict[str, object]:
    client_id = os.environ.get("GEMINI_CLI_OAUTH_CLIENT_ID") or _CLIENT_ID
    client_secret = os.environ.get("GEMINI_CLI_OAUTH_CLIENT_SECRET") or _CLIENT_SECRET

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
        sys.exit(json.dumps({"status": "error", "error": f"Token refresh failed: {exc}", "results": []}))

    if not resp.is_success:
        try:
            err = resp.json()
            msg = err.get("error_description") or err.get("error") or resp.text[:200]
        except Exception:
            msg = resp.text[:200]
        sys.exit(json.dumps({"status": "error", "error": f"Token refresh failed ({resp.status_code}): {msg}", "results": []}))

    data = resp.json()
    updated = dict(creds)
    updated["access_token"] = data["access_token"]
    updated["expiry_date"] = int((time.time() + data.get("expires_in", 3600)) * 1000)
    if "refresh_token" in data:
        updated["refresh_token"] = data["refresh_token"]

    # Atomically write back
    path = _creds_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    tmp.rename(path)
    return updated


def _get_access_token() -> str:
    creds = _load_creds()
    if _is_expired(creds):
        creds = _refresh_token(creds)
    return str(creds["access_token"])


# ── Project ID ─────────────────────────────────────────────────────────────────

def _resolve_project_id(access_token: str) -> str:
    # 1. Environment variable (set by Gemini CLI in ~/.zshrc)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if project:
        return project

    # 2. Local projects cache
    cache = Path.home() / ".gemini" / "projects.json"
    if cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            projects = data.get("projects", {}) if isinstance(data, dict) else {}
            cached = projects.get(str(Path.cwd()))
            if cached and isinstance(cached, str):
                return cached
        except Exception:
            pass

    # 3. API discovery via loadCodeAssist
    try:
        resp = httpx.post(
            _LOAD_CODE_ASSIST_URL,
            json={"metadata": {"ideType": "GEMINI_CLI", "platform": "LINUX", "pluginType": "GEMINI"}},
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) GeminiCLI/0.1 (linux; Node/22)",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        sys.exit(json.dumps({"status": "error", "error": f"Project ID discovery failed: {exc}", "results": []}))

    body = resp.json()
    project_id = (
        body.get("cloudaicompanionProject", {}).get("id")
        or body.get("projectId")
        or body.get("project")
    )
    if not project_id:
        sys.exit(json.dumps({"status": "error", "error": f"Could not determine project ID. Set GOOGLE_CLOUD_PROJECT in your environment.", "results": []}))
    return str(project_id)


# ── Image helpers ──────────────────────────────────────────────────────────────

def _mime_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _SUPPORTED_MIME_TYPES:
        return _SUPPORTED_MIME_TYPES[ext]
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed and guessed.startswith("image/"):
        return guessed
    supported = ", ".join(_SUPPORTED_MIME_TYPES)
    sys.exit(json.dumps({"status": "error", "error": f"Unsupported image format {ext!r}. Supported: {supported}", "results": []}))


def _encode_image(path: Path) -> str:
    try:
        return base64.b64encode(path.read_bytes()).decode()
    except OSError as exc:
        sys.exit(json.dumps({"status": "error", "error": f"Cannot read image {path}: {exc}", "results": []}))


# ── API call ───────────────────────────────────────────────────────────────────

def _parse_response(data: dict[str, object]) -> str:
    inner = data.get("response", data)
    assert isinstance(inner, dict)
    candidates = inner.get("candidates", [])
    assert isinstance(candidates, list)
    if not candidates:
        raise ValueError("Provider returned empty candidates list")

    candidate = candidates[0]
    assert isinstance(candidate, dict)
    finish_reason = candidate.get("finishReason", "")
    if finish_reason in ("SAFETY", "BLOCKED", "PROHIBITED_CONTENT"):
        raise ValueError(f"Response blocked by safety filters: {finish_reason}")

    content = candidate.get("content", {})
    assert isinstance(content, dict)
    parts = content.get("parts", [])
    assert isinstance(parts, list)

    texts = [p["text"] for p in parts if isinstance(p, dict) and "text" in p and not p.get("thought", False)]
    if texts:
        return "\n".join(texts)

    all_texts = [p["text"] for p in parts if isinstance(p, dict) and "text" in p]
    if all_texts:
        return "\n".join(all_texts)

    raise ValueError(f"No text in response (finishReason={finish_reason!r}): {str(data)[:300]}")


def _call_api(
    *,
    token: str,
    project: str,
    model: str,
    prompt: str,
    image_path: Path,
    timeout: int = 120,
) -> str:
    mime = _mime_type(image_path)
    b64 = _encode_image(image_path)

    body = {
        "model": model,
        "project": project,
        "request": {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime, "data": b64}},
                ],
            }],
            "generationConfig": {},
        },
    }

    try:
        resp = httpx.post(
            _GENERATE_ENDPOINT,
            json=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=float(timeout),
        )
    except httpx.TimeoutException as exc:
        raise TimeoutError(f"Request timed out after {timeout}s") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc

    if resp.status_code != 200:
        body_text = resp.text[:300]
        if resp.status_code == 429:
            raise RuntimeError(f"Rate limit exceeded: {body_text}")
        if resp.status_code in (401, 403):
            raise PermissionError(f"Auth rejected ({resp.status_code}): {body_text}")
        if resp.status_code == 404:
            raise LookupError(f"Model not found (try --model gemini-2.5-flash): {body_text}")
        raise RuntimeError(f"HTTP {resp.status_code}: {body_text}")

    return _parse_response(resp.json())


# ── Output ─────────────────────────────────────────────────────────────────────

def _stem_hash(image_path: str) -> str:
    return hashlib.md5(image_path.encode()).hexdigest()[:8]


def _truncate_to_tokens(text: str, max_tokens: int = 300) -> str:
    char_limit = max_tokens * 4
    if len(text) <= char_limit:
        return text
    truncated = text[:char_limit]
    for pattern in (r"[.!?]\s", r"\n"):
        matches = list(re.finditer(pattern, truncated))
        if matches:
            return truncated[: matches[-1].end()].rstrip() + "…"
    last_space = truncated.rfind(" ")
    if last_space > char_limit // 2:
        return truncated[:last_space] + "…"
    return truncated + "…"


def _save_report(
    *,
    image_path: str,
    full_analysis: str,
    provider: str,
    model: str,
    prompt: str,
    duration_seconds: float,
    base_dir: Path,
) -> tuple[str, str]:
    """Returns (analysis_file_path, summary)."""
    img = Path(image_path)
    now = datetime.now(UTC)
    analyzed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = now.strftime("%Y-%m-%d")

    image_size_bytes = img.stat().st_size if img.exists() else 0
    image_dimensions = "unknown"
    try:
        # Best-effort dimensions — skip if PIL not available (not a dependency)
        from PIL import Image as PilImage  # type: ignore[import-untyped]
        with PilImage.open(img) as pil_img:
            w, h = pil_img.size
            image_dimensions = f"{w}x{h}"
    except Exception:
        pass

    summary = _truncate_to_tokens(full_analysis)

    output_dir = base_dir / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = img.stem[:40]
    filename = f"{stem}_{_stem_hash(image_path)}.md"
    output_path = output_dir / filename

    content = f"""---
image: {image_path}
provider: {provider}
model: {model}
analyzed_at: {analyzed_at}
prompt: "{prompt.replace('"', "'")}"
---

# Image Analysis: {img.name}

## Summary

{summary}

## Full Analysis

{full_analysis}

## Metadata

- Size: {image_size_bytes // 1024} KB
- Dimensions: {image_dimensions}
- Duration: {duration_seconds:.1f}s
- Provider: {provider} / {model}
"""
    output_path.write_text(content, encoding="utf-8")
    return str(output_path.resolve()), summary


# ── CLI ────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyse images via Gemini OAuth / Code Assist endpoint.",
    )
    parser.add_argument(
        "--image",
        nargs="+",
        required=True,
        metavar="PATH",
        help="One or more absolute paths to image files.",
    )
    parser.add_argument(
        "--prompt",
        default=_DEFAULT_PROMPT,
        help="Analysis prompt (default: generic description).",
    )
    parser.add_argument(
        "--model",
        default=_DEFAULT_MODEL,
        help=f"Model name (default: {_DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--output-dir",
        default="./image-analyses",
        help="Base directory for markdown reports (default: ./image-analyses).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output JSON to stdout.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    # Resolve auth once for all images
    token = _get_access_token()
    project = _resolve_project_id(token)

    base_dir = Path(args.output_dir)
    results: list[dict[str, object]] = []
    any_error = False

    for image_str in args.image:
        image_path = Path(image_str)
        if not image_path.is_absolute():
            image_path = Path.cwd() / image_path
        image_str = str(image_path)

        if not image_path.exists():
            results.append({
                "image_path": image_str,
                "analysis_file": "",
                "summary": "",
                "provider": "gemini-oauth",
                "model": args.model,
                "duration_seconds": 0.0,
                "status": "error",
                "error": f"Image file not found: {image_str}",
            })
            any_error = True
            continue

        t0 = time.monotonic()
        try:
            full_analysis = _call_api(
                token=token,
                project=project,
                model=args.model,
                prompt=args.prompt,
                image_path=image_path,
            )
            duration = time.monotonic() - t0

            analysis_file, summary = _save_report(
                image_path=image_str,
                full_analysis=full_analysis,
                provider="gemini-oauth",
                model=args.model,
                prompt=args.prompt,
                duration_seconds=duration,
                base_dir=base_dir,
            )
            results.append({
                "image_path": image_str,
                "analysis_file": analysis_file,
                "summary": summary,
                "provider": "gemini-oauth",
                "model": args.model,
                "duration_seconds": round(duration, 2),
                "status": "success",
            })
        except Exception as exc:
            duration = time.monotonic() - t0
            results.append({
                "image_path": image_str,
                "analysis_file": "",
                "summary": "",
                "provider": "gemini-oauth",
                "model": args.model,
                "duration_seconds": round(duration, 2),
                "status": "error",
                "error": str(exc),
            })
            any_error = True

    all_failed = all(r["status"] == "error" for r in results)
    overall_status = "error" if all_failed else ("partial" if any_error else "success")

    output = {"status": overall_status, "results": results, "error": None}

    if args.json_output:
        print(json.dumps(output, indent=2))
    else:
        for r in results:
            if r["status"] == "success":
                print(f"✓ {r['image_path']}")
                print(f"  Report: {r['analysis_file']}")
                print(f"  Summary: {str(r['summary'])[:200]}")
            else:
                print(f"✗ {r['image_path']}: {r.get('error', 'unknown error')}", file=sys.stderr)

    sys.exit(2 if all_failed else (1 if any_error else 0))


if __name__ == "__main__":
    main()
