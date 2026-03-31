---
name: agentic-vision
description: Analyse local image files using Gemini, OpenAI, Anthropic, or local LLM vision models.
  Saves a full markdown report to ./image-analyses/ and returns ONLY a summary and file path to
  keep image bytes completely out of Claude's context.

  TRIGGER when:
  - User asks to "analyse", "describe", "inspect", or "review" an image or screenshot
  - A tool (chrome-devtools, screenshot MCP, etc.) has produced an image file that needs interpretation
  - User references a local image path (PNG, JPEG, WEBP, GIF)
  - You have captured a screenshot and need to interpret its contents

  DO NOT TRIGGER when:
  - The image has already been pasted into context (Claude can see it directly)
  - The task is to edit or generate an image (not analyse one)
---

# agentic-vision

Delegates vision analysis to external models (Gemini, OpenAI, Claude, local LLMs).
Image bytes never enter this context — only a ≤300-token summary and a file path are returned.

## Step 1 — Pre-flight check (ALWAYS run first)

```bash
uv run agentic-vision precheck --json
```

Parse the JSON. If `status != "ok"`, report the failed checks and their `actionable` hints to the user.
Do NOT proceed to analysis if a hard dependency (python, auth) is missing.

If the package is not installed:
```bash
cd /path/to/agentic-image-analyser && uv sync
```

## Step 2 — Resolve image paths

- Require **absolute paths** to existing files. Relative paths: resolve with `realpath`.
- Supported formats: PNG, JPEG, WEBP, GIF.
- Do NOT attempt to paste or read image bytes into this context.

## Step 3 — Run analysis

### Single image
```bash
uv run agentic-vision analyze \
  --image /absolute/path/to/image.png \
  --json
```

### Multiple images (batch)
```bash
uv run agentic-vision analyze \
  --image /path/img1.png /path/img2.png /path/img3.png \
  --json
```

### With a custom prompt
```bash
uv run agentic-vision analyze \
  --image /path/screenshot.png \
  --prompt "Identify all form elements, their labels, and any validation errors visible." \
  --json
```

### Force a specific provider or model
```bash
uv run agentic-vision analyze \
  --image /path/img.png \
  --provider gemini-oauth \
  --model gemini-2.5-flash \
  --json
```

## Step 4 — Parse the output

The command writes JSON to stdout:
```json
{
  "status": "success",
  "results": [
    {
      "image_path": "/abs/path/img.png",
      "analysis_file": "./image-analyses/2026-03-31/img_a1b2c3d4.md",
      "summary": "The screenshot shows a login form with...",
      "provider": "gemini-oauth",
      "model": "gemini-2.5-pro",
      "duration_seconds": 3.7,
      "status": "success"
    }
  ],
  "error": null
}
```

## Step 5 — What to return to the user

RETURN:
  - `results[N].summary` (already ≤300 tokens)
  - `results[N].analysis_file` path for full details

DO NOT:
  - Read the full markdown analysis file into context (defeats the purpose)
  - Paste image bytes or base64 data
  - Return more than the summary + file path unless the user asks for more detail

If the user explicitly wants more detail: `Read` the analysis_file, but summarise the relevant section rather than dumping the whole file.

## Error handling

| Exit code | Meaning | Action |
|---|---|---|
| 0 | All images succeeded | Return summaries |
| 1 | Partial success | Report which images failed; return summaries for succeeded ones |
| 2 | All failed | Report errors; suggest `auth-check` or `list-models` |
| 3 | Auth / config error | Run `agentic-vision auth-check --json` and guide user to fix |

### Auth troubleshooting
```bash
# Check all auth methods
uv run agentic-vision auth-check --json --pretty

# List available models per provider
uv run agentic-vision list-models --json --pretty

# If OAuth token expired: re-authenticate
gemini auth login
```

## Fallback behaviour

If `agentic-vision.toml` is configured with `fallback.mode = "llm-prompt"`, the engine
will print a decision request. In this mode, you (Claude) should decide:
- **Yes, use fallback** if: the task is time-sensitive, accuracy difference is small, or the
  failure is transient (rate limit, timeout)
- **No, don't fallback** if: accuracy is critical and the fallback is a significantly weaker model

Set `AGENTIC_VISION_TASK_CONTEXT` in the environment before running for context-aware decisions:
```bash
export AGENTIC_VISION_TASK_CONTEXT="design review requiring pixel-accurate analysis"
uv run agentic-vision analyze --image /path/img.png --json
```

## Output file location

Reports are saved to `./image-analyses/YYYY-MM-DD/<stem>_<hash>.md` relative to the project root.
Each file contains YAML frontmatter, a summary, the full analysis, and metadata (dimensions, size, duration).

## Configuration (optional)

Copy `agentic-vision.toml.example` → `agentic-vision.toml` to customise providers, models,
rate limits, output directory, and fallback behaviour. Secrets go in `.env` (see `.env.example`).
