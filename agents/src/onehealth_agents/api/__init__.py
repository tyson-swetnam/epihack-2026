"""FastAPI HTTP layer for the OneHealth Sentinel intake API.

Conforms to ``api/openapi.yaml`` at the repo root. The agent
orchestrator (``onehealth_agents.orchestrator``) runs behind each
endpoint; this package contains only the HTTP-shaped wrappers,
auth glue, and the pydantic request/response models that mirror
the spec.

See ``plan/06-mobile-app.md`` for the privacy contract and
``plan/07-auth.md`` for the auth architecture.
"""

from .main import app  # noqa: F401  (re-export for `uvicorn onehealth_agents.api:app`)

__all__ = ["app"]
