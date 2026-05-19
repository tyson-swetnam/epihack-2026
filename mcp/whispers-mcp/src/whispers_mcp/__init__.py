"""WHISPers MCP server.

A Model Context Protocol server wrapping the USGS National Wildlife
Health Center's WHISPers (Wildlife Health Information Sharing
Partnership) event reporting system. Built for EpiHack Arizona 2026's
wildlife & vector-borne diseases focus group.

Public WHISPers events (the EventViewSet and EventSummaryViewSet
endpoints serving rows with ``public=True``) are unauthenticated; the
server falls back to a small canned AZ-centric dataset when the live
service is unreachable.
"""

__version__ = "0.1.0"
