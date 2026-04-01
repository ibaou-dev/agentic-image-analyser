#!/usr/bin/env bash
# bootstrap.sh — idempotent install of agentic-vision for Claude Code skill
#
# Usage: bash .agents/skills/agentic-vision/scripts/bootstrap.sh
#
# Safe to run multiple times. Upgrades if already installed.
# Ends with `agentic-vision precheck --json` so Claude can check status in one shot.
set -euo pipefail

REPO_URL="https://github.com/ibaou-dev/agentic-image-analyser"
TAG="v1.0.0"
PACKAGE="agentic-vision @ git+${REPO_URL}@${TAG}"

# ── 1. Ensure uv is available ─────────────────────────────────────────────────
# uv is a prerequisite — install it manually if missing rather than running
# an unattended curl|sh.  This keeps the user in control of that decision.
if ! command -v uv &>/dev/null; then
    echo '{"status":"error","error":"uv not found. Install it first: curl -LsSf https://astral.sh/uv/install.sh | sh  (see https://docs.astral.sh/uv/)"}' >&2
    exit 1
fi

# ── 2. Install agentic-vision (pinned to TAG) ────────────────────────────────
# We always install the pinned tag — never auto-upgrade to HEAD.
# To upgrade: update the TAG variable above and re-run this script.
if command -v agentic-vision &>/dev/null; then
    echo "agentic-vision already installed ($(agentic-vision --version)) — reinstalling pinned ${TAG}..." >&2
fi
uv tool install --force "${PACKAGE}"

# ── 3. Run precheck — output is what Claude reads ────────────────────────────
agentic-vision precheck --json
