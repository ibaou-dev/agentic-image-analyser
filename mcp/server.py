"""
FastMCP stdio server for agentic-vision.

Usage:
    uv run python mcp/server.py

Or via MCP client config:
    {
      "mcpServers": {
        "agentic-vision": {
          "command": "uv",
          "args": ["run", "python", "mcp/server.py"],
          "cwd": "/path/to/agentic-image-analyser"
        }
      }
    }
"""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError(
        "FastMCP is not installed. Install with: uv add 'agentic-vision[mcp]'"
    ) from exc

from mcp_tools import register_tools

mcp = FastMCP("agentic-vision")
register_tools(mcp)

if __name__ == "__main__":
    mcp.run()
