"""
Command-line interface for agentic-vision.

All commands output JSON to stdout (for easy parsing by SKILL.md or MCP).
Exit codes:
    0  — success
    1  — partial failure (some images failed)
    2  — complete failure
    3  — auth / configuration error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agentic_vision import __version__


def _json_out(data: dict[str, Any], *, pretty: bool = False) -> None:
    indent = 2 if pretty else None
    print(json.dumps(data, indent=indent))


def _add_json_pretty(parser: argparse.ArgumentParser) -> None:
    """Add --json and --pretty to a subparser. Both control output format."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="Output compact JSON (default — explicit flag accepted for scripting)",
    )
    group.add_argument(
        "--pretty",
        action="store_true",
        dest="pretty",
        help="Pretty-print JSON output",
    )


def _is_pretty(args: argparse.Namespace) -> bool:
    return getattr(args, "pretty", False)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-vision",
        description="Provider-agnostic image analysis for Claude Code",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # ── analyze ────────────────────────────────────────────────────────────────
    analyze = sub.add_parser("analyze", help="Analyse one or more image files")
    analyze.add_argument(
        "--image", nargs="+", required=True, metavar="PATH", help="Image file(s) to analyse"
    )
    analyze.add_argument("--prompt", metavar="TEXT", help="Custom analysis prompt")
    analyze.add_argument(
        "--provider",
        metavar="NAME",
        help="Force a specific provider (e.g. gemini-oauth, gemini-api)",
    )
    analyze.add_argument("--model", metavar="NAME", help="Force a specific model")
    analyze.add_argument(
        "--output-dir", metavar="PATH", help="Override the output directory for analysis reports"
    )
    _add_json_pretty(analyze)

    # ── list-models ────────────────────────────────────────────────────────────
    list_models = sub.add_parser("list-models", help="List available models per provider")
    list_models.add_argument("--provider", metavar="NAME", help="Filter to a specific provider")
    _add_json_pretty(list_models)

    # ── check-quota ────────────────────────────────────────────────────────────
    check_quota = sub.add_parser("check-quota", help="Show rate limit status")
    check_quota.add_argument("--provider", metavar="NAME", help="Filter to a specific provider")
    _add_json_pretty(check_quota)

    # ── auth-check ─────────────────────────────────────────────────────────────
    auth_check = sub.add_parser("auth-check", help="Verify authentication configuration")
    _add_json_pretty(auth_check)

    # ── precheck ───────────────────────────────────────────────────────────────
    precheck = sub.add_parser("precheck", help="Check environment prerequisites")
    _add_json_pretty(precheck)

    # ── login ──────────────────────────────────────────────────────────────────
    login = sub.add_parser(
        "login",
        help="Authenticate with Gemini (delegates to 'gemini auth login' if available)",
    )
    login.add_argument(
        "--force",
        action="store_true",
        help="Force re-authentication even if credentials exist",
    )
    _add_json_pretty(login)

    # ── export-schema ──────────────────────────────────────────────────────────
    sub.add_parser("export-schema", help="Print JSON Schema for agentic-vision.toml")

    return parser


# ── helpers ───────────────────────────────────────────────────────────────────


def _default_provider_cfgs() -> list[Any]:
    """
    Return a best-effort list of ProviderConfig objects based on available credentials,
    used when no agentic-vision.toml is present.
    """
    import os

    from agentic_vision.auth.gemini_oauth import GeminiOAuthProvider
    from agentic_vision.config import ProviderConfig

    defaults = []
    if GeminiOAuthProvider().is_available():
        defaults.append(
            ProviderConfig(
                name="gemini-oauth",
                priority_model="gemini-3-flash-preview",
                fallback_model="gemini-2.5-flash",
            )
        )
    if os.environ.get("GEMINI_API_KEY"):
        defaults.append(
            ProviderConfig(
                name="gemini-api",
                priority_model="gemini-2.5-pro",
                fallback_model="gemini-2.5-flash",
            )
        )
    if os.environ.get("OPENAI_API_KEY"):
        defaults.append(
            ProviderConfig(
                name="openai",
                priority_model="gpt-4o",
            )
        )
    if os.environ.get("ANTHROPIC_API_KEY"):
        defaults.append(
            ProviderConfig(
                name="anthropic",
                priority_model="claude-sonnet-4-6",
            )
        )
    return defaults


# ── command handlers ──────────────────────────────────────────────────────────


