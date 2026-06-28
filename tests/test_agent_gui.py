"""Tests for the consumer GUI helpers (mcpworld_agent_gui).

Only the pure helpers are tested — the tkinter window needs a display. The whole
module is skipped if tkinter (or the agent import) is unavailable, so a headless
environment never breaks the suite.
"""
import socket
import sys
from pathlib import Path

import pytest

AGENT_DIR = Path(__file__).resolve().parents[1] / "agent"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

try:
    import mcpworld_agent_gui as gui
except Exception as exc:  # tkinter missing, etc.
    gui = None
    pytest.skip(f"GUI module not importable: {exc}", allow_module_level=True)


def test_mcp_reachable_open_and_closed():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        assert gui.mcp_reachable(port) is True
    finally:
        srv.close()
    assert gui.mcp_reachable(1) is False  # privileged port, almost certainly closed
    assert gui.mcp_reachable(None) is False


def test_status_text():
    assert "연결 안 됨" in gui.status_text(False)
    assert "폴링" in gui.status_text(True)
    assert "agent-1" in gui.status_text(True, "agent-1")


def test_dashboard_url():
    assert gui.dashboard_url("https://x/mcpworld") == "https://x/mcpworld/dashboard.html"
    assert gui.dashboard_url("https://x/mcpworld/") == "https://x/mcpworld/dashboard.html"
    assert gui.dashboard_url("").endswith("/dashboard.html")


def test_mask_token():
    assert gui.mask_token("") == ""
    assert gui.mask_token("short") == "저장됨"
    masked = gui.mask_token("agent.usr.123.abcdefghij")
    assert masked.startswith("agent.usr.") and "(저장됨)" in masked


def test_ensure_local_config_creates_when_missing(tmp_path):
    target = tmp_path / "config.json"
    assert not target.exists()
    gui.ensure_local_config(target)
    assert target.exists()
    import json
    data = json.loads(target.read_text(encoding="utf-8"))
    assert "mcps" in data  # valid config (example or minimal default)


def test_singleton_acquire_and_forward():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    role, srv = gui.acquire_singleton(port)
    assert role == "primary" and srv is not None
    try:
        role2, srv2 = gui.acquire_singleton(port)  # second instance sees it taken
        assert role2 == "secondary" and srv2 is None
        assert gui.forward_to_primary("mcpworld://connect?token=x", port) is True
    finally:
        srv.close()
    assert gui.forward_to_primary("PING", port) is False  # nobody listening now


if __name__ == "__main__":
    test_mcp_reachable_open_and_closed()
    test_status_text()
    test_dashboard_url()
    test_mask_token()
    test_singleton_acquire_and_forward()
    print("PASS agent GUI helper tests")
