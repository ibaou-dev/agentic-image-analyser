"""Unit tests for analysis output writer."""

from __future__ import annotations

from pathlib import Path

from agentic_vision.output import (
    AnalysisResult,
    _estimate_tokens,
    _truncate_to_tokens,
    save_analysis,
)


# ─── Token helpers ────────────────────────────────────────────────────────────
class TestTokenHelpers:
    def test_estimate_tokens_non_zero(self) -> None:
        assert _estimate_tokens("hello world") >= 1

    def test_estimate_tokens_scales(self) -> None:
        short = _estimate_tokens("hi")
        long = _estimate_tokens("x" * 400)
        assert long > short

    def test_truncate_short_text_unchanged(self) -> None:
        text = "Short sentence."
        assert _truncate_to_tokens(text, 100) == text

    def test_truncate_adds_ellipsis(self) -> None:
        text = "A" * 2000  # ~500 tokens
        result = _truncate_to_tokens(text, 100)
        assert result.endswith("…")
        assert len(result) <= 430  # 100 tokens * 4 chars + ellipsis

    def test_truncate_at_sentence_boundary(self) -> None:
        # Build text with a sentence boundary before the limit
        sentences = "This is sentence one. " * 5 + "This is sentence two. " * 50
        result = _truncate_to_tokens(sentences, 50)
        assert result.endswith(".…") or result.endswith(". …") or result.endswith("…")
        assert "sentence one." in result  # at least the early sentences


# ─── AnalysisResult ───────────────────────────────────────────────────────────
class TestAnalysisResult:
    def test_to_dict_no_error(self) -> None:
        r = AnalysisResult(
            image_path="/img.png",
            analysis_file="/out.md",
            summary="Summary here",
            provider="gemini-oauth",
            model="gemini-2.5-pro",
            duration_seconds=2.5,
        )
        d = r.to_dict()
        assert d["status"] == "success"
        assert "error" not in d
        assert d["duration_seconds"] == 2.5

    def test_to_dict_with_error(self) -> None:
        r = AnalysisResult(
            image_path="/img.png",
            analysis_file="",
            summary="",
            provider="gemini-oauth",
            model="gemini-2.5-pro",
            duration_seconds=0.1,
            status="error",
            error="rate limited",
        )
        d = r.to_dict()
        assert d["error"] == "rate limited"

    def test_duration_rounded(self) -> None:
        r = AnalysisResult(
            image_path="/img.png",
            analysis_file="/out.md",
            summary="s",
            provider="p",
            model="m",
            duration_seconds=3.14159,
        )
        assert r.to_dict()["duration_seconds"] == 3.14


# ─── save_analysis ────────────────────────────────────────────────────────────
class TestSaveAnalysis:
    def test_saves_markdown_file(self, tmp_path: Path) -> None:
        # Create a tiny fake PNG
        fake_img = tmp_path / "screenshot.png"
        fake_img.write_bytes(b"PNG data here")  # not a real PNG, just for path/size

        result = save_analysis(
            image_path=str(fake_img),
            full_analysis="The UI shows a login form with a blue button.",
            provider="gemini-oauth",
            model="gemini-2.5-pro",
            prompt="Analyse this screenshot.",
            base_dir=tmp_path / "analyses",
            duration_seconds=1.5,
        )

        assert result.status == "success"
        assert Path(result.analysis_file).exists()
        content = Path(result.analysis_file).read_text()
        assert "gemini-oauth" in content
        assert "gemini-2.5-pro" in content
        assert "login form" in content
        assert "image:" in content  # YAML frontmatter

    def test_creates_date_subdirectory(self, tmp_path: Path) -> None:
        fake_img = tmp_path / "img.png"
        fake_img.write_bytes(b"x")

        result = save_analysis(
            image_path=str(fake_img),
            full_analysis="Some analysis.",
            provider="gemini-api",
            model="gemini-2.5-flash",
            prompt="Describe.",
            base_dir=tmp_path / "out",
            duration_seconds=0.5,
        )

        analysis_path = Path(result.analysis_file)
        # Parent is a date directory like 2026-03-31
        date_dir = analysis_path.parent.name
        assert len(date_dir) == 10
        assert date_dir[4] == "-" and date_dir[7] == "-"

    def test_summary_respects_max_tokens(self, tmp_path: Path) -> None:
        fake_img = tmp_path / "img.png"
        fake_img.write_bytes(b"x")
        long_analysis = "Word " * 1000  # ~4000 tokens

        result = save_analysis(
            image_path=str(fake_img),
            full_analysis=long_analysis,
            provider="p",
            model="m",
            prompt="q",
            base_dir=tmp_path / "out",
            duration_seconds=1.0,
            summary_max_tokens=100,
        )

        # Summary should be at most ~100 tokens (400 chars) + small overhead for ellipsis
        assert len(result.summary) <= 450

    def test_filename_uses_stem_and_hash(self, tmp_path: Path) -> None:
        fake_img = tmp_path / "my-screenshot.png"
        fake_img.write_bytes(b"x")

        result = save_analysis(
            image_path=str(fake_img),
            full_analysis="Analysis.",
            provider="p",
            model="m",
            prompt="q",
            base_dir=tmp_path / "out",
            duration_seconds=1.0,
        )

        filename = Path(result.analysis_file).name
        assert filename.startswith("my-screenshot_")
        assert filename.endswith(".md")

    def test_duplicate_image_path_same_filename(self, tmp_path: Path) -> None:
        """Same image path always produces the same output filename."""
        fake_img = tmp_path / "img.png"
        fake_img.write_bytes(b"x")

        r1 = save_analysis(
            image_path=str(fake_img),
            full_analysis="A",
            provider="p",
            model="m",
            prompt="q",
            base_dir=tmp_path / "out",
            duration_seconds=1.0,
        )
        r2 = save_analysis(
            image_path=str(fake_img),
            full_analysis="B",
            provider="p",
            model="m",
            prompt="q",
            base_dir=tmp_path / "out",
            duration_seconds=1.0,
        )
        assert Path(r1.analysis_file).name == Path(r2.analysis_file).name
