"""
Tool definitions for the agentic-vision MCP server.

Thin wrappers over the CLI engine — all heavy lifting is in agentic_vision.engine.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is importable when running from mcp/
_src = Path(__file__).parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from agentic_vision.config import load_config
from agentic_vision.engine import AnalysisEngine
from agentic_vision.output import AnalysisResult, ErrorResult


def _engine() -> AnalysisEngine:
    return AnalysisEngine(load_config())


def register_tools(mcp: object) -> None:  # mcp: FastMCP instance
    """Register all tools on the FastMCP server."""

    @mcp.tool()  # type: ignore[attr-defined]
    def analyze_image(
        image_path: str,
        prompt: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict:
        """
        Analyse a single local image file using a vision model.

        Returns a summary (≤300 tokens) and the path to the full markdown report.
        Image bytes never enter the MCP context — only the summary is returned.

        Args:
            image_path: Absolute path to the image file (PNG, JPEG, WEBP, GIF).
            prompt: Custom analysis prompt. Defaults to generic analysis.
            provider: Force a specific provider (gemini-oauth, gemini-api, openai, anthropic).
            model: Force a specific model name.

        Returns:
            {
                "status": "success" | "error",
                "summary": "...",
                "analysis_file": "/path/to/report.md",
                "provider": "gemini-oauth",
                "model": "gemini-2.5-pro",
                "duration_seconds": 3.7,
                "error": null
            }
        """
        path = Path(image_path)
        if not path.is_absolute():
            return {"status": "error", "error": f"image_path must be absolute, got: {image_path}"}
        if not path.exists():
            return {"status": "error", "error": f"File not found: {image_path}"}

        engine = _engine()
        results = engine.analyze(
            [str(path)],
            prompt=prompt,
            provider_name=provider,
            model_name=model,
        )
        result = results[0]
        return _format_result(result)

    @mcp.tool()  # type: ignore[attr-defined]
    def analyze_images_batch(
        image_paths: list[str],
        prompt: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict:
        """
        Analyse multiple local image files in a single call.

        Returns a summary for each image (≤300 tokens each) and paths to full reports.
        Image bytes never enter the MCP context.

        Args:
            image_paths: List of absolute paths to image files.
            prompt: Custom analysis prompt applied to all images.
            provider: Force a specific provider for all images.
            model: Force a specific model for all images.

        Returns:
            {
                "status": "success" | "partial" | "error",
                "results": [...],
                "error": null
            }
        """
        errors = []
        valid_paths = []
        for p in image_paths:
            path = Path(p)
            if not path.is_absolute():
                errors.append({"image_path": p, "error": "Must be an absolute path"})
            elif not path.exists():
                errors.append({"image_path": p, "error": "File not found"})
            else:
                valid_paths.append(str(path))

        if not valid_paths:
            return {
                "status": "error",
                "results": errors,
                "error": "No valid image paths provided",
            }

        engine = _engine()
        results = engine.analyze(
            valid_paths,
            prompt=prompt,
            provider_name=provider,
            model_name=model,
        )

        formatted = [_format_result(r) for r in results] + errors
        all_ok = all(r.get("status") == "success" for r in formatted)
        some_ok = any(r.get("status") == "success" for r in formatted)

        return {
            "status": "success" if all_ok else ("partial" if some_ok else "error"),
            "results": formatted,
            "error": None,
        }

    @mcp.tool()  # type: ignore[attr-defined]
    def list_models(provider: str | None = None) -> dict:
        """
        List available vision models, optionally filtered by provider.

        Args:
            provider: Provider name to filter by (gemini-oauth, gemini-api, openai, anthropic).

        Returns:
            {"providers": [{"name": "...", "models": ["..."], "enabled": true}]}
        """
        from agentic_vision.providers.code_assist import _KNOWN_VISION_MODELS as code_assist_models

        gemini_models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

        config = load_config()
        providers_info = []

        model_map = {
            "gemini-oauth": code_assist_models,
            "gemini-api": gemini_models,
            "openai": ["gpt-4o", "gpt-4-turbo", "gpt-4-vision-preview"],
            "anthropic": [
                "claude-opus-4-6",
                "claude-sonnet-4-6",
                "claude-haiku-4-5-20251001",
                "claude-3-5-sonnet-latest",
            ],
        }

        for pcfg in config.providers:
            if provider and pcfg.name != provider:
                continue
            models = model_map.get(pcfg.name, [pcfg.priority_model])
            providers_info.append({
                "name": pcfg.name,
                "models": models,
                "priority_model": pcfg.priority_model,
                "fallback_model": pcfg.fallback_model,
                "enabled": pcfg.enabled,
            })

        # Include unconfigured providers if filtering by specific provider
        if provider and not providers_info:
            models = model_map.get(provider, [])
            providers_info.append({
                "name": provider,
                "models": models,
                "priority_model": models[0] if models else "unknown",
                "fallback_model": models[1] if len(models) > 1 else None,
                "enabled": True,
            })

        return {"providers": providers_info}

    @mcp.tool()  # type: ignore[attr-defined]
    def check_quota(provider: str | None = None) -> dict:
        """
        Check current rate limit status for configured providers.

        Args:
            provider: Provider name to check. Checks all enabled providers if omitted.

        Returns:
            {"providers": [{"name": "...", "rpm": {...}, "tpm": {...}}]}
        """
        config = load_config()
        engine = _engine()

        results = []
        for pcfg in config.providers:
            if provider and pcfg.name != provider:
                continue
            if not pcfg.enabled:
                continue
            rl = engine._get_rate_limiter(pcfg)
            status = rl.status()
            results.append({
                "name": pcfg.name,
                "rpm": status.get("rpm", {}),
                "tpm": status.get("tpm", {}),
            })

        return {"providers": results}


def _format_result(result: AnalysisResult | ErrorResult) -> dict:
    if isinstance(result, AnalysisResult):
        return {
            "status": "success",
            "image_path": result.image_path,
            "summary": result.summary,
            "analysis_file": str(result.analysis_file),
            "provider": result.provider,
            "model": result.model,
            "duration_seconds": round(result.duration_seconds, 2),
            "error": None,
        }
    return {
        "status": "error",
        "image_path": result.image_path,
        "summary": None,
        "analysis_file": None,
        "provider": result.provider,
        "model": result.model,
        "duration_seconds": round(result.duration_seconds, 2),
        "error": result.error,
    }
