"""
Google Cloud project ID discovery for the Code Assist / Antigravity endpoint.

Resolution order:
  1. GOOGLE_CLOUD_PROJECT environment variable (most reliable, usually set by Gemini CLI)
  2. ~/.gemini/projects.json cache keyed by CWD
  3. POST /v1internal:loadCodeAssist to auto-provision and discover a managed project
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from agentic_vision.auth.base import AuthError

_PROJECTS_CACHE = Path.home() / ".gemini" / "projects.json"
_LOAD_CODE_ASSIST_URL = (
    "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"
)
_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
    "GeminiCLI/0.1 (linux; Node/22)"
)


def _load_projects_cache() -> dict[str, Any]:
    if _PROJECTS_CACHE.exists():
        try:
            with _PROJECTS_CACHE.open() as f:
                data = json.load(f)
            return data.get("projects", {}) if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def resolve_project_id(access_token: str | None = None) -> str:
    """
    Return the Google Cloud project ID for the Code Assist endpoint.

    Args:
        access_token: OAuth Bearer token. Required only if auto-discovery
                      via the API is needed (steps 1 and 2 don't need it).

    Returns:
        Project ID string (e.g. "geminicli-466113").

    Raises:
        AuthError: if no project ID can be determined.
    """
    # 1. Environment variable (fastest, set by Gemini CLI in ~/.zshrc)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if project:
        return project

    # 2. Local projects cache
    cwd = str(Path.cwd())
    projects = _load_projects_cache()
    if projects.get(cwd):
        cached = projects[cwd]
        # The cache stores project names, but GOOGLE_CLOUD_PROJECT may differ.
        # Only use the cache value if it looks like a real project ID (not just a name).
        if isinstance(cached, str) and cached:
            # Try to return it; caller can verify it works
            return cached

    # 3. API discovery
    if access_token is None:
        raise AuthError(
            "No Google Cloud project ID found. "
            "Set GOOGLE_CLOUD_PROJECT in your environment or .env file, "
            "or run: gemini auth login"
        )

    try:
        resp = httpx.post(
            _LOAD_CODE_ASSIST_URL,
            json={
                "metadata": {
                    "ideType": "GEMINI_CLI",
                    "platform": "LINUX",
                    "pluginType": "GEMINI",
                }
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": _USER_AGENT,
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise AuthError(f"Project discovery failed: {exc}") from exc

    data = resp.json()
    project_id = (
        data.get("cloudaicompanionProject", {}).get("id")
        or data.get("projectId")
        or data.get("project")
    )
    if not project_id:
        raise AuthError(
            f"Could not extract project ID from loadCodeAssist response: "
            f"{str(data)[:200]}"
        )

    return str(project_id)
