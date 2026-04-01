"""
Configuration loading and validation for agentic-vision.

Two layers:
  - EnvSettings: secrets / env vars loaded from .env (via pydantic-settings)
  - AppConfig:   structured non-secret config loaded from agentic-vision.toml

Usage:
    from agentic_vision.config import load_config
    cfg = load_config()  # auto-discovers config files
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ─── Config file discovery ─────────────────────────────────────────────────────
_CONFIG_FILENAME = "agentic-vision.toml"
_ENV_FILENAME = ".env"


# Ordered search paths: project root first, then user home
def _find_config_file(name: str) -> Path | None:
    cwd = Path.cwd()
    candidates = [cwd / name, Path.home() / ".config" / "agentic-vision" / name]
    for p in candidates:
        if p.exists():
            return p
    return None


# ─── Environment / secrets ────────────────────────────────────────────────────
class EnvSettings(BaseSettings):
    """Loaded from environment variables and/or .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_find_config_file(_ENV_FILENAME) or _ENV_FILENAME),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google / Gemini
    google_cloud_project: str | None = Field(
        default=None,
        description="GCP project ID for Code Assist endpoint (also read from GOOGLE_CLOUD_PROJECT)",
    )
    gemini_oauth_creds_path: str = Field(
        default="~/.gemini/oauth_creds.json",
        description="Path to Gemini CLI OAuth credentials file",
    )
    gemini_api_key: str | None = Field(default=None)

    # OAuth client credentials (auto-extracted from Gemini CLI if not set)
    gemini_cli_oauth_client_id: str | None = Field(default=None)
    gemini_cli_oauth_client_secret: str | None = Field(default=None)

    # OpenAI-compatible
    openai_api_key: str | None = Field(default=None)
    openai_base_url: str | None = Field(default=None)

    # Anthropic
    anthropic_api_key: str | None = Field(default=None)

    # Development
    agentic_vision_integration_test: bool = Field(default=False)
    agentic_vision_debug: bool = Field(default=False)

    @property
    def oauth_creds_path(self) -> Path:
        return Path(self.gemini_oauth_creds_path).expanduser()


# ─── Structured config (TOML) ─────────────────────────────────────────────────
class OutputConfig(BaseModel):
    base_dir: str = Field(
        default="./image-analyses",
        description="Directory where analysis reports are saved",
    )
    summary_max_tokens: Annotated[int, Field(ge=50, le=2000)] = 300

    @property
    def base_path(self) -> Path:
        return Path(self.base_dir)


class FallbackConfig(BaseModel):
    mode: Literal["auto", "llm-prompt", "disabled"] = "auto"
    auto_on_errors: list[str] = Field(
        default_factory=lambda: ["rate_limit", "auth_failure", "model_unavailable", "timeout"]
    )


class BackoffConfig(BaseModel):
    """Retry-with-backoff settings applied before falling back to a secondary provider."""

    enabled: bool = True
    delays: list[Annotated[float, Field(ge=0.0)]] = Field(
        default_factory=lambda: [5.0, 15.0, 30.0],
        description="Seconds to wait between successive retries (3 attempts by default)",
    )
    respect_retry_after: bool = Field(
        default=True,
        description="Honour the Retry-After value returned by the API when present",
    )
    max_retry_after: Annotated[float, Field(ge=1.0, le=300.0)] = Field(
        default=60.0,
        description="Cap on the API-provided Retry-After value to prevent indefinite waits",
    )


class ProviderConfig(BaseModel):
    name: Literal["gemini-oauth", "gemini-api", "openai", "anthropic"] | str
    priority_model: str
    fallback_model: str | None = None
    rate_limit_rpm: Annotated[int, Field(ge=1, le=10_000)] = 60
    rate_limit_tpm: Annotated[int, Field(ge=1_000, le=10_000_000)] = 250_000
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Provider name must not be empty")
        return v.strip()