def _cmd_analyze(args: argparse.Namespace) -> int:
    from agentic_vision.config import load_config
    from agentic_vision.engine import AnalysisEngine

    try:
        cfg = load_config()
    except Exception as exc:
        _json_out(
            {"status": "error", "error": f"Config error: {exc}", "results": []},
            pretty=_is_pretty(args),
        )
        return 3

    if args.output_dir:
        cfg.app.output.base_dir = args.output_dir

    engine = AnalysisEngine(cfg)

    # Validate image paths before sending
    valid_paths: list[str] = []
    pre_errors: list[dict[str, Any]] = []
    for raw in args.image:
        p = Path(raw)
        if p.exists():
            valid_paths.append(str(p.resolve()))
        else:
            pre_errors.append(
                {
                    "image_path": raw,
                    "analysis_file": "",
                    "summary": "",
                    "provider": "",
                    "model": "",
                    "duration_seconds": 0.0,
                    "status": "error",
                    "error": f"File not found: {raw}",
                }
            )

    results_raw = engine.analyze(
        valid_paths,
        prompt=args.prompt,
        provider_name=getattr(args, "provider", None),
        model_name=getattr(args, "model", None),
    )

    results = [r.to_dict() for r in results_raw] + pre_errors

    has_errors = any(r.get("status") == "error" for r in results)
    all_errors = all(r.get("status") == "error" for r in results)

    status = "error" if all_errors else ("partial" if has_errors else "success")
    _json_out({"status": status, "results": results, "error": None}, pretty=_is_pretty(args))

    if all_errors:
        return 2
    if has_errors:
        return 1
    return 0


def _cmd_list_models(args: argparse.Namespace) -> int:
    from agentic_vision.config import load_config
    from agentic_vision.engine import _make_provider

    try:
        cfg = load_config()
    except Exception as exc:
        _json_out({"status": "error", "error": str(exc)}, pretty=_is_pretty(args))
        return 3

    target_name = getattr(args, "provider", None)
    providers_list = cfg.enabled_providers() or _default_provider_cfgs()

    providers_out: dict[str, object] = {}
    for pcfg in providers_list:
        if target_name and pcfg.name != target_name:
            continue
        provider = _make_provider(pcfg)
        if provider is None:
            providers_out[pcfg.name] = {"available": False, "error": "not implemented"}
            continue
        try:
            models = provider.list_models()
            providers_out[pcfg.name] = {
                "available": True,
                "models": [m.name for m in models],
                "priority_model": pcfg.priority_model,
                "fallback_model": pcfg.fallback_model,
            }
        except Exception as exc:
            providers_out[pcfg.name] = {"available": False, "error": str(exc)}

    _json_out({"status": "success", "providers": providers_out}, pretty=_is_pretty(args))
    return 0


def _cmd_check_quota(args: argparse.Namespace) -> int:
    from agentic_vision.config import load_config
    from agentic_vision.rate_limiter import RateLimiter

    try:
        cfg = load_config()
    except Exception as exc:
        _json_out({"status": "error", "error": str(exc)}, pretty=_is_pretty(args))
        return 3

    target_name = getattr(args, "provider", None)
    providers_list = cfg.enabled_providers() or _default_provider_cfgs()
    providers_out: dict[str, object] = {}

    for pcfg in providers_list:
        if target_name and pcfg.name != target_name:
            continue
        rl = RateLimiter(rpm=pcfg.rate_limit_rpm, tpm=pcfg.rate_limit_tpm)
        status = rl.status()
        providers_out[pcfg.name] = {
            "rpm_available": round(status["rpm_available"]),
            "rpm_limit": int(status["rpm_capacity"]),
            "tpm_available": round(status["tpm_available"]),
            "tpm_limit": int(status["tpm_capacity"]),
        }

    _json_out({"status": "success", "providers": providers_out}, pretty=_is_pretty(args))
    return 0


