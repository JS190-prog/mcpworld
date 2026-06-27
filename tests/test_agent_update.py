"""Tests for the agent auto-update engine (version compare + update decision).

Pure logic only — no network. Covers _version_key ordering (prerelease vs stable),
update_decision (available/forced/asset extraction), and manifest URL resolution.
"""
import importlib.util
import os
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "mcpworld_agent_upd", Path(__file__).resolve().parents[1] / "agent" / "mcpworld_agent.py"
)
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


def test_version_key_orders_prereleases():
    k = agent._version_key
    assert k("0.2.0-beta.2") < k("0.2.0-beta.3")
    assert k("0.2.0-beta.3") < k("0.2.0-beta.10")  # numeric, not lexical
    assert k("0.2.0-beta.9") < k("0.2.0")          # stable outranks its prereleases
    assert k("0.2.0") < k("0.3.0")
    assert k("0.2.0") < k("1.0.0-beta.1")           # major bump wins
    assert k("v0.2.0-beta.2") == k("0.2.0-beta.2")  # leading v tolerated


def _manifest(version, minimum=None):
    return {
        "version": version,
        "minimumAgentVersion": minimum or version,
        "assets": {"exe": {"url": f"https://x/{version}/Setup.exe", "sha256": "deadbeef"}},
    }


def test_update_available_when_target_newer():
    # explicit older minimum -> available but not forced
    d = agent.update_decision("0.2.0-beta.2", _manifest("0.2.0-beta.3", minimum="0.2.0-beta.1"))
    assert d["update_available"] is True
    assert d["forced"] is False
    assert d["asset_url"].endswith("0.2.0-beta.3/Setup.exe")
    assert d["sha256"] == "deadbeef"


def test_no_update_when_same_or_older():
    assert agent.update_decision("0.2.0-beta.2", _manifest("0.2.0-beta.2"))["update_available"] is False
    assert agent.update_decision("0.2.0-beta.3", _manifest("0.2.0-beta.2"))["update_available"] is False


def test_forced_when_below_minimum():
    d = agent.update_decision("0.2.0-beta.1", _manifest("0.2.0-beta.3", minimum="0.2.0-beta.2"))
    assert d["update_available"] is True
    assert d["forced"] is True


def test_not_forced_at_or_above_minimum():
    d = agent.update_decision("0.2.0-beta.2", _manifest("0.2.0-beta.3", minimum="0.2.0-beta.2"))
    assert d["forced"] is False


def test_manifest_url_resolution():
    server = "https://www.tornado616.cloud/mcpworld"
    assert agent.manifest_url_for(server) == "https://www.tornado616.cloud/mcpworld/release/stable.json"
    assert agent.manifest_url_for(server, "https://x/edge.json") == "https://x/edge.json"
    os.environ["MCPWORLD_UPDATE_MANIFEST_URL"] = "https://env/m.json"
    try:
        assert agent.manifest_url_for(server) == "https://env/m.json"
    finally:
        del os.environ["MCPWORLD_UPDATE_MANIFEST_URL"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS agent update engine tests")
