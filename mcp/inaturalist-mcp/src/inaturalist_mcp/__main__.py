"""Entry point for ``inaturalist-mcp`` and ``python -m inaturalist_mcp``.

Refuses to start if ``INAT_USER_AGENT`` is unset, because the
iNaturalist API documentation requires every client to identify
itself with a meaningful User-Agent header. Surfacing this as a
hard failure (rather than a silent default) keeps anonymous /
abusive traffic from poisoning the shared rate-limit budget.
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    if not os.environ.get("INAT_USER_AGENT"):
        sys.stderr.write(
            "inaturalist-mcp: refusing to start because INAT_USER_AGENT "
            "is not set.\n"
            "The iNaturalist API requires every client to identify "
            "itself with a meaningful User-Agent header. Set e.g.\n"
            "  export INAT_USER_AGENT='epihack-az-2026/0.1 "
            "(contact: ops@example.org)'\n"
            "and try again.\n"
        )
        raise SystemExit(2)

    # FastMCP's default transport is stdio, which is what Claude
    # Desktop and most MCP clients expect. Pass
    # MCP_TRANSPORT=streamable-http to switch to HTTP for a hosted
    # deployment.
    from .server import mcp

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
