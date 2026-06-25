#!/usr/bin/env python3
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import urllib.parse
import urllib.request
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_ROOT = os.environ.get("MCPWORLD_PUBLIC_URL", "https://www.tornado616.cloud/mcpworld").rstrip("/")
DB_PATH = Path(os.environ.get("MCPWORLD_DB", "/var/lib/mcpworld/mcpworld.sqlite3"))
HOST = os.environ.get("MCPWORLD_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCPWORLD_PORT", "33210"))
TOKEN_TTL_SECONDS = int(os.environ.get("MCPWORLD_SESSION_TTL_SECONDS", "3600"))
MCP_WAIT_SECONDS = float(os.environ.get("MCPWORLD_MCP_WAIT_SECONDS", "25"))
PROXY_PUBLIC_BASE = os.environ.get("MCPWORLD_PROXY_PUBLIC_BASE", "").rstrip("/")
LOGIN_TTL_SECONDS = int(os.environ.get("MCPWORLD_LOGIN_TTL_SECONDS", "604800"))
SESSION_SECRET = os.environ.get("MCPWORLD_SESSION_SECRET", "dev-insecure-change-me")
AUTH_COOKIE_NAME = "mcpworld_session"
ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.environ.get("MCPWORLD_ADMIN_EMAILS", "sky7823a@gmail.com").split(",")
    if email.strip()
}


CONNECTOR_CATALOG = [
    {"slug": "word", "category": "office", "label": "Word", "mcpTarget": "office", "description": "Use the local Office MCP through MCPWorld Agent for Word workflows."},
    {"slug": "powerpoint", "category": "office", "label": "PowerPoint", "mcpTarget": "office", "description": "Use the local Office MCP through MCPWorld Agent for PowerPoint workflows."},
    {"slug": "excel", "category": "office", "label": "Excel", "mcpTarget": "office", "description": "Use the local Office MCP through MCPWorld Agent for Excel workflows."},
    {"slug": "cad", "category": "cad", "label": "CAD", "mcpTarget": "cad", "description": "Use the local CAD MCP through MCPWorld Agent for drawing analysis and automation."},
    {"slug": "hwp", "category": "document", "label": "HWP", "mcpTarget": "hwp", "description": "Use the local HWP MCP through MCPWorld Agent for Hancom document workflows."},
    {"slug": "photoshop", "category": "creative", "label": "Photoshop", "mcpTarget": "photoshop", "description": "Use the local Photoshop MCP through MCPWorld Agent for document and layer automation."},
    {"slug": "blender", "category": "creative", "label": "Blender", "mcpTarget": "blender", "description": "Use the local Blender MCP through MCPWorld Agent for scene and render workflows."},
]

TOOL_CATALOG = [
    {
        "id": "system.ping",
        "category": "system",
        "label": "Agent ping",
        "description": "Verify MCPWorld Agent can receive and answer tool calls.",
        "requiresLocalApp": False,
        "transport": "agent-poll",
    }
]

for connector in CONNECTOR_CATALOG:
    slug = connector["slug"]
    TOOL_CATALOG.extend(
        [
            {
                "id": f"{slug}.status",
                "category": connector["category"],
                "label": f"{connector['label']} app status",
                "description": f"Check local app availability and the configured {connector['mcpTarget']} MCP endpoint.",
                "requiresLocalApp": True,
                "transport": "agent-poll",
                "connector": slug,
                "mcpTarget": connector["mcpTarget"],
            },
            {
                "id": f"{slug}.mcp.status",
                "category": connector["category"],
                "label": f"{connector['label']} MCP status",
                "description": f"List and verify tools exposed by the local {connector['mcpTarget']} MCP endpoint.",
                "requiresLocalApp": True,
                "transport": "agent-poll-to-local-mcp",
                "connector": slug,
                "mcpTarget": connector["mcpTarget"],
            },
            {
                "id": f"{slug}.mcp.call",
                "category": connector["category"],
                "label": f"{connector['label']} MCP tool call",
                "description": connector["description"] + " Arguments must include {'tool': '<local_mcp_tool_name>', 'arguments': {...}}.",
                "requiresLocalApp": True,
                "transport": "agent-poll-to-local-mcp",
                "connector": slug,
                "mcpTarget": connector["mcpTarget"],
                "inputSchema": {
                    "type": "object",
                    "required": ["tool"],
                    "properties": {
                        "tool": {"type": "string", "description": "Tool name exposed by the local MCP server."},
                        "arguments": {"type": "object", "description": "Arguments forwarded to the local MCP tool.", "default": {}},
                    },
                },
            },
        ]
    )

