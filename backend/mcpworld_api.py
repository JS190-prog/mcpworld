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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_ROOT = os.environ.get("MCPWORLD_PUBLIC_URL", "https://www.tornado616.cloud/mcpworld").rstrip("/")
DB_PATH = Path(os.environ.get("MCPWORLD_DB", "/var/lib/mcpworld/mcpworld.sqlite3"))
HOST = os.environ.get("MCPWORLD_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCPWORLD_PORT", "33210"))
TOKEN_TTL_SECONDS = int(os.environ.get("MCPWORLD_SESSION_TTL_SECONDS", "3600"))


TOOL_CATALOG = [
    {"id": "system.ping", "category": "system", "label": "Agent ping", "description": "Verify MCPWorld Agent can receive and answer tool calls.", "requiresLocalApp": False},
    {"id": "word.status", "category": "office", "label": "Word status", "description": "Check whether Word automation is available on the user's PC.", "requiresLocalApp": True},
    {"id": "powerpoint.status", "category": "office", "label": "PowerPoint status", "description": "Check whether PowerPoint automation is available on the user's PC.", "requiresLocalApp": True},
    {"id": "excel.status", "category": "office", "label": "Excel status", "description": "Check whether Excel automation is available on the user's PC.", "requiresLocalApp": True},
    {"id": "cad.status", "category": "cad", "label": "CAD status", "description": "Check whether AutoCAD/GstarCAD/ZWCAD automation is available on the user's PC.", "requiresLocalApp": True},
    {"id": "hwp.status", "category": "document", "label": "HWP status", "description": "Check whether Hancom HWP automation is available on the user's PC.", "requiresLocalApp": True},
    {"id": "photoshop.status", "category": "creative", "label": "Photoshop status", "description": "Check whether Photoshop automation is available on the user's PC.", "requiresLocalApp": True},
    {"id": "blender.status", "category": "creative", "label": "Blender status", "description": "Check whether Blender automation is available on the user's PC.", "requiresLocalApp": True},
]


def now() -> int:
    return int(time.time())


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
    session_id = "ses-" + secrets.token_hex(5)
    expires_at = now() + TOKEN_TTL_SECONDS
    user = db.execute("select email from users where id = ?", (user_id,)).fetchone()
    user_key = urllib.parse.quote((user["email"].split("@")[0] if user else "demo").lower())
    route = f"{APP_ROOT}/relay/u/{user_key}/mcp/{tool}?session={session_id}&token={token}"
    db.execute(
        """
        insert into sessions (id, user_id, tool, token_hash, route, status, relay_status, created_at, expires_at)
        values (?, ?, ?, ?, ?, 'active', 'waiting_agent', ?, ?)
        """,
        (session_id, user_id, tool, hash_secret(token), route, now(), expires_at),
    )
    log_event(db, user["email"] if user else "system", "session.issue", session_id, "success", f"{tool} connector issued")
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
            if path == "/admin/bootstrap":
                return self.admin_bootstrap()
            if path == "/tools/catalog":
                return json_response(self, 200, {"ok": True, "tools": TOOL_CATALOG})
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
        if path.startswith("/api/"):
            path = path[4:]
        try:
            if path == "/auth/signup":
                return self.signup()
            if path == "/auth/login":
                return self.login()
            if path == "/billing/checkout":
                return self.checkout()
            if path == "/billing/webhook":
                return self.billing_webhook()
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

    def google_url(self):
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", f"{APP_ROOT}/api/auth/google/callback")
        if not client_id:
            return json_response(self, 503, {"ok": False, "error": "needs_config", "missing": ["GOOGLE_CLIENT_ID"]})
        state = secrets.token_urlsafe(18)
        params = urllib.parse.urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
            }
        )
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
        return json_response(self, 200, {"ok": True, "user": public_user(row)})

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
        return json_response(self, 200, {"ok": True, "user": public_user(row)})

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
        return json_response(self, 200, {"ok": True, "user": public_user(row)})

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
        with get_db() as db:
            user = db.execute("select * from users where email = ?", (email,)).fetchone()
            if not user:
                return json_response(self, 404, {"ok": False, "error": "user_not_found"})
            session = create_session(db, user["id"], tool)
        return json_response(self, 200, {"ok": True, "session": session})

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
        if tool_name not in {tool["id"] for tool in TOOL_CATALOG}:
            return json_response(self, 400, {"ok": False, "error": "unknown_tool"})
        with get_db() as db:
            session = db.execute("select * from sessions where id = ?", (session_id,)).fetchone()
            if not session or session["status"] != "active" or session["expires_at"] < now():
                return json_response(self, 404, {"ok": False, "error": "active_session_not_found"})
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

    def admin_bootstrap(self):
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
        action = body.get("action") or "unknown"
        target = body.get("target") or "system"
        with get_db() as db:
            if action == "lock-user":
                db.execute("update users set status = 'limited', risk = 'warning' where email = ?", (target,))
            elif action == "terminate-session":
                db.execute("update sessions set status = 'terminated', ended_at = ? where id = ?", (now(), target))
            log_event(db, "operator", f"admin.{action}", target, "success", f"operator action: {action}")
        return json_response(self, 200, {"ok": True, "action": action, "target": target})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), ApiHandler)
    print(f"MCP World API listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()
