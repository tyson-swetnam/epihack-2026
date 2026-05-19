"""The server must refuse to start when INAT_USER_AGENT is unset.

The iNaturalist API explicitly requires a meaningful User-Agent
header on every request
(see https://www.inaturalist.org/pages/api+recommended+practices).
Anonymous traffic gets throttled or blocked, which would poison the
shared rate-limit budget for the whole EpiHack stack. So we enforce
the requirement at startup -- both in the ``INaturalistClient``
constructor and in the ``__main__`` entry point.
"""

from __future__ import annotations

import os
import runpy
import sys

import pytest

from inaturalist_mcp.client import INatUserAgentMissing, INaturalistClient


def _scrub_ua(monkeypatch):
    monkeypatch.delenv("INAT_USER_AGENT", raising=False)


def test_client_refuses_without_user_agent(monkeypatch):
    """The client constructor must raise if INAT_USER_AGENT is unset."""
    _scrub_ua(monkeypatch)
    with pytest.raises(INatUserAgentMissing) as excinfo:
        INaturalistClient(offline=True)
    msg = str(excinfo.value)
    assert "INAT_USER_AGENT" in msg
    assert "User-Agent" in msg


def test_client_accepts_explicit_user_agent(monkeypatch):
    """Passing user_agent= overrides the env-var requirement."""
    _scrub_ua(monkeypatch)
    c = INaturalistClient(
        user_agent="explicit-ua/0.1 (test@example.org)",
        offline=True,
    )
    assert c.user_agent == "explicit-ua/0.1 (test@example.org)"


def test_client_accepts_env_user_agent(monkeypatch):
    monkeypatch.setenv("INAT_USER_AGENT", "from-env/0.1 (ops@example.org)")
    c = INaturalistClient(offline=True)
    assert c.user_agent == "from-env/0.1 (ops@example.org)"


def test_main_entry_point_exits_2_without_user_agent(monkeypatch, capsys):
    """Running the module as ``python -m inaturalist_mcp`` must exit 2.

    We invoke ``__main__.main`` directly (rather than spawning a
    subprocess) so the test stays offline and deterministic.
    """
    _scrub_ua(monkeypatch)
    # `from .server import mcp` is only triggered if main() gets past
    # the User-Agent check, so this test never spins up FastMCP.
    from inaturalist_mcp.__main__ import main

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "INAT_USER_AGENT" in err
    assert "refusing to start" in err.lower()


def test_main_entry_point_module_runpath_also_exits_2(monkeypatch, capsys):
    """``python -m inaturalist_mcp`` (the runpy path) must also exit 2."""
    _scrub_ua(monkeypatch)
    # Force a fresh import so the if __name__ == "__main__" guard fires.
    for mod in list(sys.modules):
        if mod.startswith("inaturalist_mcp.__main__"):
            del sys.modules[mod]
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("inaturalist_mcp", run_name="__main__")
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "INAT_USER_AGENT" in err
