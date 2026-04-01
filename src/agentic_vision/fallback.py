"""
Fallback decision logic.

Three modes:
  - "auto"        — fall back immediately when the error is in auto_on_errors list
  - "llm-prompt"  — ask an LLM to decide (requires an available text provider)
  - "disabled"    — never fall back; surface the error immediately

Error categorisation:
  - rate_limit         → RateLimitError
  - auth_failure       → AuthFailureError
  - model_unavailable  → ModelUnavailableError
  - timeout            → TimeoutError (provider)
  - invalid_image      → InvalidImageError  (do NOT fall back — image-side problem)
"""

from __future__ import annotations

from agentic_vision.config import FallbackConfig, ProviderConfig
from agentic_vision.providers.base import (
    AuthFailureError,
    InvalidImageError,
    ModelUnavailableError,
    RateLimitError,
)
from agentic_vision.providers.base import TimeoutError as ProviderTimeoutError

# Map error types → category strings used in FallbackConfig.auto_on_errors
_ERROR_CATEGORY: dict[type[Exception], str] = {
    RateLimitError: "rate_limit",
    AuthFailureError: "auth_failure",
    ModelUnavailableError: "model_unavailable",
    ProviderTimeoutError: "timeout",
    InvalidImageError: "invalid_image",  # never falls back
}


def _categorise(error: Exception) -> str:
    for exc_type, category in _ERROR_CATEGORY.items():
        if isinstance(error, exc_type):
            return category
    return "provider_error"


class FallbackExhaustedError(Exception):
    """Raised when all fallback options have been tried."""


class FallbackDecider:
    """
    Decides whether and how to fall back after a provider failure.

    Usage:
        decider = FallbackDecider(config.fallback)
        if decider.should_fallback(error, provider_config):
            next_provider, next_cfg, next_model = decider.next_option(failed, all_providers)
    """

    def __init__(self, config: FallbackConfig) -> None:
        self._config = config

    def should_fallback(
        self,
        error: Exception,
        provider_cfg: ProviderConfig,
    ) -> bool:
        """
        Return True if we should attempt a fallback for this error.

        Never falls back on InvalidImageError (image-side issue, not provider issue).
        """
        if isinstance(error, InvalidImageError):
            return False

        mode = self._config.mode
        if mode == "disabled":
            return False
        if mode == "auto":
            category = _categorise(error)
            return category in self._config.auto_on_errors
        if mode == "llm-prompt":
            return self._ask_llm(error, provider_cfg)
        return False

    def next_option(
        self,
        failed_cfg: ProviderConfig,
        all_providers: list[ProviderConfig],
        failed_model: str,
    ) -> tuple[ProviderConfig, str]:
        """
        Return (provider_config, model) for the next fallback option.

        Tries in order:
          1. fallback_model on the same provider
          2. priority_model on the next enabled provider
          3. fallback_model on the next enabled provider

        Raises FallbackExhaustedError if nothing is available.
        """
        # 1. Fallback model on same provider
        if failed_cfg.fallback_model and failed_model != failed_cfg.fallback_model:
            return failed_cfg, failed_cfg.fallback_model

        # 2 + 3. Try next providers in order
        found_current = False
        for pcfg in all_providers:
            if not pcfg.enabled:
                continue
            if not found_current:
                if pcfg.name == failed_cfg.name:
                    found_current = True
                continue
            # Next provider after failed one
            return pcfg, pcfg.priority_model

        # Also try fallback_model on subsequent providers
        found_current = False
        for pcfg in all_providers:
            if not pcfg.enabled:
                continue
            if not found_current:
                if pcfg.name == failed_cfg.name:
                    found_current = True
                continue
            if pcfg.fallback_model:
                return pcfg, pcfg.fallback_model

        raise FallbackExhaustedError(
            f"All fallback options exhausted. "
            f"Last error from provider '{failed_cfg.name}' / model '{failed_model}'"
        )

    def _ask_llm(self, error: Exception, provider_cfg: ProviderConfig) -> bool:
        """
        Ask an LLM whether to fall back (llm-prompt mode).

        Uses the first available text provider. If no LLM is reachable,
        falls back to auto-mode behaviour.
        """
        import os

        task_context = os.environ.get("AGENTIC_VISION_TASK_CONTEXT", "image analysis task")

        decision_prompt = (
            f"Provider '{provider_cfg.name}' failed with: {_categorise(error)}: "
            f"{str(error)[:100]}\n"
            f"Task context: {task_context[:200]}\n"
            f"Fallback available: {provider_cfg.fallback_model or 'next provider'}\n"
            "Should we use the fallback? Reply with ONLY 'yes' or 'no'.\n"
            "Prefer 'yes' for rate limits and transient errors. "
            "Prefer 'no' if accuracy is critical and fallback is a weaker model."
        )

        try:
            answer = self._call_llm_for_decision(decision_prompt)
            return answer.strip().lower().startswith("y")
        except Exception:
            # LLM unavailable — fall through to auto-mode
            category = _categorise(error)
            return category in self._config.auto_on_errors

    @staticmethod
    def _call_llm_for_decision(prompt: str) -> str:
        """Call any available LLM for a yes/no decision. Returns the response text."""
        import os

        # Try Anthropic first (most likely to be configured as fallback decider)
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            import anthropic

            client = anthropic.Anthropic(api_key=anthropic_key)
            message = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=5,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text  # type: ignore[union-attr,no-any-return]

        # Try Gemini API key
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            import google.generativeai as genai

            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            return response.text or "no"

        raise RuntimeError("No LLM available for fallback decision")
