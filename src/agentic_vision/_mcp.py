"""
FastMCP stdio server entry point for agentic-vision.

Install with MCP extras:
    uv tool install "agentic-vision[mcp] @ git+https://github.com/ibaou-dev/agentic-image-analyser"

Register with Claude Code (add to claude_desktop_config.json or project MCP settings):
    {
      "mcpServers": {
        "agentic-vision": {
          "command": "agentic-vision-mcp"
        }
      }
    }

Or start manually for testing:
    agentic-vision-mcp
"""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError(
        "FastMCP is not installed. Install with:\n"
        '  uv tool install "agentic-vision[mcp] @ git+https://github.com/ibaou-dev/agentic-image-analyser"'
    ) from exc

from agentic_vision._mcp_tools import register_tools


def main() -> None:
    mcp = FastMCP("agentic-vision")
    register_tools(mcp)
    mcp.run()


if __name__ == "__main__":
    main()
