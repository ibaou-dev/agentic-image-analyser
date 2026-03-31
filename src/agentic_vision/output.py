"""
Analysis report writer.

Saves full analysis as a markdown file with YAML frontmatter and returns
a condensed AnalysisResult (summary + file path) that is safe to inject
into Claude's context without blowing the token budget.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class AnalysisResult:
    """Returned to the calling agent — small enough to include in context."""

    image_path: str
    analysis_file: str  # absolute path to the saved markdown report
    summary: str  # ≤ summary_max_tokens condensed analysis
    provider: str
    model: str
    duration_seconds: float
    status: str = "success"
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "image_path": self.image_path,
            "analysis_file": self.analysis_file,
            "summary": self.summary,
            "provider": self.provider,
            "model": self.model,
            "duration_seconds": round(self.duration_seconds, 2),
            "status": self.status,
        }
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class ErrorResult:
    """Returned when analysis fails completely."""

    image_path: str
    provider: str
    model: str
    error: str
    duration_seconds: float
    status: str = "error"
    analysis_file: str = ""
    summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "image_path": self.image_path,
            "analysis_file": self.analysis_file,
            "summary": self.summary,
            "provider": self.provider,
            "model": self.model,
            "duration_seconds": round(self.duration_seconds, 2),
            "status": self.status,
            "error": self.error,
        }


def _stem_hash(image_path: str) -> str:
    """8-char content hash of the image path for unique filenames."""
    return hashlib.md5(image_path.encode()).hexdigest()[:8]


def _estimate_tokens(text: str) -> int:
    """Crude token estimate: 1 token ≈ 4 chars (GPT-style)."""
    return max(1, len(text) // 4)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """
    Truncate text to approximately max_tokens, ending at a sentence boundary.
    Returns the truncated text, possibly with a trailing '…'.
    """
    char_limit = max_tokens * 4
    if len(text) <= char_limit:
        return text

    truncated = text[:char_limit]
    # Find the last sentence-ending punctuation before the limit
    for pattern in (r"[.!?]\s", r"\n"):
        matches = list(re.finditer(pattern, truncated))
        if matches:
            last_match = matches[-1]
            return truncated[: last_match.end()].rstrip() + "…"

    # No sentence boundary — truncate at last space
    last_space = truncated.rfind(" ")
    if last_space > char_limit // 2:
        return truncated[:last_space] + "…"
    return truncated + "…"


def _build_markdown(
    *,
    image_path: str,
    provider: str,
    model: str,
    analyzed_at: str,
    prompt: str,
    summary: str,
    full_analysis: str,
    image_size_bytes: int,
    image_dimensions: str,
    duration_seconds: float,
) -> str:
    return f"""---
image: {image_path}
provider: {provider}
model: {model}
analyzed_at: {analyzed_at}
prompt: "{prompt.replace('"', "'")}"
---

# Image Analysis: {Path(image_path).name}

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


def save_analysis(
    *,
    image_path: str,
    full_analysis: str,
    provider: str,
    model: str,
    prompt: str,
    base_dir: Path,
    duration_seconds: float,
    summary_max_tokens: int = 300,
) -> AnalysisResult:
    """
    Save the full analysis to disk and return a slim AnalysisResult.

    The markdown file is saved to:
        <base_dir>/YYYY-MM-DD/<stem>_<hash8>.md

    Args:
        image_path:        Absolute path to the analysed image.
        full_analysis:     Complete model response text.
        provider:          Provider name used.
        model:             Model name used.
        prompt:            The prompt that was sent.
        base_dir:          Root output directory.
        duration_seconds:  How long the analysis took.
        summary_max_tokens: Max tokens for the returned summary.

    Returns:
        AnalysisResult with summary and analysis_file path.
    """
    img = Path(image_path)
    now = datetime.now(UTC)
    analyzed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = now.strftime("%Y-%m-%d")

    # Image metadata (best-effort — Pillow if available, otherwise skip)
    image_size_bytes = img.stat().st_size if img.exists() else 0
    image_dimensions = "unknown"
    try:
        from PIL import Image as PilImage  # type: ignore[import-untyped,unused-ignore]

        with PilImage.open(img) as pil_img:
            w, h = pil_img.size
            image_dimensions = f"{w}x{h}"
    except Exception:
        pass

    # Build summary
    summary = _truncate_to_tokens(full_analysis, summary_max_tokens)

    # Build output path
    output_dir = base_dir / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = img.stem[:40]  # cap long stems
    filename = f"{stem}_{_stem_hash(image_path)}.md"
    output_path = output_dir / filename

    # Write markdown
    content = _build_markdown(
        image_path=image_path,
        provider=provider,
        model=model,
        analyzed_at=analyzed_at,
        prompt=prompt,
        summary=summary,
        full_analysis=full_analysis,
        image_size_bytes=image_size_bytes,
        image_dimensions=image_dimensions,
        duration_seconds=duration_seconds,
    )
    output_path.write_text(content, encoding="utf-8")

    return AnalysisResult(
        image_path=image_path,
        analysis_file=str(output_path.resolve()),
        summary=summary,
        provider=provider,
        model=model,
        duration_seconds=duration_seconds,
    )
