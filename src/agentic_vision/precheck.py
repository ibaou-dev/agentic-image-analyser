"""
Pre-flight checks for agentic-vision.

Run before any analysis to validate that the environment is correctly set up.
Used by the SKILL.md to fail fast with actionable error messages.
"""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    actionable: str = ""  # what the user can do to fix it


def check_python_version() -> CheckResult:
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 12)
    return CheckResult(
        name="python_version",
        passed=ok,
        message=f"Python {major}.{minor} {'≥' if ok else '<'} 3.12",
        actionable="" if ok else "Install Python 3.12+: https://python.org",
    )


def check_uv_available() -> CheckResult:
    uv = shutil.which("uv")
    return CheckResult(
        name="uv_available",
        passed=bool(uv),
        message=f"uv {'found' if uv else 'not found'}{f' at {uv}' if uv else ''}",
        actionable="" if uv else "Install uv: curl -Ls https://astral.sh/uv | sh",
    )


def check_venv_exists() -> CheckResult:
    venv = Path(".venv")
    return CheckResult(
        name="venv_exists",
        passed=venv.exists(),
        message=f".venv {'exists' if venv.exists() else 'not found'}",
        actionable="" if venv.exists() else "Run: uv sync --dev",
    )


def check_auth_available() -> CheckResult:
    """Check if at least one auth method is configured."""
    import os

    checks = {
        "Gemini CLI OAuth (~/.gemini/oauth_creds.json)": Path.home() / ".gemini" / "oauth_creds.json",
    }
    env_keys = ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]

    for label, path in checks.items():
        if path.exists():
            return CheckResult(
                name="auth_available",
                passed=True,
                message=f"Auth configured: {label}",
            )

    for key in env_keys:
        if os.environ.get(key):
            return CheckResult(
                name="auth_available",
                passed=True,
                message=f"Auth configured: {key} env var",
            )

    return CheckResult(
        name="auth_available",
        passed=False,
        message="No auth method configured",
        actionable=(
            "Run: gemini auth login  (Gemini CLI OAuth)\n"
            "  OR set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in .env"
        ),
    )


def check_config_available() -> CheckResult:
    """Check if a config file exists (optional — defaults are fine)."""
    cfg_paths = [
        Path("agentic-vision.toml"),
        Path.home() / ".config" / "agentic-vision" / "agentic-vision.toml",
    ]
    for p in cfg_paths:
        if p.exists():
            return CheckResult(
                name="config_available",
                passed=True,
                message=f"Config found: {p}",
            )
    return CheckResult(
        name="config_available",
        passed=True,  # defaults are valid — this is not a hard failure
        message="No config file found — using defaults",
        actionable="Copy agentic-vision.toml.example to agentic-vision.toml to customise",
    )


def run_all_checks() -> list[CheckResult]:
    return [
        check_python_version(),
        check_uv_available(),
        check_venv_exists(),
        check_auth_available(),
        check_config_available(),
    ]


def all_passed(results: list[CheckResult]) -> bool:
    return all(r.passed for r in results)
