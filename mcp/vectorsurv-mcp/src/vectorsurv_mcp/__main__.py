"""Entry point for `vectorsurv-mcp` and `python -m vectorsurv_mcp`."""

from .server import mcp


def main() -> None:
    # FastMCP's default transport is stdio, which is what Claude Desktop
    # and most MCP clients expect. Pass MCP_TRANSPORT=streamable-http
    # to switch to HTTP for a hosted deployment.
    import os

    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    # FastMCP bakes host/port/path defaults in at construction (its __init__
    # kwargs win over FASTMCP_* env vars), so apply the documented overrides
    # here for hosted streamable-HTTP deployments — e.g. several MCP servers
    # behind one nginx, each on its own port + sub-path. See README.
    if host := os.environ.get("FASTMCP_HOST"):
        mcp.settings.host = host
    if port := os.environ.get("FASTMCP_PORT"):
        mcp.settings.port = int(port)
    if path := os.environ.get("FASTMCP_STREAMABLE_HTTP_PATH"):
        mcp.settings.streamable_http_path = path

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
