import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("mcpworld_agent", ROOT / "agent" / "mcpworld_agent.py")
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


class FakeMcpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        if body["method"] == "tools/list":
            result = {"tools": [{"name": "echo", "description": "Echo test tool"}]}
        elif body["method"] == "tools/call":
            result = {"content": [{"type": "text", "text": json.dumps(body["params"], sort_keys=True)}]}
        else:
            result = {"unknown": body["method"]}
        payload = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


def with_fake_server(fn):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeMcpHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        return fn(server.server_address[1])
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_mcp_status_and_call_proxy():
    def run(port):
        config = {"path": "test-config.json", "mcps": {"office": {"id": "office", "name": "Office MCP", "local_port": port}}}
        status = agent.run_adapter("powerpoint.mcp.status", {}, config)
        assert status["reachable"] is True
        assert status["mcpId"] == "office"
        result = agent.run_adapter("powerpoint.mcp.call", {"tool": "echo", "arguments": {"value": 7}}, config)
        assert result["content"][0]["type"] == "text"
        assert '"name": "echo"' in result["content"][0]["text"]
    with_fake_server(run)


def test_missing_mcp_tool_name_is_actionable():
    config = {"path": "test-config.json", "mcps": {"office": {"id": "office", "local_port": 1}}}
    try:
        agent.run_adapter("powerpoint.mcp.call", {}, config)
    except ValueError as exc:
        assert "Missing MCP tool name" in str(exc)
    else:
        raise AssertionError("expected ValueError")


if __name__ == "__main__":
    test_mcp_status_and_call_proxy()
    test_missing_mcp_tool_name_is_actionable()
    print("PASS agent local MCP proxy tests")
