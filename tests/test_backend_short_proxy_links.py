import importlib.util
import json
import os
import shutil
import threading
import uuid
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer


def load_api(db_path, proxy_base=""):
    os.environ["MCPWORLD_DB"] = str(db_path)
    os.environ["MCPWORLD_PROXY_PUBLIC_BASE"] = proxy_base
    spec = importlib.util.spec_from_file_location("mcpworld_api_short", Path(__file__).resolve().parents[1] / "backend" / "mcpworld_api.py")
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    return api


def temp_db_path():
    root = Path.cwd() / ".test-tmp" / str(uuid.uuid4())
    root.mkdir(parents=True, exist_ok=True)
    return root, root / "mcpworld.sqlite3"


def create_test_user(api, db):
    api.seed_user(db, "test-user@example.com", "Test User", "change-me-1234", "Pro", "active", "normal")
    return db.execute("select * from users where email = ?", ("test-user@example.com",)).fetchone()


def post_json(url, payload, cookie=None):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, dict(response.headers), json.loads(response.read().decode("utf-8"))


def with_api_server(api, fn):
    server = ThreadingHTTPServer(("127.0.0.1", 0), api.ApiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        return fn(f"http://127.0.0.1:{server.server_address[1]}")
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_session_route_uses_worker_proxy_base():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path, "https://mcpworld-proxy.example.workers.dev/mcpworld")
        api.init_db()
        with api.get_db() as db:
            user = create_test_user(api, db)
            session = api.create_session(db, user["id"], "cad")
            stored = db.execute("select route_key, route from sessions where id = ?", (session["id"],)).fetchone()
        assert session["route"].startswith("https://mcpworld-proxy.example.workers.dev/mcpworld/mw-")
        assert session["route"].endswith("/mcp")
        assert "/relay/" not in session["route"]
        assert "token=" not in session["route"]
        assert stored["route_key"].startswith("mw-")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_session_route_falls_back_to_vps_short_endpoint():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path, "")
        api.init_db()
        with api.get_db() as db:
            user = create_test_user(api, db)
            session = api.create_session(db, user["id"], "hwp")
        assert session["route"].startswith("https://www.tornado616.cloud/mcpworld/mcp?key=mw-")
        assert "/relay/" not in session["route"]
        assert "token=" not in session["route"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_session_links_use_authenticated_owner_not_posted_email():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path, "")
        api.init_db()
        with api.get_db() as db:
            api.seed_user(db, "owner@example.com", "Owner", "owner-pass-1234", "Admin", "active", "normal")
            create_test_user(api, db)

        def run(base_url):
            _, login_headers, login_body = post_json(
                f"{base_url}/auth/login",
                {"identifier": "owner@example.com", "password": "owner-pass-1234"},
            )
            assert login_body["ok"] is True
            cookie = login_headers["Set-Cookie"].split(";", 1)[0]
            _, _, links_body = post_json(
                f"{base_url}/sessions/links",
                {"email": "test-user@example.com"},
                cookie=cookie,
            )
            assert links_body["ok"] is True
            with api.get_db() as db:
                owner = db.execute("select id from users where email = ?", ("owner@example.com",)).fetchone()
                test_user = db.execute("select id from users where email = ?", ("test-user@example.com",)).fetchone()
                owner_sessions = db.execute("select count(*) as c from sessions where user_id = ?", (owner["id"],)).fetchone()["c"]
                test_sessions = db.execute("select count(*) as c from sessions where user_id = ?", (test_user["id"],)).fetchone()["c"]
            assert owner_sessions == len(api.CONNECTOR_CATALOG)
            assert test_sessions == 0

        with_api_server(api, run)
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    test_session_route_uses_worker_proxy_base()
    test_session_route_falls_back_to_vps_short_endpoint()
    test_session_links_use_authenticated_owner_not_posted_email()
    print("PASS backend short proxy link tests")
