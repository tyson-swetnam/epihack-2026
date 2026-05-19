"""Entry point for ``adhs-mcp`` and ``python -m adhs_mcp``."""

from .server import mcp


def main() -> None:
    # FastMCP's default transport is stdio, which is what Claude Desktop
    # and most MCP clients expect. Pass MCP_TRANSPORT=streamable-http
    # to switch to HTTP for a hosted deployment.
    import os

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
