"""Unit tests for fallback logic."""

from __future__ import annotations

import pytest

from agentic_vision.config import FallbackConfig, ProviderConfig
from agentic_vision.fallback import FallbackDecider, FallbackExhaustedError
from agentic_vision.providers.base import (
    AuthFailureError,
    InvalidImageError,
    ModelUnavailableError,
    ProviderError,
    RateLimitError,
)
from agentic_vision.providers.base import TimeoutError as ProviderTimeoutError


def _make_cfg(
    name: str = "gemini-oauth", fallback_model: str | None = "gemini-2.5-flash"
) -> ProviderConfig:
    return ProviderConfig(
        name=name,
        priority_model="gemini-2.5-pro",
        fallback_model=fallback_model,
        enabled=True,
    )


def _make_decider(mode: str = "auto", auto_on: list[str] | None = None) -> FallbackDecider:
    cfg = FallbackConfig(
        mode=mode,  # type: ignore[arg-type]
        auto_on_errors=auto_on or ["rate_limit", "auth_failure", "model_unavailable", "timeout"],
    )
    return FallbackDecider(cfg)


# ─── should_fallback ──────────────────────────────────────────────────────────
class TestShouldFallback:
    def test_never_fallback_on_invalid_image(self) -> None:
        decider = _make_decider(mode="auto")
        assert decider.should_fallback(InvalidImageError("bad"), _make_cfg()) is False

    def test_auto_fallback_on_rate_limit(self) -> None:
        decider = _make_decider(mode="auto")
        assert decider.should_fallback(RateLimitError("429"), _make_cfg()) is True

    def test_auto_fallback_on_auth_failure(self) -> None:
        decider = _make_decider(mode="auto")
        assert decider.should_fallback(AuthFailureError("401"), _make_cfg()) is True

    def test_auto_fallback_on_timeout(self) -> None:
        decider = _make_decider(mode="auto")
        assert decider.should_fallback(ProviderTimeoutError("timeout"), _make_cfg()) is True

    def test_auto_fallback_on_model_unavailable(self) -> None:
        decider = _make_decider(mode="auto")
        assert decider.should_fallback(ModelUnavailableError("404"), _make_cfg()) is True

    def test_disabled_never_fallbacks(self) -> None:
        decider = _make_decider(mode="disabled")
        for exc in (RateLimitError("x"), AuthFailureError("x"), ProviderTimeoutError("x")):
            assert decider.should_fallback(exc, _make_cfg()) is False

    def test_auto_respects_configured_error_list(self) -> None:
        decider = _make_decider(mode="auto", auto_on=["rate_limit"])
        # auth_failure NOT in list → no fallback
        assert decider.should_fallback(AuthFailureError("401"), _make_cfg()) is False
        # rate_limit IS in list → fallback
        assert decider.should_fallback(RateLimitError("429"), _make_cfg()) is True

    def test_generic_provider_error_not_in_auto_list(self) -> None:
        decider = _make_decider(mode="auto")
        # ProviderError (generic) is "provider_error" category — not in default list
        assert decider.should_fallback(ProviderError("oops"), _make_cfg()) is False


# ─── next_option ─────────────────────────────────────────────────────────────
class TestNextOption:
    def test_uses_fallback_model_first(self) -> None:
        decider = _make_decider()
        cfg = _make_cfg(fallback_model="gemini-2.5-flash")
        result_cfg, result_model = decider.next_option(cfg, [cfg], "gemini-2.5-pro")
        assert result_model == "gemini-2.5-flash"
        assert result_cfg.name == cfg.name

    def test_moves_to_next_provider_when_no_fallback_model(self) -> None:
        decider = _make_decider()
        primary = ProviderConfig(
            name="gemini-oauth", priority_model="gemini-2.5-pro", fallback_model=None, enabled=True
        )
        secondary = ProviderConfig(name="gemini-api", priority_model="gemini-2.5-pro", enabled=True)
        result_cfg, result_model = decider.next_option(
            primary, [primary, secondary], "gemini-2.5-pro"
        )
        assert result_cfg.name == "gemini-api"
        assert result_model == "gemini-2.5-pro"

    def test_skips_disabled_providers(self) -> None:
        decider = _make_decider()
        primary = _make_cfg("gemini-oauth", fallback_model=None)
        disabled = ProviderConfig(name="gemini-api", priority_model="x", enabled=False)
        active = ProviderConfig(name="anthropic", priority_model="claude-sonnet-4-6", enabled=True)
        result_cfg, _ = decider.next_option(primary, [primary, disabled, active], "gemini-2.5-pro")
        assert result_cfg.name == "anthropic"

    def test_raises_when_exhausted(self) -> None:
        decider = _make_decider()
        single = _make_cfg(fallback_model=None)
        with pytest.raises(FallbackExhaustedError):
            decider.next_option(single, [single], "gemini-2.5-pro")

    def test_skips_to_fallback_model_on_same_provider_if_not_tried(self) -> None:
        decider = _make_decider()
        cfg = _make_cfg(fallback_model="gemini-2.5-flash")
        # Already failed on fallback_model — should skip to next provider
        next_cfg = ProviderConfig(name="gemini-api", priority_model="gemini-pro", enabled=True)
        result_cfg, _result_model = decider.next_option(cfg, [cfg, next_cfg], "gemini-2.5-flash")
        assert result_cfg.name == "gemini-api"
