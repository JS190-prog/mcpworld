"""Tests for the agent release channel + promotion gate (scripts/release_channel.py).

Model: edge (admin test) -> stable (consumer). The gate requires N consecutive
green runs with a healthy last run, and promotion still needs explicit confirmation.
These tests cover the pure logic; gh/deploy orchestration is exercised separately.
"""
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "release_channel", Path(__file__).resolve().parents[1] / "scripts" / "release_channel.py"
)
rc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rc)


def _ledger_with(version, runs):
    """Build a ledger by replaying (result, health) tuples through record_result."""
    ledger = {}
    for i, (result, health) in enumerate(runs):
        ledger = rc.record_result(ledger, version, result, health=health, ts=1000 + i)
    return ledger


def test_record_result_appends_and_is_immutable():
    base = {}
    one = rc.record_result(base, "0.1.0", "pass", ts=1)
    two = rc.record_result(one, "0.1.0", "fail", ts=2)
    assert base == {}  # original untouched
    assert len(one["0.1.0"]) == 1
    assert len(two["0.1.0"]) == 2
    assert two["0.1.0"][0]["result"] == "pass"
    assert two["0.1.0"][1]["result"] == "fail"


def test_record_result_validates_inputs():
    for bad in ("PASS", "ok", ""):
        try:
            rc.record_result({}, "v", bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for result={bad!r}")
    try:
        rc.record_result({}, "v", "pass", health="green")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for bad health")


def test_green_streak_counts_trailing_green():
    ledger = _ledger_with("v", [("pass", "ok"), ("pass", "ok"), ("pass", "ok")])
    assert rc.green_streak(ledger, "v") == 3


def test_green_streak_breaks_on_fail_result():
    ledger = _ledger_with("v", [("pass", "ok"), ("fail", "ok"), ("pass", "ok")])
    assert rc.green_streak(ledger, "v") == 1  # only the trailing pass counts


def test_green_streak_breaks_on_health_fail():
    ledger = _ledger_with("v", [("pass", "ok"), ("pass", "ok"), ("pass", "fail")])
    assert rc.green_streak(ledger, "v") == 0  # last run unhealthy


def test_green_streak_unknown_version_is_zero():
    assert rc.green_streak({}, "nope") == 0


def test_promotion_gate_requires_no_runs_blocks():
    elig = rc.promotion_eligibility({}, "v", required_green=3)
    assert elig["eligible"] is False
    assert elig["total_runs"] == 0


def test_promotion_gate_blocks_below_threshold():
    ledger = _ledger_with("v", [("pass", "ok"), ("pass", "ok")])
    elig = rc.promotion_eligibility(ledger, "v", required_green=3)
    assert elig["eligible"] is False
    assert elig["green_streak"] == 2
    assert elig["required_green"] == 3


def test_promotion_gate_passes_at_threshold():
    ledger = _ledger_with("v", [("pass", "ok"), ("pass", "ok"), ("pass", "ok")])
    elig = rc.promotion_eligibility(ledger, "v", required_green=3)
    assert elig["eligible"] is True
    assert elig["green_streak"] == 3
    assert elig["health_ok"] is True


def test_promotion_gate_blocks_after_recent_fail():
    # three greens then a fail resets the streak -> blocked
    ledger = _ledger_with("v", [("pass", "ok"), ("pass", "ok"), ("pass", "ok"), ("fail", "ok")])
    elig = rc.promotion_eligibility(ledger, "v", required_green=3)
    assert elig["eligible"] is False
    assert elig["green_streak"] == 0


def test_compute_promoted_manifest_flips_track_keeps_assets():
    edge = {
        "channel": "beta",
        "track": "edge",
        "version": "0.2.0-beta.3",
        "assets": {"exe": {"sha256": "abc"}},
    }
    stable = rc.compute_promoted_manifest(edge)
    assert stable["track"] == "stable"
    assert stable["version"] == "0.2.0-beta.3"
    assert stable["assets"] == edge["assets"]
    assert edge["track"] == "edge"  # input not mutated


def test_repoint_site_text_replaces_tag():
    text = "  githubReleases: 'https://github.com/JS190-prog/mcpworld/releases/tag/v0.2.0-beta.2',\n"
    out = rc.repoint_site_text(text, "0.2.0-beta.5", repo="JS190-prog/mcpworld")
    assert "releases/tag/v0.2.0-beta.5'" in out
    assert "beta.2" not in out


def test_classify_verification_pytest_only():
    assert rc.classify_verification(0) == ("pass", "ok", "pytest=pass")
    assert rc.classify_verification(1) == ("fail", "ok", "pytest=fail")


def test_classify_verification_with_smoke():
    # tests pass and tool smoke runs -> green
    assert rc.classify_verification(0, 0) == ("pass", "ok", "pytest=pass; smoke=ok")
    # tests pass but the tool does not actually run -> health fail (not green)
    assert rc.classify_verification(0, 1) == ("pass", "fail", "pytest=pass; smoke=fail")
    # tests fail but smoke ok -> result fail
    assert rc.classify_verification(1, 0) == ("fail", "ok", "pytest=fail; smoke=ok")


def test_classify_verification_feeds_gate():
    # a pass/ok classification recorded 3x should make the gate eligible
    result, health, _ = rc.classify_verification(0, 0)
    ledger = {}
    for i in range(3):
        ledger = rc.record_result(ledger, "v", result, health=health, ts=i)
    assert rc.promotion_eligibility(ledger, "v", required_green=3)["eligible"] is True
    # a pass-with-failing-smoke classification must NOT make it eligible
    result, health, _ = rc.classify_verification(0, 1)
    ledger2 = rc.record_result({}, "v", result, health=health)
    assert rc.green_streak(ledger2, "v") == 0


def test_seeded_channel_manifests_are_consistent():
    """The committed edge/stable seeds should be valid and same-version at rest."""
    root = Path(__file__).resolve().parents[1]
    edge = rc.read_json(root / "release" / "edge.json")
    stable = rc.read_json(root / "release" / "stable.json")
    assert edge["track"] == "edge"
    assert stable["track"] == "stable"
    assert edge["version"] == stable["version"]
    assert set(edge["assets"]) == {"exe", "msi"}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS release channel tests")
