import importlib.util
import os
import shutil
import uuid
from pathlib import Path


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


def test_session_route_uses_worker_proxy_base():
    root, db_path = temp_db_path()
    try:
        api = load_api(db_path, "https://mcpworld-proxy.example.workers.dev/mcpworld")
        api.init_db()
        with api.get_db() as db:
            user = db.execute("select * from users where email = ?", ("demo@mcpworld.local",)).fetchone()
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
            user = db.execute("select * from users where email = ?", ("demo@mcpworld.local",)).fetchone()
            session = api.create_session(db, user["id"], "hwp")
        assert session["route"].startswith("https://www.tornado616.cloud/mcpworld/mcp?key=mw-")
        assert "/relay/" not in session["route"]
        assert "token=" not in session["route"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    test_session_route_uses_worker_proxy_base()
    test_session_route_falls_back_to_vps_short_endpoint()
    print("PASS backend short proxy link tests")
