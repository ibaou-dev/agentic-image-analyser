#!/usr/bin/env bash
# bootstrap.sh — preflight check for the agentic-vision skill
#
# Usage: bash .agents/skills/agentic-vision/scripts/bootstrap.sh
#
# Verifies uv is available, then runs precheck.py (stdlib-only).
# No package download — the analysis scripts ship with the skill itself.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 1. Ensure uv is available ─────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    echo '{"status":"error","error":"uv not found. Install it first: curl -LsSf https://astral.sh/uv/install.sh | sh  (see https://docs.astral.sh/uv/)"}' >&2
    exit 1
fi

# ── 2. Run precheck — output is what Claude reads ────────────────────────────
python3 "${SCRIPT_DIR}/precheck.py" --json