class PromptsConfig(BaseModel):
    default_ui_analysis: str = (
        "Analyse this screenshot and report:\n"
        "1. Layout structure and visual hierarchy\n"
        "2. UI components present (buttons, forms, navigation, cards, etc.)\n"
        "3. Colour scheme and typography observations\n"
        "4. Visual anomalies, misalignments, or rendering issues\n"
        "5. Mobile/responsive design indicators\n"
        "6. Key content areas and their apparent purpose\n\n"
        "Be specific and concise. Focus on what is visually observable."
    )
    default_generic: str = "Describe this image in detail, noting key elements, visible text, and any technical content."


def _default_providers() -> list[ProviderConfig]:
    """
    Built-in provider list used when no agentic-vision.toml is present (or [[providers]] omitted).
    Mirrors agentic-vision.toml.example exactly.
    gemini-oauth is first (free-tier OAuth, no API key needed).
    gemini-api is second (requires GEMINI_API_KEY).
    """
    return [
        ProviderConfig(
            name="gemini-oauth",
            priority_model="gemini-3-flash-preview",
            fallback_model="gemini-2.5-flash",
        ),
        ProviderConfig(
            name="gemini-api",
            priority_model="gemini-2.5-pro",
            fallback_model="gemini-2.5-flash",
        ),
    ]


class AppConfig(BaseModel):
    """Loaded from agentic-vision.toml."""

    output: OutputConfig = Field(default_factory=OutputConfig)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)
    backoff: BackoffConfig = Field(default_factory=BackoffConfig)
    providers: list[ProviderConfig] = Field(default_factory=_default_providers)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)

    @model_validator(mode="after")
    def validate_providers(self) -> AppConfig:
        if not self.providers:
            # TOML was loaded but [[providers]] was omitted entirely — apply defaults
            self.providers = _default_providers()
        names = [p.name for p in self.providers]
        if len(names) != len(set(names)):
            raise ValueError("Provider names must be unique")
        return self

    def get_provider(self, name: str) -> ProviderConfig | None:
        return next((p for p in self.providers if p.name == name), None)

    def enabled_providers(self) -> list[ProviderConfig]:
        return [p for p in self.providers if p.enabled]


# ─── Combined config ───────────────────────────────────────────────────────────
class Config:
    """Combined config: structured TOML + env/secrets."""

    def __init__(self, app: AppConfig, env: EnvSettings) -> None:
        self.app = app
        self.env = env

    @property
    def output(self) -> OutputConfig:
        return self.app.output

    @property
    def fallback(self) -> FallbackConfig:
        return self.app.fallback

    @property
    def backoff(self) -> BackoffConfig:
        return self.app.backoff

    @property
    def providers(self) -> list[ProviderConfig]:
        return self.app.providers

    @property
    def prompts(self) -> PromptsConfig:
        return self.app.prompts

    def enabled_providers(self) -> list[ProviderConfig]:
        return self.app.enabled_providers()


# ─── Loaders ─────────────────────────────────────────────────────────────────
def load_app_config(path: Path | None = None) -> AppConfig:
    """Load and validate agentic-vision.toml. Returns defaults if not found."""
    toml_path = path or _find_config_file(_CONFIG_FILENAME)
    if toml_path is None or not toml_path.exists():
        return AppConfig()
    with toml_path.open("rb") as f:
        data = tomllib.load(f)
    return AppConfig.model_validate(data)


def load_env_settings() -> EnvSettings:
    """Load environment variables + .env file."""
    return EnvSettings()


def load_config(toml_path: Path | None = None) -> Config:
    """Load full config (TOML + env). Primary entry point."""
    return Config(
        app=load_app_config(toml_path),
        env=load_env_settings(),
    )


# ─── Schema export ────────────────────────────────────────────────────────────
def export_json_schema() -> str:
    """Generate JSON Schema from AppConfig (for IDE autocompletion of TOML)."""
    schema = AppConfig.model_json_schema()
    return json.dumps(schema, indent=2)