TOOL_IDS = {tool["id"] for tool in TOOL_CATALOG}
SESSION_TOOL_IDS = {connector["slug"] for connector in CONNECTOR_CATALOG}
SESSION_TOOL_ALLOWLIST = {
    connector["slug"]: {"system.ping", f"{connector['slug']}.status", f"{connector['slug']}.mcp.status", f"{connector['slug']}.mcp.call"}
    for connector in CONNECTOR_CATALOG
}



def now() -> int:
    return int(time.time())


def json_response(handler, status, payload, extra_headers=None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    for name, value in extra_headers or []:
        handler.send_header(name, value)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def html_response(handler, status, body, extra_headers=None):
    encoded = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    for name, value in extra_headers or []:
        handler.send_header(name, value)
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_admin_email(email: str) -> bool:
    return bool(email) and email.strip().lower() in ADMIN_EMAILS


def cookie_path() -> str:
    return urllib.parse.urlparse(APP_ROOT).path or "/"


def sign_auth_session(user_id: str) -> str:
    issued_at = str(now())
    payload = f"{user_id}.{issued_at}"
    signature = hmac.new(SESSION_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    encoded_sig = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{payload}.{encoded_sig}"


def verify_auth_session(value: str):
    try:
        user_id, issued_at, signature = value.split(".", 2)
        payload = f"{user_id}.{issued_at}"
        expected = hmac.new(SESSION_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
        padded = signature + "=" * (-len(signature) % 4)
        actual = base64.urlsafe_b64decode(padded.encode("ascii"))
        if not hmac.compare_digest(expected, actual):
            return None
        if now() - int(issued_at) > LOGIN_TTL_SECONDS:
            return None
        return user_id
    except Exception:
        return None


def auth_cookie_header(user_id: str) -> str:
    return (
        f"{AUTH_COOKIE_NAME}={sign_auth_session(user_id)}; "
        f"Path={cookie_path()}; Max-Age={LOGIN_TTL_SECONDS}; HttpOnly; Secure; SameSite=Lax"
    )


def clear_auth_cookie_header() -> str:
    return f"{AUTH_COOKIE_NAME}=; Path={cookie_path()}; Max-Age=0; HttpOnly; Secure; SameSite=Lax"


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(db, table, column, definition):
    existing = {row["name"] for row in db.execute(f"pragma table_info({table})").fetchall()}
    if column not in existing:
        db.execute(f"alter table {table} add column {column} {definition}")


def init_db():
    with get_db() as db:
        db.executescript(
            """
            create table if not exists users (
              id text primary key,
              email text unique not null,
              display_name text not null,
              password_hash text,
              provider text not null default 'email',
              plan text not null default 'Free',
              status text not null default 'active',
              risk text not null default 'normal',
              created_at integer not null,
              last_seen_at integer
            );
            create table if not exists sessions (
              id text primary key,
              user_id text not null,
              tool text not null,
              token_hash text not null,
              route_key text,
              route text not null,
              status text not null default 'active',
              relay_status text not null default 'waiting_agent',
              created_at integer not null,
              expires_at integer not null,
              ended_at integer
            );
            create table if not exists agents (
              id text primary key,
              user_id text not null,
              device_name text not null,
              status text not null default 'online',
              last_seen_at integer not null
            );
            create table if not exists audit_logs (
              id integer primary key autoincrement,
              at integer not null,
              actor text not null,
              event_type text not null,
              target text not null,
              status text not null,
              message text not null
            );
            create table if not exists billing_events (
              id integer primary key autoincrement,
              at integer not null,
              provider text not null,
              event_id text,
              status text not null,
              payload text not null
            );
            create table if not exists tool_calls (
              id text primary key,
              session_id text not null,
              user_id text not null,
              tool_name text not null,
              arguments_json text not null,
              status text not null default 'queued',
              result_json text,
              error text,
              agent_id text,
              created_at integer not null,
              updated_at integer not null
            );
            """
        )
        seed_user(db, "demo@mcpworld.local", "데모 사용자", "demo1234", "Pro", "active", "normal")
        seed_user(db, "ops@flowstudio.kr", "Flow Studio", "demo1234", "Team", "active", "warning")
        seed_user(db, "cad24@example.com", "CAD 검토자", "demo1234", "Pro", "limited", "critical")
        seed_log(db, "system", "startup", "api", "success", "MCP World API initialized")


def seed_user(db, email, display_name, password, plan, status, risk):
    existing = db.execute("select id from users where email = ?", (email,)).fetchone()
    if existing:
        return
    db.execute(
        """
        insert into users (id, email, display_name, password_hash, provider, plan, status, risk, created_at, last_seen_at)
        values (?, ?, ?, ?, 'email', ?, ?, ?, ?, ?)
        """,
        (secrets.token_hex(8), email, display_name, hash_secret(password), plan, status, risk, now(), now()),
    )


def seed_log(db, actor, event_type, target, status, message):
    recent = db.execute(
        "select id from audit_logs where actor = ? and event_type = ? and target = ? and message = ? limit 1",
        (actor, event_type, target, message),
    ).fetchone()
    if not recent:
        db.execute(
            "insert into audit_logs (at, actor, event_type, target, status, message) values (?, ?, ?, ?, ?, ?)",
            (now(), actor, event_type, target, status, message),
        )


def read_body(handler):
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    data = handler.rfile.read(length)
    if not data:
        return {}
    return json.loads(data.decode("utf-8"))


def public_user(row):
    return {
        "id": row["id"],
        "email": row["email"],
        "displayName": row["display_name"],
        "plan": row["plan"],
        "status": row["status"],
        "risk": row["risk"],
        "lastSeenAt": row["last_seen_at"],
    }


def log_event(db, actor, event_type, target, status, message):
    db.execute(
        "insert into audit_logs (at, actor, event_type, target, status, message) values (?, ?, ?, ?, ?, ?)",
        (now(), actor, event_type, target, status, message),
    )


def create_session(db, user_id, tool):
    token = secrets.token_urlsafe(24)
    route_key = "mw-" + secrets.token_urlsafe(12).replace("=", "")
    session_id = "ses-" + secrets.token_hex(5)
    expires_at = now() + TOKEN_TTL_SECONDS
    user = db.execute("select email from users where id = ?", (user_id,)).fetchone()
    encoded_key = urllib.parse.quote(route_key)
    route = f"{PROXY_PUBLIC_BASE}/{encoded_key}/mcp" if PROXY_PUBLIC_BASE else f"{APP_ROOT}/mcp?key={encoded_key}"
    db.execute(
        """
        insert into sessions (id, user_id, tool, token_hash, route_key, route, status, relay_status, created_at, expires_at)
        values (?, ?, ?, ?, ?, ?, 'active', 'waiting_agent', ?, ?)
        """,
        (session_id, user_id, tool, hash_secret(token), route_key, route, now(), expires_at),
    )
    log_event(db, user["email"] if user else "system", "session.issue", session_id, "success", f"{tool} mcpworld short connector issued")
    return {"id": session_id, "tool": tool, "route": route, "expiresAt": expires_at, "status": "active"}


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "MCPWorldAPI/0.1"

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", APP_ROOT)
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            path = path[4:]
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if path == "/health":
                with get_db() as db:
                    count = db.execute("select count(*) c from users").fetchone()["c"]
                return json_response(self, 200, {"ok": True, "users": count, "time": now()})
            if path == "/auth/google/url":
                return self.google_url()
            if path == "/auth/google/callback":
                return self.google_callback(query)
            if path == "/auth/me":
                return self.auth_me()
            if path == "/admin/bootstrap":
                return self.admin_bootstrap(query)
            if path == "/tools/catalog":
                return json_response(self, 200, {"ok": True, "tools": TOOL_CATALOG})
            if path == "/mcp":
                return self.mcp_endpoint_status(query)
            if path.startswith("/tool-calls/"):
                call_id = path.split("/")[2]
                return self.get_tool_call(call_id)
            if path.startswith("/relay/u/"):
                return self.relay_status(path, query)
            return json_response(self, 404, {"ok": False, "error": "not_found"})
        except Exception as exc:
            return json_response(self, 500, {"ok": False, "error": "server_error", "message": str(exc)})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        if path.startswith("/api/"):
            path = path[4:]
        try:
            if path == "/auth/signup":
                return self.signup()
            if path == "/auth/login":
                return self.login()
            if path == "/auth/logout":
                return json_response(self, 200, {"ok": True}, extra_headers=[("Set-Cookie", clear_auth_cookie_header())])
            if path == "/billing/checkout":
                return self.checkout()
            if path == "/billing/webhook":
                return self.billing_webhook()
            if path == "/mcp":
                return self.mcp_json_rpc(query)
            if path == "/sessions/links":
                return self.session_links(regenerate=False)
            if path == "/sessions/regenerate":
                return self.session_links(regenerate=True)
            if path == "/sessions/issue":
                return self.issue_session()
            if path.startswith("/sessions/") and path.endswith("/terminate"):
                session_id = path.split("/")[2]
                return self.terminate_session(session_id)
            if path == "/agent/register":
                return self.register_agent()
            if path == "/agent/poll":
                return self.agent_poll()
            if path == "/agent/result":
                return self.agent_result()
            if path == "/tool-calls/enqueue":
                return self.enqueue_tool_call()
            if path == "/admin/action":
                return self.admin_action()
            return json_response(self, 404, {"ok": False, "error": "not_found"})
        except Exception as exc:
            return json_response(self, 500, {"ok": False, "error": "server_error", "message": str(exc)})

    def resolve_short_session(self, query):
        route_key = (query.get("key") or query.get("mcpworld") or [""])[0]
        if not route_key:
            return None, {"ok": False, "error": "missing_key", "message": "Use /mcp?key=YOUR_MCPWORLD_KEY."}
        with get_db() as db:
            session = db.execute("select * from sessions where route_key = ?", (route_key,)).fetchone()
            if not session:
                return None, {"ok": False, "error": "session_not_found"}
            if session["expires_at"] < now() or session["status"] != "active":
                return None, {"ok": False, "error": "session_expired"}
            return dict(session), None

    def mcp_endpoint_status(self, query):
        session, error = self.resolve_short_session(query)
        if error:
            status = 400 if error["error"] == "missing_key" else 404 if error["error"] == "session_not_found" else 410
            return json_response(self, status, error)
        return json_response(
            self,
            200,
            {
                "ok": True,
                "service": "mcpworld",
                "endpoint": "/mcp",
                "sessionId": session["id"],
                "connector": session["tool"],
                "message": "Short MCPWorld endpoint is valid. Use this URL as the MCP server URL.",
            },
        )

    def mcp_json_rpc(self, query):
        session, error = self.resolve_short_session(query)
        if error:
            status = 400 if error["error"] == "missing_key" else 404 if error["error"] == "session_not_found" else 410
            return json_response(self, status, error)
        payload = read_body(self)
        if isinstance(payload, list):
            responses = [self.handle_mcp_rpc_item(item, session) for item in payload]
            return json_response(self, 200, responses)
        return json_response(self, 200, self.handle_mcp_rpc_item(payload, session))

    def handle_mcp_rpc_item(self, payload, session):
        rpc_id = payload.get("id") if isinstance(payload, dict) else None
        method = payload.get("method") if isinstance(payload, dict) else ""
        params = payload.get("params") or {} if isinstance(payload, dict) else {}
        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "serverInfo": {"name": "mcpworld", "version": "0.2.0-beta.1"},
                        "capabilities": {"tools": {}},
                    },
                }
            if method == "notifications/initialized":
                return {"jsonrpc": "2.0", "id": rpc_id, "result": {}}
            if method == "tools/list":
                return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": self.mcp_tools_for_session(session)}}
            if method == "tools/call":
                result = self.enqueue_and_wait_for_mcp_call(session, params)
                return {"jsonrpc": "2.0", "id": rpc_id, "result": result}
            return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32601, "message": f"Unsupported MCP method: {method}"}}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32000, "message": str(exc)}}

    def mcp_tools_for_session(self, session):
        allowed = SESSION_TOOL_ALLOWLIST.get(session["tool"], {"system.ping"})
        tools = []
        for tool in TOOL_CATALOG:
            if tool["id"] not in allowed:
                continue
            tools.append(
                {
                    "name": tool["id"],
                    "description": tool.get("description", tool.get("label", tool["id"])),
                    "inputSchema": tool.get("inputSchema", {"type": "object", "properties": {}}),
                }
            )
        return tools

    def enqueue_and_wait_for_mcp_call(self, session, params):
        tool_name = params.get("name") or ""
        arguments = params.get("arguments") or {}
        allowed = SESSION_TOOL_ALLOWLIST.get(session["tool"], {"system.ping"})
        if tool_name not in TOOL_IDS:
            raise ValueError("unknown_tool")
        if tool_name not in allowed:
            raise ValueError(f"tool_not_allowed_for_session:{session['tool']}")
        call_id = "call-" + secrets.token_hex(6)
        with get_db() as db:
            db.execute(
                """
                insert into tool_calls (id, session_id, user_id, tool_name, arguments_json, status, created_at, updated_at)
                values (?, ?, ?, ?, ?, 'queued', ?, ?)
                """,
                (call_id, session["id"], session["user_id"], tool_name, json.dumps(arguments, ensure_ascii=False), now(), now()),
            )
            db.execute("update sessions set relay_status = 'queued' where id = ?", (session["id"],))
            log_event(db, "mcpworld", "mcp.tool.enqueue", call_id, "success", f"{tool_name} queued through short endpoint")
        deadline = time.time() + MCP_WAIT_SECONDS
        while time.time() < deadline:
            with get_db() as db:
                row = db.execute("select * from tool_calls where id = ?", (call_id,)).fetchone()
            if row and row["status"] in {"done", "error"}:
                if row["status"] == "error":
                    raise ValueError(row["error"] or "agent_error")
                result = json.loads(row["result_json"] or "null")
                if isinstance(result, dict) and "content" in result:
                    return result
                return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "callId": call_id}
            time.sleep(0.5)
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"MCPWorld queued {tool_name} as {call_id}. The local agent has not returned a result yet.",
                }
            ],
            "isError": True,
            "callId": call_id,
        }

    def google_url(self):
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", f"{APP_ROOT}/api/auth/google/callback")
        if not client_id:
            return json_response(self, 503, {"ok": False, "error": "needs_config", "missing": ["GOOGLE_CLIENT_ID"]})
        state = secrets.token_urlsafe(18)
        params_data = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
        access_type = os.environ.get("GOOGLE_OAUTH_ACCESS_TYPE", "").strip()
        prompt = os.environ.get("GOOGLE_OAUTH_PROMPT", "").strip()
        if access_type:
            params_data["access_type"] = access_type
        if prompt:
            params_data["prompt"] = prompt
        params = urllib.parse.urlencode(params_data)
        return json_response(self, 200, {"ok": True, "url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}", "state": state})

    def google_callback(self, query):
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", f"{APP_ROOT}/api/auth/google/callback")
        code = (query.get("code") or [""])[0]
        if not client_id or not client_secret:
            return json_response(self, 503, {"ok": False, "error": "needs_config", "missing": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]})
        if not code:
            return json_response(self, 400, {"ok": False, "error": "missing_code"})

        token_payload = urllib.parse.urlencode(
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        token_req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(token_req, timeout=10) as res:
            token_data = json.loads(res.read().decode("utf-8"))
        access_token = token_data.get("access_token")
        if not access_token:
            return json_response(self, 502, {"ok": False, "error": "token_exchange_failed"})
        user_req = urllib.request.Request("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        with urllib.request.urlopen(user_req, timeout=10) as res:
            info = json.loads(res.read().decode("utf-8"))
        email = (info.get("email") or "").lower()
        display_name = info.get("name") or email.split("@")[0]
        if not email:
            return json_response(self, 502, {"ok": False, "error": "missing_google_email"})
        with get_db() as db:
            row = db.execute("select * from users where email = ?", (email,)).fetchone()
            if not row:
                user_id = secrets.token_hex(8)
                db.execute(
                    """
                    insert into users (id, email, display_name, provider, plan, status, risk, created_at, last_seen_at)
                    values (?, ?, ?, 'google', 'Free', 'active', 'normal', ?, ?)
                    """,
                    (user_id, email, display_name, now(), now()),
                )
                log_event(db, email, "auth.google_signup", user_id, "success", "google signup")
                row = db.execute("select * from users where id = ?", (user_id,)).fetchone()
            else:
                db.execute("update users set last_seen_at = ? where id = ?", (now(), row["id"]))
                log_event(db, email, "auth.google_login", row["id"], "success", "google login")
                row = db.execute("select * from users where id = ?", (row["id"],)).fetchone()
        user = public_user(row)
        dashboard_user = {
            "nickname": user["displayName"],
            "email": user["email"],
            "plan": user["plan"],
        }
        user_json = json.dumps(dashboard_user, ensure_ascii=False).replace("</", "<\\/")
        dashboard_url = f"{APP_ROOT}/dashboard.html"
        return html_response(
            self,
            200,
            f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MCPWorld 로그인 완료</title>
</head>
<body>
  <p>Google 로그인 완료. 대시보드로 이동합니다.</p>
  <script>
    sessionStorage.setItem('mcpworld_demo_user', JSON.stringify({user_json}));
    window.location.replace({json.dumps(dashboard_url)});
  </script>
</body>
    </html>""",
            extra_headers=[("Set-Cookie", auth_cookie_header(user["id"]))],
        )

    def signup(self):
        body = read_body(self)
        email = (body.get("email") or "").strip().lower()
        display_name = (body.get("displayName") or "").strip()
        password = body.get("password") or ""
        if not email or not display_name or len(password) < 8:
            return json_response(self, 400, {"ok": False, "error": "invalid_signup"})
        with get_db() as db:
            try:
                user_id = secrets.token_hex(8)
                db.execute(
                    """
                    insert into users (id, email, display_name, password_hash, provider, plan, status, risk, created_at, last_seen_at)
                    values (?, ?, ?, ?, 'email', 'Free', 'active', 'normal', ?, ?)
                    """,
                    (user_id, email, display_name, hash_secret(password), now(), now()),
                )
                log_event(db, email, "auth.signup", user_id, "success", "email signup")
            except sqlite3.IntegrityError:
                return json_response(self, 409, {"ok": False, "error": "email_exists"})
            row = db.execute("select * from users where id = ?", (user_id,)).fetchone()
        return json_response(self, 200, {"ok": True, "user": public_user(row)}, extra_headers=[("Set-Cookie", auth_cookie_header(row["id"]))])

    def login(self):
        body = read_body(self)
        identifier = (body.get("identifier") or "").strip().lower()
        password = body.get("password") or ""
        if identifier == "demo":
            identifier = "demo@mcpworld.local"
        with get_db() as db:
            row = db.execute("select * from users where email = ?", (identifier,)).fetchone()
            if not row or row["password_hash"] != hash_secret(password):
                log_event(db, identifier or "unknown", "auth.login", identifier or "unknown", "error", "login failed")
                return json_response(self, 401, {"ok": False, "error": "invalid_credentials"})
            db.execute("update users set last_seen_at = ? where id = ?", (now(), row["id"]))
            log_event(db, row["email"], "auth.login", row["id"], "success", "login success")
            row = db.execute("select * from users where id = ?", (row["id"],)).fetchone()
        return json_response(self, 200, {"ok": True, "user": public_user(row)}, extra_headers=[("Set-Cookie", auth_cookie_header(row["id"]))])

    def checkout(self):
        body = read_body(self)
        provider = os.environ.get("BILLING_PROVIDER", "manual")
        plan = body.get("plan") or "Pro"
        if provider == "manual":
            return json_response(
                self,
                503,
                {
                    "ok": False,
                    "error": "needs_config",
                    "message": "Set BILLING_PROVIDER and provider keys for hosted checkout.",
                    "plan": plan,
                },
            )
        return json_response(self, 200, {"ok": True, "provider": provider, "checkoutUrl": os.environ.get("BILLING_CHECKOUT_URL", APP_ROOT)})

    def billing_webhook(self):
        raw = read_body(self)
        secret = os.environ.get("BILLING_WEBHOOK_SECRET")
        signature = self.headers.get("X-MCPWorld-Signature", "")
        if secret:
            expected = hmac.new(secret.encode("utf-8"), json.dumps(raw, sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return json_response(self, 401, {"ok": False, "error": "bad_signature"})
        with get_db() as db:
            db.execute(
                "insert into billing_events (at, provider, event_id, status, payload) values (?, ?, ?, 'received', ?)",
                (now(), raw.get("provider", "unknown"), raw.get("id"), json.dumps(raw, ensure_ascii=False)),
            )
            log_event(db, "billing", "billing.webhook", raw.get("id", "event"), "success", "billing webhook received")
        return json_response(self, 200, {"ok": True})

    def issue_session(self):
        body = read_body(self)
        email = (body.get("email") or "demo@mcpworld.local").strip().lower()
        tool = (body.get("tool") or "word").strip().lower()
        if tool not in SESSION_TOOL_IDS:
            return json_response(self, 400, {"ok": False, "error": "unknown_connector"})
        with get_db() as db:
            user = db.execute("select * from users where email = ?", (email,)).fetchone()
            if not user:
                return json_response(self, 404, {"ok": False, "error": "user_not_found"})
            session = create_session(db, user["id"], tool)
        return json_response(self, 200, {"ok": True, "session": session})

    def session_links(self, regenerate=False):
        body = read_body(self)
        email = (body.get("email") or "demo@mcpworld.local").strip().lower()
        current_time = now()
        with get_db() as db:
            user = db.execute("select * from users where email = ?", (email,)).fetchone()
            if not user:
                return json_response(self, 404, {"ok": False, "error": "user_not_found"})
            if regenerate:
                db.execute(
                    """
                    update sessions
                    set status = 'terminated', ended_at = ?
                    where user_id = ? and status = 'active'
                    """,
                    (current_time, user["id"]),
                )
                log_event(db, email, "session.regenerate", user["id"], "success", "active connector links terminated before regeneration")

            sessions = []
            for connector in CONNECTOR_CATALOG:
                tool = connector["slug"]
                row = None
                if not regenerate:
                    row = db.execute(
                        """
                        select * from sessions
                        where user_id = ? and tool = ? and status = 'active' and expires_at > ?
                        order by created_at desc
                        limit 1
                        """,
                        (user["id"], tool, current_time),
                    ).fetchone()
                if row:
                    sessions.append(
                        {
                            "id": row["id"],
                            "tool": row["tool"],
                            "route": row["route"],
                            "expiresAt": row["expires_at"],
                            "status": row["status"],
                        }
                    )
                else:
                    sessions.append(create_session(db, user["id"], tool))
        return json_response(self, 200, {"ok": True, "regenerated": regenerate, "sessions": sessions})

    def terminate_session(self, session_id):
        with get_db() as db:
            db.execute("update sessions set status = 'terminated', ended_at = ? where id = ?", (now(), session_id))
            log_event(db, "operator", "session.terminate", session_id, "success", "session terminated")
        return json_response(self, 200, {"ok": True, "sessionId": session_id, "status": "terminated"})

    def register_agent(self):
        body = read_body(self)
        email = (body.get("email") or "demo@mcpworld.local").strip().lower()
        device = body.get("deviceName") or "Windows PC"
        with get_db() as db:
            user = db.execute("select * from users where email = ?", (email,)).fetchone()
            if not user:
                return json_response(self, 404, {"ok": False, "error": "user_not_found"})
            agent_id = body.get("agentId") or "agent-" + secrets.token_hex(4)
            db.execute(
                "insert or replace into agents (id, user_id, device_name, status, last_seen_at) values (?, ?, ?, 'online', ?)",
                (agent_id, user["id"], device, now()),
            )
            log_event(db, email, "agent.register", agent_id, "success", f"{device} registered")
        return json_response(self, 200, {"ok": True, "agentId": agent_id, "status": "online"})


    def enqueue_tool_call(self):
        body = read_body(self)
        session_id = body.get("sessionId") or ""
        tool_name = body.get("toolName") or ""
        arguments = body.get("arguments") or {}
        if tool_name not in TOOL_IDS:
            return json_response(self, 400, {"ok": False, "error": "unknown_tool"})
        with get_db() as db:
            session = db.execute("select * from sessions where id = ?", (session_id,)).fetchone()
            if not session or session["status"] != "active" or session["expires_at"] < now():
                return json_response(self, 404, {"ok": False, "error": "active_session_not_found"})
            allowed_tools = SESSION_TOOL_ALLOWLIST.get(session["tool"], {"system.ping"})
            if tool_name not in allowed_tools:
                return json_response(self, 403, {"ok": False, "error": "tool_not_allowed_for_session", "sessionTool": session["tool"]})
            call_id = "call-" + secrets.token_hex(6)
            db.execute(
                """
                insert into tool_calls (id, session_id, user_id, tool_name, arguments_json, status, created_at, updated_at)
                values (?, ?, ?, ?, ?, 'queued', ?, ?)
                """,
                (call_id, session_id, session["user_id"], tool_name, json.dumps(arguments, ensure_ascii=False), now(), now()),
            )
            log_event(db, "relay", "tool.enqueue", call_id, "success", f"{tool_name} queued for agent")
        return json_response(self, 200, {"ok": True, "callId": call_id, "status": "queued"})

    def get_tool_call(self, call_id):
        with get_db() as db:
            row = db.execute("select * from tool_calls where id = ?", (call_id,)).fetchone()
            if not row:
                return json_response(self, 404, {"ok": False, "error": "call_not_found"})
        return json_response(
            self,
            200,
            {
                "ok": True,
                "call": {
                    "id": row["id"],
                    "sessionId": row["session_id"],
                    "toolName": row["tool_name"],
                    "arguments": json.loads(row["arguments_json"]),
                    "status": row["status"],
                    "result": json.loads(row["result_json"]) if row["result_json"] else None,
                    "error": row["error"],
                },
            },
        )

    def agent_poll(self):
        body = read_body(self)
        agent_id = body.get("agentId") or ""
        email = (body.get("email") or "").strip().lower()
        with get_db() as db:
            user = db.execute("select * from users where email = ?", (email,)).fetchone()
            if not user:
                return json_response(self, 404, {"ok": False, "error": "user_not_found"})
            db.execute("update agents set status = 'online', last_seen_at = ? where id = ? and user_id = ?", (now(), agent_id, user["id"]))
            row = db.execute(
                """
                select * from tool_calls
                where user_id = ? and status = 'queued'
                order by created_at asc
                limit 1
                """,
                (user["id"],),
            ).fetchone()
            if not row:
                return json_response(self, 200, {"ok": True, "call": None})
            db.execute("update tool_calls set status = 'running', agent_id = ?, updated_at = ? where id = ?", (agent_id, now(), row["id"]))
            log_event(db, email, "tool.dispatch", row["id"], "success", f"{row['tool_name']} dispatched to agent")
        return json_response(self, 200, {"ok": True, "call": {"id": row["id"], "sessionId": row["session_id"], "toolName": row["tool_name"], "arguments": json.loads(row["arguments_json"])}})

    def agent_result(self):
        body = read_body(self)
        call_id = body.get("callId") or ""
        status = body.get("status") or "done"
        result = body.get("result")
        error = body.get("error")
        if status not in {"done", "error"}:
            return json_response(self, 400, {"ok": False, "error": "bad_status"})
        with get_db() as db:
            db.execute(
                "update tool_calls set status = ?, result_json = ?, error = ?, updated_at = ? where id = ?",
                (status, json.dumps(result, ensure_ascii=False) if result is not None else None, error, now(), call_id),
            )
            log_event(db, "agent", "tool.result", call_id, "success" if status == "done" else "error", status)
        return json_response(self, 200, {"ok": True, "callId": call_id, "status": status})

    def relay_status(self, path, query):
        parts = path.strip("/").split("/")
        tool = parts[4] if len(parts) >= 5 else "unknown"
        session_id = (query.get("session") or [""])[0]
        token = (query.get("token") or [""])[0]
        with get_db() as db:
            session = db.execute("select * from sessions where id = ?", (session_id,)).fetchone()
            if not session:
                return json_response(self, 404, {"ok": False, "error": "session_not_found"})
            if session["expires_at"] < now() or session["status"] != "active":
                return json_response(self, 410, {"ok": False, "error": "session_expired"})
            if not token or session["token_hash"] != hash_secret(token):
                return json_response(self, 401, {"ok": False, "error": "bad_token"})
        return json_response(
            self,
            200,
            {
                "ok": True,
                "tool": tool,
                "sessionId": session_id,
                "status": "waiting_agent",
                "message": "Session is valid. Tool calls should be enqueued through /api/tool-calls/enqueue and delivered to MCPWorld Agent through /api/agent/poll.",
            },
        )

    def auth_user(self):
        jar = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        morsel = jar.get(AUTH_COOKIE_NAME)
        if not morsel:
            return None
        user_id = verify_auth_session(morsel.value)
        if not user_id:
            return None
        with get_db() as db:
            row = db.execute("select * from users where id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def auth_me(self):
        user = self.auth_user()
        if not user:
            return json_response(self, 401, {"ok": False, "error": "not_authenticated"})
        public = public_user(user)
        return json_response(self, 200, {"ok": True, "user": public, "isAdmin": is_admin_email(user["email"])})

    def require_admin(self):
        user = self.auth_user()
        if not user or not is_admin_email(user["email"]):
            return None
        return user

    def admin_bootstrap(self, query):
        actor = self.require_admin()
        if not actor:
            return json_response(self, 403, {"ok": False, "error": "admin_forbidden"})
        with get_db() as db:
            users = [public_user(row) for row in db.execute("select * from users order by created_at desc").fetchall()]
            sessions = [dict(row) for row in db.execute("select * from sessions order by created_at desc limit 50").fetchall()]
            logs = [dict(row) for row in db.execute("select * from audit_logs order by at desc limit 80").fetchall()]
            unresolved = [
                {"id": "inc-relay-latency", "title": "Relay latency watch", "severity": "warning", "owner": "ops", "impact": "Monitor relay route latency."},
                {"id": "inc-billing-config", "title": "Billing provider config", "severity": "warning", "owner": "billing", "impact": "Hosted checkout is not configured."},
            ]
        return json_response(self, 200, {"ok": True, "users": users, "sessions": sessions, "logs": logs, "issues": unresolved})

    def admin_action(self):
        body = read_body(self)
        actor = self.require_admin()
        if not actor:
            return json_response(self, 403, {"ok": False, "error": "admin_forbidden"})
        action = body.get("action") or "unknown"
        target = body.get("target") or "system"
        with get_db() as db:
            if action == "lock-user":
                db.execute("update users set status = 'limited', risk = 'warning' where email = ?", (target,))
            elif action == "terminate-session":
                db.execute("update sessions set status = 'terminated', ended_at = ? where id = ?", (now(), target))
            log_event(db, actor["email"], f"admin.{action}", target, "success", f"operator action: {action}")
        return json_response(self, 200, {"ok": True, "action": action, "target": target})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), ApiHandler)
    print(f"MCP World API listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()
