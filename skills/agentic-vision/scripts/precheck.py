#!/usr/bin/env python3
"""
precheck.py — stdlib-only preflight check for the agentic-vision skill.

Usage:
    python3 .agents/skills/agentic-vision/scripts/precheck.py
    python3 .agents/skills/agentic-vision/scripts/precheck.py --json

Exits 0 if all checks pass, 1 if any check fails.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path


def _check_python_version() -> dict[str, object]:
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 12)
    return {
        "name": "python_version",
        "passed": ok,
        "detail": f"Python {major}.{minor}",
        "actionable": "" if ok else "Install Python 3.12 or newer.",
    }


def _check_uv() -> dict[str, object]:
    found = shutil.which("uv") is not None
    return {
        "name": "uv",
        "passed": found,
        "detail": "uv found" if found else "uv not found",
        "actionable": "" if found else (
            "Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh  "
            "(see https://docs.astral.sh/uv/)"
        ),
    }


def _check_oauth_creds() -> dict[str, object]:
    creds_path_raw = os.environ.get("GEMINI_OAUTH_CREDS_PATH", "~/.gemini/oauth_creds.json")
    creds_path = Path(creds_path_raw).expanduser()

    if not creds_path.exists():
        return {
            "name": "gemini_oauth",
            "passed": False,
            "detail": f"Not found: {creds_path}",
            "actionable": (
                "Authenticate with Gemini: run 'agentic-vision login' "
                "or 'gemini auth login' (Gemini CLI)."
            ),
        }

    try:
        data = json.loads(creds_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "name": "gemini_oauth",
            "passed": False,
            "detail": f"Cannot read {creds_path}: {exc}",
            "actionable": "Delete the file and re-authenticate: agentic-vision login",
        }

    if "access_token" not in data:
        return {
            "name": "gemini_oauth",
            "passed": False,
            "detail": f"{creds_path} exists but has no access_token field",
            "actionable": "Re-authenticate: agentic-vision login",
        }

    return {
        "name": "gemini_oauth",
        "passed": True,
        "detail": f"Credentials found at {creds_path}",
        "actionable": "",
    }


def main() -> None:
    as_json = "--json" in sys.argv

    checks = [
        _check_python_version(),
        _check_uv(),
        _check_oauth_creds(),
    ]

    all_passed = all(c["passed"] for c in checks)
    status = "ok" if all_passed else "error"

    failed = [c for c in checks if not c["passed"]]
    actionable = "; ".join(c["actionable"] for c in failed if c["actionable"])

    result = {
        "status": status,
        "checks": checks,
        "actionable": actionable,
    }

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        for c in checks:
            mark = "✓" if c["passed"] else "✗"
            print(f"  {mark} {c['name']}: {c['detail']}")
        if not all_passed:
            print(f"\nAction required: {actionable}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
