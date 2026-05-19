"""Entry point for `sms-entry-mcp` and `python -m sms_entry_mcp`."""

from __future__ import annotations

from .server import mcp


def main() -> None:
    import os

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
