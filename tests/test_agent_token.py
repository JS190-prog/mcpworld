"""Tests for the account-level agent token (web-driven onboarding auth).

The agent token replaces email-only identification: the dashboard mints a signed,
long-lived token for the logged-in user, the deep link carries it, and the agent
authenticates with it. Email remains accepted for backward compatibility.
"""
import importlib.util
import os
import shutil
import uuid
from pathlib import Path


def load_api(db_path):
    os.environ["MCPWORLD_DB"] = str(db_path)
    os.environ["MCPWORLD_PROXY_PUBLIC_BASE"] = ""
    spec = importlib.util.spec_from_file_location(
        "mcpworld_api_tok", Path(__file__).resolve().parents[1] / "backend" / "mcpworld_api.py"
    )
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    return api


def temp_db():
    root = Path.cwd() / ".test-tmp" / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    return root, root / "mcpworld.sqlite3"


def test_sign_verify_roundtrip():
    root, db = temp_db()
    try:
        api = load_api(db)
        token = api.sign_agent_token("usr-123")
        assert api.verify_agent_token(token) == "usr-123"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_verify_rejects_tamper_garbage_and_wrong_prefix():
    root, db = temp_db()
    try:
        api = load_api(db)
        token = api.sign_agent_token("usr-123")
        assert api.verify_agent_token(token + "x") is None  # tampered signature
        assert api.verify_agent_token("garbage") is None
        # a login-cookie token (no 'agent.' prefix) must not pass as an agent token
        assert api.verify_agent_token(api.sign_auth_session("usr-123")) is None
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_agent_user_from_body_token_and_email():
    root, db_path = temp_db()
    try:
        api = load_api(db_path)
        api.init_db()
        with api.get_db() as db:
            api.seed_user(db, "u@example.com", "U", "pw-12345678", "Pro", "active", "normal")
            uid = db.execute("select id from users where email=?", ("u@example.com",)).fetchone()["id"]
            assert api.agent_user_from_body(db, {"token": api.sign_agent_token(uid)})["id"] == uid
            assert api.agent_user_from_body(db, {"email": "u@example.com"})["id"] == uid
            # a bad token resolves to nobody (must NOT fall back to email)
            assert api.agent_user_from_body(db, {"token": "bad", "email": "u@example.com"}) is None
            assert api.agent_user_from_body(db, {}) is None
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("PASS agent token tests")
