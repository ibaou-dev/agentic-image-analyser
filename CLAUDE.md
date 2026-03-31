# agentic-vision — Claude Code Session Context

> This file persists context across Claude Code sessions. Keep it accurate.

## What this project does

Delegates image/screenshot analysis to external vision models (Gemini, OpenAI, Anthropic, local LLMs), keeping image bytes **out of Claude's context**. Returns only a text summary + file path, achieving ~7× context savings per image.

**Primary use case**: ad-hoc or automated analysis of local image files
**Secondary use case**: complement chrome-devtools MCP for website screenshot pipelines

## Package

- **Python package**: `agentic_vision` (in `src/`)
- **CLI entry point**: `agentic-vision` (via `uv run agentic-vision`)
- **Output dir**: `./image-analyses/YYYY-MM-DD/` (gitignored)

## Tech stack

| Tool | Purpose |
|---|---|
| `uv` | Package manager, venv, run tasks |
| `pydantic` + `pydantic-settings` | Config validation + .env loading |
| `httpx` | HTTP client (Code Assist raw HTTP) |
| `ruff` | Lint + format |
| `mypy --strict` | Type checking |
| `pytest` + `pytest-cov` | Tests (≥80% coverage target) |
| `pre-commit` | Hook runner |
| `commitizen` | Conventional Commits enforcement |

## Key commands

```bash
# Install deps (creates .venv automatically)
uv sync --dev

# Install pre-commit hooks (do once after uv sync)
uv run pre-commit install --hook-type commit-msg --hook-type pre-push

# Run unit tests
uv run pytest tests/unit -v

# Run integration tests (requires real credentials + network)
AGENTIC_VISION_INTEGRATION_TEST=1 uv run pytest tests/integration -v

# Lint + format
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/

# Type check
uv run mypy src/

# CLI
uv run agentic-vision precheck
uv run agentic-vision auth-check --json
uv run agentic-vision analyze --image /path/to/image.png --json

# Verify auth endpoints (Phase 0 script)
uv run python scripts/verify_auth.py
uv run python scripts/verify_auth.py --vision /path/to/test.png
```

## Auth priority chain

1. **Gemini CLI OAuth** — `~/.gemini/oauth_creds.json` (fields: `access_token`, `refresh_token`, `expiry_date` ms-epoch). 60s refresh buffer. Client credentials auto-extracted from Gemini CLI install.
2. **Code Assist / Antigravity** — `GOOGLE_CLOUD_PROJECT` env var (value: `geminicli-466113`). Endpoint: `POST https://cloudcode-pa.googleapis.com/v1internal:generateContent`. Request wrapper: `{model, project, request: {contents: [...]}}`.
3. **Gemini API Key** — `GEMINI_API_KEY` env var → `google-generativeai` SDK.
4. **OpenAI-compatible** — `OPENAI_API_KEY` + `OPENAI_BASE_URL` → `openai` SDK.
5. **Anthropic** — `ANTHROPIC_API_KEY` → `anthropic` SDK.

## Config files

| File | Purpose | Gitignored? |
|---|---|---|
| `.env` | Secrets (API keys, project ID) | Yes |
| `.env.example` | Template for .env | No |
| `agentic-vision.toml` | Structured config (providers, output, fallback) | Yes |
| `agentic-vision.toml.example` | Template for toml config | No |
| `agentic-vision.schema.json` | JSON Schema (generated from Pydantic) | No |

## Environment

- **GOOGLE_CLOUD_PROJECT=geminicli-466113** is set in the user's zshrc — always available
- `~/.gemini/oauth_creds.json` exists with valid tokens
- `~/.gemini/projects.json` maps workspace paths to project names
- WSL2 environment — OAuth browser redirects may need manual copy-paste
- Python 3.14.2 installed (satisfies >=3.12 requirement)

## Commit format (Conventional Commits)

```
type(scope): description

Types: feat | fix | test | refactor | docs | chore | ci
Examples:
  feat(auth): add gemini oauth token refresh
  fix(providers): handle 429 rate limit in code assist provider
  test(unit): add token bucket exhaustion tests
  chore(deps): bump httpx to 0.28
```

## Testing discipline

- Write unit tests **before** moving to the next phase
- Unit tests: no API calls, no network — mock all external I/O
- Integration tests: gated by `AGENTIC_VISION_INTEGRATION_TEST=1`
- Pre-push hook runs unit tests automatically

## .inspiration/ directory

Contains reference opencode plugins (`opencode-gemini-auth`, `opencode-antigravity-auth`).
**Gitignored. Read-only. Do not modify.**
Used to understand: OAuth flow, Code Assist endpoint format, token refresh patterns, rate-limit retry logic.

## Module map

```
src/agentic_vision/
├── config.py          — Pydantic AppConfig + EnvSettings, TOML loader, schema export
├── rate_limiter.py    — TokenBucket (RPM + TPM, thread-safe)
├── output.py          — Markdown report writer + summary truncator
├── engine.py          — AnalysisEngine: orchestrates auth+provider+fallback+rate-limit
├── fallback.py        — FallbackDecider: auto / llm-prompt / disabled
├── precheck.py        — Dependency checker for skill entry point
├── cli.py             — argparse CLI: analyze, batch, list-models, check-quota, auth-check, precheck
├── auth/
│   ├── base.py        — AuthProvider ABC
│   ├── gemini_oauth.py — Gemini CLI OAuth (PRIMARY)
│   ├── code_assist.py — Google project ID discovery
│   ├── gemini_api_key.py
│   ├── openai_compat.py
│   ├── anthropic_api.py
│   └── resolver.py    — Priority chain
└── providers/
    ├── base.py        — VisionProvider ABC + ModelInfo + AnalysisResult
    ├── code_assist.py — Raw HTTP (Code Assist endpoint)
    ├── gemini_direct.py — google-generativeai SDK
    ├── openai_compat.py — openai SDK
    └── anthropic.py   — anthropic SDK
```
