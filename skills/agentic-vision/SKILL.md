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

## Step 0 — Bootstrap (run once per machine)

Check if the CLI is available:
```bash
agentic-vision --version 2>/dev/null || echo "NOT_INSTALLED"
```

If `NOT_INSTALLED`, install globally:
```bash
uv tool install "agentic-vision @ git+https://github.com/ibaou-dev/agentic-image-analyser@feat/productize-skill"
```

If `uv` itself is missing:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# then reload shell or: export PATH="$HOME/.local/bin:$PATH"
```

Alternatively, run the bootstrap script (idempotent — safe to run multiple times):
```bash
bash .agents/skills/agentic-vision/scripts/bootstrap.sh
```

After install, verify: `agentic-vision precheck --json`

## Step 1 — Pre-flight check (ALWAYS run first)

```bash
agentic-vision precheck --json
```

Parse the JSON. If `status != "ok"`, report the failed checks and their `actionable` hints.
Do NOT proceed to analysis if a hard dependency (python, auth) is missing.

### If no auth is configured

Run the interactive OAuth login (no Gemini CLI required):
```bash
agentic-vision login
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
agentic-vision analyze \
  --image /absolute/path/to/image.png \
  --json
```

### Multiple images (batch)
```bash
agentic-vision analyze \
  --image /path/img1.png /path/img2.png /path/img3.png \
  --json
```

### With a custom prompt
```bash
agentic-vision analyze \
  --image /path/screenshot.png \
  --prompt "Identify all form elements, their labels, and any validation errors visible." \
  --json
```

### Force a specific provider or model
```bash
agentic-vision analyze \
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
      "analysis_file": "./image-analyses/2026-04-01/img_a1b2c3d4.md",
      "summary": "The screenshot shows a login form with...",
      "provider": "gemini-oauth",
      "model": "gemini-3-flash-preview",
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
| 2 | All failed | Report errors; suggest `auth-check` or `list-models` |
| 3 | Auth / config error | Run `agentic-vision auth-check --json` and guide user to fix |

### Auth troubleshooting
```bash
# Check all auth methods
agentic-vision auth-check --json --pretty

# List available models per provider
agentic-vision list-models --json --pretty

# Re-authenticate
agentic-vision login
```

## Configuration (optional — not required for basic use)

Default providers are built-in: gemini-oauth (gemini-3-flash-preview → gemini-2.5-flash fallback)
then gemini-api, based on which credentials are present.

To customise providers, output directory, rate limits, or fallback behaviour:
```bash
# Create a config in the current project directory
agentic-vision init-config

# Or create a global user-level config
agentic-vision init-config --global
```

Edit the resulting `agentic-vision.toml` as needed.
Full reference: https://github.com/ibaou-dev/agentic-image-analyser/blob/main/agentic-vision.toml.example

## Optional: MCP server

For tighter Claude Code integration (native tool calls instead of Bash):

```bash
# Install with MCP extras
uv tool install "agentic-vision[mcp] @ git+https://github.com/ibaou-dev/agentic-image-analyser"

# Add to Claude Code MCP config:
# {
#   "mcpServers": {
#     "agentic-vision": { "command": "agentic-vision-mcp" }
#   }
# }
```
