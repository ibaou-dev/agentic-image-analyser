"""
Analysis engine — orchestrates auth, provider selection, rate limiting, fallback, and output.
"""
from __future__ import annotations

import time
from pathlib import Path

from agentic_vision.config import Config, ProviderConfig
from agentic_vision.fallback import FallbackDecider, FallbackExhaustedError
from agentic_vision.output import AnalysisResult, ErrorResult, save_analysis
from agentic_vision.providers.base import ProviderError, VisionProvider
from agentic_vision.providers.code_assist import CodeAssistProvider
from agentic_vision.rate_limiter import RateLimiter


def _make_provider(provider_cfg: ProviderConfig) -> VisionProvider | None:
    """Instantiate the correct VisionProvider for a given config."""
    from agentic_vision.providers.anthropic import AnthropicVisionProvider
    from agentic_vision.providers.gemini_direct import GeminiDirectProvider
    from agentic_vision.providers.openai_compat import OpenAICompatVisionProvider

    name = provider_cfg.name
    if name == "gemini-oauth":
        return CodeAssistProvider()
    if name == "gemini-api":
        return GeminiDirectProvider()
    if name == "openai":
        return OpenAICompatVisionProvider()
    if name == "anthropic":
        return AnthropicVisionProvider()
    return None


def _estimate_tokens_for_image(image_path: str) -> int:
    """Rough token estimate: image_size_bytes / 750."""
    try:
        size = Path(image_path).stat().st_size
        return max(500, size // 750)
    except OSError:
        return 1_000


def _default_provider_config() -> ProviderConfig:
    return ProviderConfig(name="gemini-oauth", priority_model="gemini-2.5-pro")


class AnalysisEngine:
    """
    Orchestrates image analysis across providers with fallback and rate limiting.

    Usage:
        engine = AnalysisEngine(config)
        results = engine.analyze(["/path/to/img.png"], prompt="Describe this.")
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._fallback_decider = FallbackDecider(config.fallback)

    def _get_rate_limiter(self, provider_cfg: ProviderConfig) -> RateLimiter:
        if provider_cfg.name not in self._rate_limiters:
            self._rate_limiters[provider_cfg.name] = RateLimiter(
                rpm=provider_cfg.rate_limit_rpm,
                tpm=provider_cfg.rate_limit_tpm,
            )
        return self._rate_limiters[provider_cfg.name]

    def _select_primary(
        self,
        provider_name: str | None,
        model_name: str | None,
    ) -> tuple[VisionProvider, ProviderConfig, str]:
        candidates = self._config.enabled_providers()

        if provider_name:
            cfg = next((p for p in candidates if p.name == provider_name), None)
            if cfg is None:
                cfg = ProviderConfig(
                    name=provider_name,
                    priority_model=model_name or "gemini-2.5-pro",
                )
        elif candidates:
            cfg = candidates[0]
        else:
            cfg = _default_provider_config()

        provider = _make_provider(cfg)
        if provider is None:
            raise ProviderError(
                f"Provider '{cfg.name}' is not implemented. "
                "Available: gemini-oauth, gemini-api, openai, anthropic"
            )
        model = model_name or cfg.priority_model
        return provider, cfg, model

    def analyze(
        self,
        image_paths: list[str],
        *,
        prompt: str | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> list[AnalysisResult | ErrorResult]:
        """
        Analyse one or more images, applying fallback if configured.

        Args:
            image_paths:   List of absolute paths to image files.
            prompt:        Analysis prompt. Falls back to config default.
            provider_name: Force a specific provider by name.
            model_name:    Force a specific model.

        Returns:
            One result per image (AnalysisResult on success, ErrorResult on failure).
        """
        provider, cfg, model = self._select_primary(provider_name, model_name)
        effective_prompt = prompt or self._config.prompts.default_generic
        output_dir = self._config.output.base_path
        summary_max = self._config.output.summary_max_tokens

        return [
            self._analyze_single(
                image_path=path,
                prompt=effective_prompt,
                provider=provider,
                cfg=cfg,
                model=model,
                output_dir=output_dir,
                summary_max_tokens=summary_max,
            )
            for path in image_paths
        ]

    def _analyze_single(
        self,
        *,
        image_path: str,
        prompt: str,
        provider: VisionProvider,
        cfg: ProviderConfig,
        model: str,
        output_dir: Path,
        summary_max_tokens: int,
    ) -> AnalysisResult | ErrorResult:
        start = time.monotonic()

        # Rate limiting
        estimated_tokens = _estimate_tokens_for_image(image_path)
        rate_limiter = self._get_rate_limiter(cfg)
        if not rate_limiter.acquire(estimated_tokens=estimated_tokens, timeout=30.0):
            return ErrorResult(
                image_path=image_path,
                provider=provider.name,
                model=model,
                error="rate_limit: could not acquire rate limit slot within 30s",
                duration_seconds=time.monotonic() - start,
            )

        # Analysis with fallback
        try:
            full_analysis = provider.analyze_image(image_path, prompt, model)
        except Exception as exc:
            if not self._fallback_decider.should_fallback(exc, cfg):
                return ErrorResult(
                    image_path=image_path,
                    provider=provider.name,
                    model=model,
                    error=str(exc),
                    duration_seconds=time.monotonic() - start,
                )
            # Attempt fallback
            try:
                fallback_cfg, fallback_model = self._fallback_decider.next_option(
                    cfg,
                    self._config.enabled_providers() or [cfg],
                    model,
                )
                fallback_provider = _make_provider(fallback_cfg)
                if fallback_provider is None:
                    raise FallbackExhaustedError(f"No provider for '{fallback_cfg.name}'")

                fallback_rl = self._get_rate_limiter(fallback_cfg)
                fallback_rl.acquire(estimated_tokens=estimated_tokens, timeout=15.0)
                full_analysis = fallback_provider.analyze_image(
                    image_path, prompt, fallback_model
                )
                # Use fallback provider/model in the result
                provider = fallback_provider
                model = fallback_model
            except (FallbackExhaustedError, Exception) as fallback_exc:
                return ErrorResult(
                    image_path=image_path,
                    provider=provider.name,
                    model=model,
                    error=f"{exc} | fallback also failed: {fallback_exc}",
                    duration_seconds=time.monotonic() - start,
                )

        return save_analysis(
            image_path=image_path,
            full_analysis=full_analysis,
            provider=provider.name,
            model=model,
            prompt=prompt,
            base_dir=output_dir,
            duration_seconds=time.monotonic() - start,
            summary_max_tokens=summary_max_tokens,
        )