def _cmd_auth_check(args: argparse.Namespace) -> int:
    import os

    from agentic_vision.auth.base import AuthError
    from agentic_vision.auth.gemini_oauth import GeminiOAuthProvider
    from agentic_vision.config import load_config

    checks: dict[str, object] = {}

    # OAuth creds
    oauth = GeminiOAuthProvider()
    checks["gemini_oauth_creds_file"] = {
        "available": oauth.is_available(),
        "path": str(oauth._creds_path),
    }

    # Env vars (redacted)
    for var in ("GOOGLE_CLOUD_PROJECT", "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        val = os.environ.get(var)
        checks[var.lower()] = {"set": bool(val), "preview": f"{val[:4]}…" if val else None}

    # Config file
    try:
        cfg = load_config()
        checks["config"] = {
            "available": True,
            "providers": [p.name for p in cfg.enabled_providers()],
        }
    except Exception as exc:
        checks["config"] = {"available": False, "error": str(exc)}

    # Try to get a token
    if oauth.is_available():
        try:
            token = oauth.get_access_token()
            checks["gemini_oauth_token"] = {"valid": True, "preview": f"{token[:8]}…"}
        except AuthError as exc:
            checks["gemini_oauth_token"] = {"valid": False, "error": str(exc)}

    _json_out({"status": "success", "checks": checks}, pretty=_is_pretty(args))
    return 0


def _cmd_precheck(args: argparse.Namespace) -> int:
    from agentic_vision.precheck import all_passed, run_all_checks

    results = run_all_checks()
    checks_out = [
        {
            "name": r.name,
            "passed": r.passed,
            "message": r.message,
            **({"actionable": r.actionable} if r.actionable else {}),
        }
        for r in results
    ]
    passed = all_passed(results)
    _json_out(
        {"status": "ok" if passed else "fail", "checks": checks_out},
        pretty=_is_pretty(args),
    )
    return 0 if passed else 2


def _cmd_login(args: argparse.Namespace) -> int:
    """
    Authenticate with Gemini OAuth.

    Strategy:
      1. If credentials exist and are valid (and --force not set) → report OK.
      2. If gemini CLI is in PATH → delegate to `gemini auth login`.
      3. Otherwise → print manual instructions.
    """
    import shutil
    import subprocess

    from agentic_vision.auth.base import AuthError
    from agentic_vision.auth.gemini_oauth import GeminiOAuthProvider

    oauth = GeminiOAuthProvider()
    force = getattr(args, "force", False)

    # Check current state unless --force
    if not force and oauth.is_available():
        try:
            token = oauth.get_access_token()
            _json_out(
                {
                    "status": "ok",
                    "message": "Already authenticated. Use --force to re-authenticate.",
                    "token_preview": f"{token[:8]}…",
                },
                pretty=_is_pretty(args),
            )
            return 0
        except AuthError:
            pass  # fall through to re-auth

    gemini_bin = shutil.which("gemini")
    if gemini_bin:
        _json_out(
            {
                "status": "delegating",
                "message": f"Delegating to '{gemini_bin} auth login' …",
            },
            pretty=_is_pretty(args),
        )
        result = subprocess.run([gemini_bin, "auth", "login"], check=False)
        if result.returncode == 0:
            _json_out(
                {"status": "ok", "message": "Authentication successful."}, pretty=_is_pretty(args)
            )
            return 0
        _json_out(
            {
                "status": "error",
                "message": f"'gemini auth login' exited with code {result.returncode}.",
            },
            pretty=_is_pretty(args),
        )
        return 3

    # No CLI available — print instructions
    creds_path = oauth._creds_path
    _json_out(
        {
            "status": "error",
            "message": (
                "Gemini CLI not found. To authenticate:\n"
                "  Option A: Install Gemini CLI (https://github.com/google-gemini/gemini-cli) "
                "and run 'gemini auth login'.\n"
                f"  Option B: Manually place OAuth credentials at {creds_path} "
                "(fields: access_token, refresh_token, expiry_date, token_type).\n"
                "  Option C: Set GEMINI_CLI_OAUTH_CLIENT_ID + GEMINI_CLI_OAUTH_CLIENT_SECRET "
                "in .env to enable token refresh without the CLI."
            ),
            "creds_path": str(creds_path),
        },
        pretty=_is_pretty(args),
    )
    return 3


def _cmd_export_schema(_args: argparse.Namespace) -> int:
    from agentic_vision.config import export_json_schema

    print(export_json_schema())
    return 0


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    dispatch = {
        "analyze": _cmd_analyze,
        "list-models": _cmd_list_models,
        "check-quota": _cmd_check_quota,
        "auth-check": _cmd_auth_check,
        "precheck": _cmd_precheck,
        "login": _cmd_login,
        "export-schema": _cmd_export_schema,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(2)

    sys.exit(handler(args))
