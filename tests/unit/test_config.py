"""Unit tests for config loading and validation."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from agentic_vision.config import (
    AppConfig,
    FallbackConfig,
    OutputConfig,
    PromptsConfig,
    ProviderConfig,
    export_json_schema,
    load_app_config,
)


# ─── OutputConfig ─────────────────────────────────────────────────────────────
class TestOutputConfig:
    def test_defaults(self) -> None:
        cfg = OutputConfig()
        assert cfg.base_dir == "./image-analyses"
        assert cfg.summary_max_tokens == 300

    def test_base_path_is_path(self) -> None:
        cfg = OutputConfig(base_dir="/tmp/analyses")
        assert cfg.base_path == Path("/tmp/analyses")

    def test_summary_max_tokens_bounds(self) -> None:
        with pytest.raises(ValueError):
            OutputConfig(summary_max_tokens=10)  # < 50
        with pytest.raises(ValueError):
            OutputConfig(summary_max_tokens=9999)  # > 2000


# ─── FallbackConfig ───────────────────────────────────────────────────────────
class TestFallbackConfig:
    def test_defaults(self) -> None:
        cfg = FallbackConfig()
        assert cfg.mode == "auto"
        assert "rate_limit" in cfg.auto_on_errors

    def test_invalid_mode(self) -> None:
        with pytest.raises(ValueError):
            FallbackConfig(mode="magic")  # type: ignore[arg-type]

    def test_valid_modes(self) -> None:
        for mode in ("auto", "llm-prompt", "disabled"):
            cfg = FallbackConfig(mode=mode)  # type: ignore[arg-type]
            assert cfg.mode == mode


# ─── ProviderConfig ───────────────────────────────────────────────────────────
class TestProviderConfig:
    def test_basic(self) -> None:
        p = ProviderConfig(name="gemini-oauth", priority_model="gemini-2.5-pro")
        assert p.name == "gemini-oauth"
        assert p.enabled is True
        assert p.fallback_model is None

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError):
            ProviderConfig(name="  ", priority_model="x")

    def test_name_stripped(self) -> None:
        p = ProviderConfig(name=" gemini-api ", priority_model="x")
        assert p.name == "gemini-api"

    def test_rpm_bounds(self) -> None:
        with pytest.raises(ValueError):
            ProviderConfig(name="x", priority_model="m", rate_limit_rpm=0)  # < 1
        with pytest.raises(ValueError):
            ProviderConfig(name="x", priority_model="m", rate_limit_rpm=99_999)  # > 10_000


# ─── AppConfig ────────────────────────────────────────────────────────────────
class TestAppConfig:
    def test_defaults(self) -> None:
        cfg = AppConfig()
        assert cfg.providers == []
        assert isinstance(cfg.output, OutputConfig)
        assert isinstance(cfg.fallback, FallbackConfig)
        assert isinstance(cfg.prompts, PromptsConfig)

    def test_enabled_providers(self) -> None:
        cfg = AppConfig(providers=[
            ProviderConfig(name="gemini-oauth", priority_model="x", enabled=True),
            ProviderConfig(name="gemini-api",   priority_model="x", enabled=False),
        ])
        enabled = cfg.enabled_providers()
        assert len(enabled) == 1
        assert enabled[0].name == "gemini-oauth"

    def test_duplicate_provider_names_rejected(self) -> None:
        with pytest.raises(ValueError, match="unique"):
            AppConfig(providers=[
                ProviderConfig(name="gemini-oauth", priority_model="a"),
                ProviderConfig(name="gemini-oauth", priority_model="b"),
            ])

    def test_get_provider(self) -> None:
        cfg = AppConfig(providers=[
            ProviderConfig(name="gemini-api", priority_model="gemini-2.5-pro"),
        ])
        found = cfg.get_provider("gemini-api")
        assert found is not None
        assert found.priority_model == "gemini-2.5-pro"
        assert cfg.get_provider("missing") is None


# ─── TOML loading ─────────────────────────────────────────────────────────────
class TestTomlLoading:
    def test_load_from_toml_file(self, tmp_path: Path) -> None:
        toml = tmp_path / "agentic-vision.toml"
        toml.write_text(textwrap.dedent("""\
            [output]
            base_dir = "/tmp/test-analyses"
            summary_max_tokens = 200

            [[providers]]
            name = "gemini-oauth"
            priority_model = "gemini-2.5-pro"
            fallback_model = "gemini-2.5-flash"
            enabled = true
        """))
        cfg = load_app_config(toml)
        assert cfg.output.base_dir == "/tmp/test-analyses"
        assert cfg.output.summary_max_tokens == 200
        assert len(cfg.providers) == 1
        assert cfg.providers[0].fallback_model == "gemini-2.5-flash"

    def test_missing_toml_returns_defaults(self) -> None:
        cfg = load_app_config(Path("/nonexistent/path/agentic-vision.toml"))
        assert cfg.output.base_dir == "./image-analyses"
        assert cfg.providers == []

    def test_invalid_toml_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "agentic-vision.toml"
        bad.write_text("[output]\nsummary_max_tokens = 5\n")  # below minimum
        with pytest.raises(ValueError):
            load_app_config(bad)


# ─── Schema export ────────────────────────────────────────────────────────────
class TestSchemaExport:
    def test_schema_is_valid_json(self) -> None:
        import json
        schema_str = export_json_schema()
        schema = json.loads(schema_str)
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_schema_contains_key_fields(self) -> None:
        import json
        schema = json.loads(export_json_schema())
        assert "output" in schema["properties"]
        assert "providers" in schema["properties"]
        assert "fallback" in schema["properties"]
