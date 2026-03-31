# agentic-vision

Provider-agnostic image analysis delegation for Claude Code. Keeps image bytes out of Claude's context by delegating vision tasks to Gemini, OpenAI, Anthropic, or local LLMs — returning only a text summary (~300 tokens) and a file path. Typical context saving: **~7× per image**.

---

## Quick Start

```bash
# Install
uv sync

# Verify auth works (run before first use)
uv run python scripts/verify_auth.py

# Analyse an image
uv run agentic-vision analyze --image /path/to/screenshot.png --json

# Pre-flight check (run before analysing)
uv run agentic-vision precheck
```

---

## Auth Priority Chain

| Priority | Method | Setup |
|---|---|---|
| 1 | **Gemini CLI OAuth** | `gemini auth login` → `~/.gemini/oauth_creds.json` |
| 2 | **Gemini API Key** | `GEMINI_API_KEY=AIza...` in `.env` |
| 3 | **OpenAI-compatible** | `OPENAI_API_KEY=sk-...` in `.env` |
| 4 | **Anthropic** | `ANTHROPIC_API_KEY=sk-ant-...` in `.env` |

Copy `.env.example` → `.env` and fill in the relevant key(s).

---

## Configuration

### `.env` (secrets — gitignored)
```bash
cp .env.example .env
# Edit .env with your credentials
```

### `agentic-vision.toml` (non-secret settings — gitignored)
```bash
cp agentic-vision.toml.example agentic-vision.toml
# Customise providers, rate limits, fallback behaviour
```

IDE autocompletion is available via `agentic-vision.schema.json`. Point your editor at it:
```json
// In VS Code settings.json:
{
  "evenBetterToml.schema.associations": {
    "agentic-vision.toml": "./agentic-vision.schema.json"
  }
}
```

To regenerate the schema after config changes:
```bash
uv run agentic-vision export-schema > agentic-vision.schema.json
```

---

## CLI Reference

```bash
# Analyse images (JSON output for scripting)
uv run agentic-vision analyze \
  --image /path/img1.png /path/img2.png \
  --prompt "Describe the UI layout" \
  --provider gemini-oauth \
  --model gemini-2.5-pro \
  --json

# Pre-flight check
uv run agentic-vision precheck [--json]

# Auth diagnostics
uv run agentic-vision auth-check [--json] [--pretty]

# List available models
uv run agentic-vision list-models [--json] [--pretty]

# Check rate limit quotas
uv run agentic-vision check-quota [--json]

# Export config JSON schema
uv run agentic-vision export-schema
```

### Exit codes

| Code | Meaning |
|---|---|
| 0 | All images succeeded |
| 1 | Partial success (some images failed) |
| 2 | All images failed |
| 3 | Auth / config error |

---

## Output

Reports are saved to `./image-analyses/YYYY-MM-DD/<stem>_<hash8>.md`:

```markdown
---
image: /abs/path/screenshot.png
provider: gemini-oauth
model: gemini-2.5-pro
analyzed_at: 2026-03-31T14:23:00Z
prompt: "Describe the UI layout"
---

# Image Analysis: screenshot.png

## Summary
<≤300 tokens — this is what gets returned to the caller>

## Full Analysis
<complete model response>

## Metadata
- Dimensions: 1920×1080 | Size: 234 KB | Duration: 4.2s
```

---

## Claude Code Skill

The `skills/agentic-vision/SKILL.md` skill lets Claude delegate image analysis automatically:

1. Claude runs `uv run agentic-vision precheck --json` (aborts on failure)
2. Resolves absolute image paths
3. Runs `uv run agentic-vision analyze --image <paths> --json`
4. Returns only the `summary` + `analysis_file` path — **image bytes never enter Claude's context**

### Trigger conditions (Claude invokes the skill when)
- User asks to "analyse", "describe", or "review" an image file
- A tool (screenshot MCP, chrome-devtools) has produced an image file
- User references a local image path

---

## MCP Server

```bash
# Run the MCP server (requires: uv add 'agentic-vision[mcp]')
uv run python mcp/server.py
```

Available MCP tools:
- `analyze_image(image_path, prompt?, provider?, model?)`
- `analyze_images_batch(image_paths, prompt?, provider?, model?)`
- `list_models(provider?)`
- `check_quota(provider?)`

Client config example (Claude Desktop / Claude Code):
```json
{
  "mcpServers": {
    "agentic-vision": {
      "command": "uv",
      "args": ["run", "python", "mcp/server.py"],
      "cwd": "/path/to/agentic-image-analyser"
    }
  }
}
```

---

## Fallback Behaviour

Three modes (`agentic-vision.toml → [fallback] mode`):

| Mode | Behaviour |
|---|---|
| `auto` | Falls back immediately on rate limits, auth failures, timeouts |
| `llm-prompt` | Asks an LLM (Anthropic/Gemini) for a yes/no decision |
| `disabled` | Never falls back — surface the error immediately |

Fallback order: `fallback_model` on same provider → `priority_model` on next provider → `fallback_model` on next provider → error.

Never falls back on `InvalidImageError` (image-side problem, not provider-side).

---

## Development

```bash
# Install with dev deps
uv sync --dev

# Install pre-commit hooks
pre-commit install

# Run unit tests
uv run pytest tests/unit -v --cov=src

# Run integration tests (requires valid credentials)
AGENTIC_VISION_INTEGRATION_TEST=1 uv run pytest tests/integration -v

# Lint + type check
uv run ruff check src tests
uv run mypy src

# Run all pre-commit hooks
pre-commit run --all-files
```

### Commit format (Conventional Commits)
```
feat(auth): add gemini oauth token refresh
fix(engine): handle empty response parts from thinking models
test(fallback): add coverage for llm-prompt mode
docs(readme): add mcp server setup instructions
```

---

## Supported Providers

| Provider | Name | Models | Auth |
|---|---|---|---|
| Gemini CLI (OAuth) | `gemini-oauth` | gemini-2.5-pro, gemini-2.5-flash | `~/.gemini/oauth_creds.json` |
| Gemini API | `gemini-api` | gemini-2.5-pro, gemini-2.5-flash, etc. | `GEMINI_API_KEY` |
| OpenAI-compatible | `openai` | gpt-4o, gpt-4-turbo, custom | `OPENAI_API_KEY` + `OPENAI_BASE_URL` |
| Anthropic | `anthropic` | claude-3.5-sonnet, claude-opus-4, etc. | `ANTHROPIC_API_KEY` |
