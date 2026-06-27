"""Tests for the relay plan-entitlement gates (Gate A: admin-only block, Gate B: daily quota).

See RELAY_ENTITLEMENT_INTEGRATION_SPEC.md (local-code-mcp repo). Model: 3 consumer
plans (Free/Pro/Expert) get the same tools and differ only by daily call quota; admin
tools are never reachable through a consumer session.
"""

import importlib.util
import json
import os
import secrets
import shutil
import uuid
from pathlib import Path


def load_api(db_path):
    os.environ["MCPWORLD_DB"] = str(db_path)
    os.environ["MCPWORLD_PROXY_PUBLIC_BASE"] = ""
    spec = importlib.util.spec_from_file_location(
        "mcpworld_api_gates", Path(__file__).resolve().parents[1] / "backend" / "mcpworld_api.py"
    )
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    return api


def temp_db_path():
    root = Path.cwd() / ".test-tmp" / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    return root, root / "mcpworld.sqlite3"


def create_test_user(api, db, plan="Pro"):
    api.seed_user(db, "test-user@example.com", "Test User", "change-me-1234", plan, "active", "normal")
    return db.execute("select * from users where email = ?", ("test-user@example.com",)).fetchone()


def insert_call(api, db, user_id, tool_name, created_at=None):
    cid = "call-" + secrets.token_hex(4)
    ts = created_at if created_at is not None else api.now()
    db.execute(
        "insert into tool_calls (id, session_id, user_id, tool_name, arguments_json, status, created_at, updated_at)"
        " values (?, ?, ?, ?, ?, 'queued', ?, ?)",
        (cid, "ses-x", user_id, tool_name, json.dumps({}), ts, ts),
    )


def test_plan_model_and_quota_table():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path)
        assert api.VALID_USER_PLANS == {"Free", "Pro", "Expert", "Admin"}
        assert api.plan_quota("Free") == 50
        assert api.plan_quota("Pro") == 1000
        assert api.plan_quota("Expert") == 0  # unlimited
        assert api.plan_quota("Bogus") == 50  # unknown -> Free quota
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_is_quota_counted():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path)
        assert api.is_quota_counted("cad.mcp.call") is True
        assert api.is_quota_counted("cad.status") is False
        assert api.is_quota_counted("cad.mcp.status") is False
        assert api.is_quota_counted("system.ping") is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_gate_a_admin_only_detection():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path)
        assert "mcp_run_command_safely" in api.ADMIN_ONLY_TOOLS
        # admin underlying tool routed via .mcp.call -> blocked
        assert api.is_admin_only_call("cad.mcp.call", {"tool": "mcp_run_command_safely"}) is True
        assert api.is_admin_only_call("hwp.mcp.call", {"tool": "mcp_autonomous_self_heal"}) is True
        # non-admin underlying -> allowed
        assert api.is_admin_only_call("cad.mcp.call", {"tool": "mcp_read_file"}) is False
        # not a .mcp.call, or no underlying tool -> not admin
        assert api.is_admin_only_call("cad.status", {"tool": "mcp_run_command_safely"}) is False
        assert api.is_admin_only_call("cad.mcp.call", {}) is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_gate_b_quota_counting_and_status():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path)
        api.init_db()
        with api.get_db() as db:
            user = create_test_user(api, db, plan="Free")
            uid = user["id"]
            for _ in range(3):
                insert_call(api, db, uid, "cad.mcp.call")
            insert_call(api, db, uid, "cad.status")  # not counted
            assert api.calls_used_today(db, uid) == 3
            exceeded, used, limit = api.quota_status(db, uid, "Free")
            assert (exceeded, used, limit) == (False, 3, 50)
            # reach the Free limit (50 counted calls total)
            for _ in range(47):
                insert_call(api, db, uid, "cad.mcp.call")
            exceeded, used, limit = api.quota_status(db, uid, "Free")
            assert exceeded is True and used == 50 and limit == 50
            # Expert (unlimited) is never exceeded
            assert api.quota_status(db, uid, "Expert")[0] is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_quota_resets_per_day():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path)
        api.init_db()
        with api.get_db() as db:
            user = create_test_user(api, db)
            uid = user["id"]
            insert_call(api, db, uid, "cad.mcp.call", created_at=api.now() - 2 * 86400)  # 2 days ago
            insert_call(api, db, uid, "cad.mcp.call")  # today
            assert api.calls_used_today(db, uid) == 1  # old call not counted
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_user_plan_lookup():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path)
        api.init_db()
        with api.get_db() as db:
            user = create_test_user(api, db, plan="Expert")
            assert api.user_plan(db, user["id"]) == "Expert"
            assert api.user_plan(db, "nonexistent") == "Free"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_localcode_is_a_connector_with_gate_a():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path)
        # local-code-mcp is now a token-issuable connector.
        assert "localcode" in api.SESSION_TOOL_IDS
        assert "localcode.mcp.call" in api.TOOL_IDS
        assert "localcode.mcp.call" in api.SESSION_TOOL_ALLOWLIST["localcode"]
        # Gate A now actually does something: admin tools via localcode.mcp.call are
        # blocked, while consumer editing tools pass.
        assert api.is_admin_only_call("localcode.mcp.call", {"tool": "mcp_run_command_safely"}) is True
        assert api.is_admin_only_call("localcode.mcp.call", {"tool": "mcp_autonomous_self_heal"}) is True
        assert api.is_admin_only_call("localcode.mcp.call", {"tool": "mcp_read_file"}) is False
        assert api.is_admin_only_call("localcode.mcp.call", {"tool": "mcp_write_file_safe"}) is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_opencrab_ingest_is_a_connector():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path)
        assert "opencrab" in api.SESSION_TOOL_IDS
        assert "opencrab.status" in api.TOOL_IDS
        assert "opencrab.mcp.status" in api.TOOL_IDS
        assert "opencrab.mcp.call" in api.TOOL_IDS
        assert "opencrab.mcp.call" in api.SESSION_TOOL_ALLOWLIST["opencrab"]
        catalog_item = next(item for item in api.CONNECTOR_CATALOG if item["slug"] == "opencrab")
        assert catalog_item["label"] == "OpenCrab Ingest"
        assert catalog_item["mcpTarget"] == "opencrab"
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS entitlement gate tests")
