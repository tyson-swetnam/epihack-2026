"""Entry point for ``wearable-mcp`` and ``python -m wearable_mcp``."""

from .server import mcp


def main() -> None:
    # FastMCP's default transport is stdio (Claude Desktop convention).
    # Override via MCP_TRANSPORT=streamable-http for a hosted deployment.
    import os

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
