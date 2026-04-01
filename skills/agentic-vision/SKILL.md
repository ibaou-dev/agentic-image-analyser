---
name: agentic-vision
description:
  "Analyses local image files (PNG, JPEG, WEBP, GIF) using Gemini via the Code
  Assist endpoint — no API key needed, uses existing Gemini CLI OAuth credentials.
  Saves a full markdown report to ./image-analyses/ and returns ONLY a summary
  and file path, keeping image bytes completely out of Claude's context (~7x
  context savings per image). Use this skill when asked to analyse, describe,
  inspect, or review a local image or screenshot, or when a tool (chrome-devtools,
  screenshot MCP, etc.) has produced an image file that needs interpretation.
  Do NOT trigger when the image is already pasted into context or when the task
  is to edit or generate an image."
user-invocable: false
license: MIT
compatibility:
  Designed for Claude Code. Requires uv and Gemini CLI OAuth credentials
  (~/.gemini/oauth_creds.json). Works on Linux, macOS, WSL2.
metadata:
  author: ibaou-dev
  version: "1.0.1"
  openclaw:
    emoji: "🔍"
    homepage: https://github.com/ibaou-dev/agentic-image-analyser
    requires:
      bins:
        - uv
        - python3
    install: []
allowed-tools: Bash(uv:*) Bash(python3:*) Read
---

# agentic-vision

Delegates vision analysis to Gemini via the Code Assist endpoint.
Image bytes never enter this context — only a ≤300-token summary and a file path are returned.

The analysis script ships inside the skill directory — no package installation required.
`uv run` installs the single dependency (httpx) in a cached venv on first use (~2s).

> **Privacy note:** images are transmitted to Google's Gemini API (Code Assist endpoint).
> The default provider uses your existing Gemini CLI OAuth credentials.

## Installing this skill

```bash
npx skills add ibaou-dev/agentic-image-analyser --agent claude-code
```

This copies the skill files into your project's `.agents/skills/agentic-vision/` directory,
including the `scripts/` subdirectory that contains the analysis scripts.

Alternatively, install manually:
```bash
mkdir -p .agents/skills/agentic-vision/scripts
curl -fsSL https://raw.githubusercontent.com/ibaou-dev/agentic-image-analyser/main/skills/agentic-vision/SKILL.md \
  -o .agents/skills/agentic-vision/SKILL.md
curl -fsSL https://raw.githubusercontent.com/ibaou-dev/agentic-image-analyser/main/skills/agentic-vision/scripts/analyze.py \
  -o .agents/skills/agentic-vision/scripts/analyze.py
curl -fsSL https://raw.githubusercontent.com/ibaou-dev/agentic-image-analyser/main/skills/agentic-vision/scripts/precheck.py \
  -o .agents/skills/agentic-vision/scripts/precheck.py
```

## Step 0 — Bootstrap (run once per machine)

Check that `uv` is available:
```bash
uv --version 2>/dev/null || echo "NOT_INSTALLED"
```

If `NOT_INSTALLED`, the user must install uv first:
```
Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh
(see https://docs.astral.sh/uv/)
```

Do NOT run this curl command yourself — ask the user to run it.

Alternatively, run the bootstrap script (checks uv + auth in one shot):
```bash
bash .agents/skills/agentic-vision/scripts/bootstrap.sh
```

## Step 1 — Pre-flight check (ALWAYS run first)

```bash
python3 .agents/skills/agentic-vision/scripts/precheck.py --json
```

Parse the JSON. If `status != "ok"`, report the failed checks and their `actionable` hints.
Do NOT proceed to analysis if a check fails.

### If no auth is configured

Run the interactive OAuth login:
```bash
agentic-vision login
```

If `agentic-vision` is not installed, use the Gemini CLI directly:
```bash
gemini auth login
```

This opens a browser (or prints a URL for WSL/SSH) and stores credentials at `~/.gemini/oauth_creds.json`.

For WSL2: the command prints a URL — open it in your Windows browser, complete sign-in,
then paste the redirect URL or auth code back into the terminal.

## Step 2 — Resolve image paths

- Require **absolute paths** to existing files. Relative paths: resolve with `realpath`.
- Supported formats: PNG, JPEG, WEBP, GIF.
- Do NOT attempt to paste or read image bytes into this context.

## Step 3 — Run analysis

### Single image
```bash
uv run .agents/skills/agentic-vision/scripts/analyze.py \
  --image /absolute/path/to/image.png \
  --json
```

### Multiple images (batch)
```bash
uv run .agents/skills/agentic-vision/scripts/analyze.py \
  --image /path/img1.png /path/img2.png /path/img3.png \
  --json
```

### With a custom prompt
```bash
uv run .agents/skills/agentic-vision/scripts/analyze.py \
  --image /path/screenshot.png \
  --prompt "Identify all form elements, their labels, and any validation errors visible." \
  --json
```

### With a specific model
```bash
uv run .agents/skills/agentic-vision/scripts/analyze.py \
  --image /path/img.png \
  --model gemini-2.5-pro \
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
      "analysis_file": "./image-analyses/2026-04-01/img_a1b2c3d4.md",
      "summary": "The screenshot shows a login form with...",
      "provider": "gemini-oauth",
      "model": "gemini-2.5-flash",
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

If the user explicitly wants more detail: `Read` the analysis_file, but summarise the
relevant section rather than dumping the whole file.

## Error handling

| Exit code | Meaning | Action |
|---|---|---|
| 0 | All images succeeded | Return summaries |
| 1 | Partial success | Report which images failed; return summaries for succeeded ones |
| 2 | All failed | Report errors; check auth with precheck.py |

### Auth troubleshooting
```bash
# Re-run precheck
python3 .agents/skills/agentic-vision/scripts/precheck.py --json

# Re-authenticate
agentic-vision login
# OR (if agentic-vision package not installed):
gemini auth login
```

## Optional: full package for advanced use

The `agentic-vision` CLI package provides additional providers (OpenAI, Anthropic, local LLMs),
an MCP server, and auth management commands:

```bash
uv tool install "agentic-vision @ git+https://github.com/ibaou-dev/agentic-image-analyser@v1.0.1"
```

After install:
```bash
agentic-vision auth-check --json      # check all auth methods
agentic-vision list-models --json     # list models per provider
agentic-vision login                  # re-authenticate with Gemini
```

To use a local LLM (fully on-device, no data leaves your machine):
```bash
agentic-vision init-config
# Edit agentic-vision.toml: set provider = "openai" pointing to Ollama/LM Studio
```
