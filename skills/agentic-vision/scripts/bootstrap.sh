#!/usr/bin/env bash
# bootstrap.sh — idempotent install of agentic-vision for Claude Code skill
#
# Usage: bash .agents/skills/agentic-vision/scripts/bootstrap.sh
#
# Safe to run multiple times. Upgrades if already installed.
# Ends with `agentic-vision precheck --json` so Claude can check status in one shot.
set -euo pipefail

REPO_URL="https://github.com/ibaou-dev/agentic-image-analyser"
BRANCH="feat/productize-skill"
PACKAGE="agentic-vision @ git+${REPO_URL}@${BRANCH}"

# ── 1. Ensure uv is available ─────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    echo "uv not found — installing..." >&2
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # uv installs to ~/.local/bin or ~/.cargo/bin — add to PATH for this script
    export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
fi

if ! command -v uv &>/dev/null; then
    echo '{"status":"error","error":"uv install failed — please install manually: https://docs.astral.sh/uv/"}' >&2
    exit 1
fi

# ── 2. Install or upgrade agentic-vision ──────────────────────────────────────
if command -v agentic-vision &>/dev/null; then
    echo "agentic-vision already installed ($(agentic-vision --version)) — upgrading..." >&2
    uv tool upgrade agentic-vision 2>/dev/null || true
else
    echo "Installing agentic-vision from GitHub..." >&2
    uv tool install "${PACKAGE}"
fi

# ── 3. Run precheck — output is what Claude reads ────────────────────────────
agentic-vision precheck --json
