"""Tests for the NWS client's env-driven configuration.

Verifies:
  * NWS_USER_AGENT is required; absent -> NWSConfigError on construction.
  * NWS_BASE_URL and NWS_HEATRISK_URL are honored when set in the env.
  * The PATHS dict can be overridden by NWS_PATH_* env vars (at
    import time of the client module).
"""

import importlib
import os

import pytest


def test_user_agent_required(monkeypatch):
    # Clear any inherited UA and try to construct the client.
    monkeypatch.delenv("NWS_USER_AGENT", raising=False)

    # Re-import fresh so module-level os.environ.get() doesn't matter;
    # the constructor re-checks env.
    from nws_heatrisk_mcp.client import NWSClient, NWSConfigError

    with pytest.raises(NWSConfigError) as exc:
        NWSClient()
    assert "NWS_USER_AGENT" in str(exc.value)


def test_user_agent_explicit_overrides_env(monkeypatch):
    monkeypatch.delenv("NWS_USER_AGENT", raising=False)
    from nws_heatrisk_mcp.client import NWSClient

    c = NWSClient(user_agent="test-suite (ci@example.org)")
    assert c.user_agent == "test-suite (ci@example.org)"


def test_base_url_default():
    # Defaults are read at module import; reload to apply a clean env.
    os.environ.pop("NWS_BASE_URL", None)
    import nws_heatrisk_mcp.client as cm

    importlib.reload(cm)
    assert cm.DEFAULT_BASE_URL == "https://api.weather.gov"


def test_base_url_env_override(monkeypatch):
    monkeypatch.setenv("NWS_BASE_URL", "https://example.test/nws")
    import nws_heatrisk_mcp.client as cm

    importlib.reload(cm)
    assert cm.DEFAULT_BASE_URL == "https://example.test/nws"


def test_heatrisk_url_env_override(monkeypatch):
    monkeypatch.setenv("NWS_HEATRISK_URL", "https://example.test/heatrisk.json")
    import nws_heatrisk_mcp.client as cm

    importlib.reload(cm)
    assert cm.DEFAULT_HEATRISK_URL == "https://example.test/heatrisk.json"


def test_paths_env_override(monkeypatch):
    monkeypatch.setenv("NWS_PATH_POINTS", "/v2/points/{lat},{lon}")
    monkeypatch.setenv("NWS_PATH_ALERTS_ACTIVE", "/v2/alerts/active")
    import nws_heatrisk_mcp.client as cm

    importlib.reload(cm)
    assert cm.PATHS["points"] == "/v2/points/{lat},{lon}"
    assert cm.PATHS["alerts_active"] == "/v2/alerts/active"


def test_client_uses_overridden_base_url(monkeypatch):
    monkeypatch.setenv("NWS_USER_AGENT", "test-suite (ci@example.org)")
    monkeypatch.setenv("NWS_BASE_URL", "https://example.test/nws")
    import nws_heatrisk_mcp.client as cm

    importlib.reload(cm)
    c = cm.NWSClient()
    assert c.base_url == "https://example.test/nws"


def test_known_heat_event_names_present():
    """Sanity: the HEAT_EVENTS tuple covers both the legacy and the
    new NWS heat-impact wording so the wrapper keeps working across
    the rollout."""
    from nws_heatrisk_mcp.client import HEAT_EVENTS

    assert "Excessive Heat Warning" in HEAT_EVENTS
    assert "Extreme Heat Warning" in HEAT_EVENTS
    assert "Heat Advisory" in HEAT_EVENTS
