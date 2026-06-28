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


def test_verify_sha256():
    import hashlib
    data = b"installer-bytes"
    good = hashlib.sha256(data).hexdigest()
    assert agent.verify_sha256(data, good) is True
    assert agent.verify_sha256(data, good.upper()) is True  # case-insensitive
    assert agent.verify_sha256(data, "deadbeef") is False
    assert agent.verify_sha256(data, "") is True  # no expected -> skip verification


def test_manifest_url_resolution():
    server = "https://www.tornado616.cloud/mcpworld"
    assert agent.manifest_url_for(server) == "https://www.tornado616.cloud/mcpworld/release/stable.json"
    assert agent.manifest_url_for(server, "https://x/edge.json") == "https://x/edge.json"
    os.environ["MCPWORLD_UPDATE_MANIFEST_URL"] = "https://env/m.json"
    try:
        assert agent.manifest_url_for(server) == "https://env/m.json"
    finally:
        del os.environ["MCPWORLD_UPDATE_MANIFEST_URL"]


def test_parse_connect_url():
    d = agent.parse_connect_url(
        "mcpworld://connect?server=https%3A%2F%2Fx%2Fmcpworld&token=agent.u.1.sig&agentId=a1"
    )
    assert d == {"server": "https://x/mcpworld", "token": "agent.u.1.sig", "agentId": "a1"}
    assert agent.parse_connect_url("mcpworld://connect?token=abc") == {"token": "abc"}
    assert agent.parse_connect_url("https://evil/connect?token=abc") == {}  # wrong scheme


def test_agent_creds_roundtrip(tmp_path):
    p = tmp_path / "agent.json"
    agent.save_agent_creds({"server": "https://s", "token": "t1", "agentId": ""}, path=p)
    loaded = agent.load_agent_creds(p)
    assert loaded["server"] == "https://s" and loaded["token"] == "t1"
    assert "agentId" not in loaded  # empty values are not persisted
    agent.save_agent_creds({"agentId": "a9"}, path=p)  # merge update
    after = agent.load_agent_creds(p)
    assert after["agentId"] == "a9" and after["token"] == "t1"  # existing preserved


if __name__ == "__main__":
    import tempfile
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            if "tmp_path" in fn.__code__.co_varnames:
                with tempfile.TemporaryDirectory() as d:
                    fn(Path(d))
            else:
                fn()
    print("PASS agent update engine tests")
