#!/usr/bin/env python3
import argparse
import json
import os
import platform
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    # Stamped by scripts/build_agent_release.ps1 at build time so the shipped
    # binary reports the exact released version (used for channel update checks).
    from _agent_version import VERSION as AGENT_VERSION
except Exception:
    AGENT_VERSION = "0.2.0-beta.2"  # dev fallback; build injects the real version
DEFAULT_CONFIG_PATHS = [
    Path(os.environ.get("MCPWORLD_LOCAL_MCP_CONFIG", "")) if os.environ.get("MCPWORLD_LOCAL_MCP_CONFIG") else None,
    Path.home() / ".mcpworld" / "config.json",
    Path("C:/scratch/mcpworld/config.json"),
]
MCP_ID_ALIASES = {
    "word": "office",
    "powerpoint": "office",
    "excel": "office",
    "office": "office",
    "cad": "cad",
    "hwp": "hwp",
    "photoshop": "photoshop",
    "blender": "blender",
    "localcode": "localcode",
    "opencrab": "opencrab",
}


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"MCPWorld-Agent/{AGENT_VERSION}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))


# --------------------------------------------------------------------------- #
# 자동 업데이트 엔진 (stable 채널 매니페스트 폴링 -> 버전 비교)
# 순수 함수(_version_key/update_decision)는 단위 테스트 대상.
# --------------------------------------------------------------------------- #
def _version_key(version):
    """'0.2.0-beta.2' -> 비교 가능한 튜플. 안정판(pre 없음)이 같은 코어의 prerelease보다 높다."""
    version = str(version or "").strip().lstrip("v")
    core, _, pre = version.partition("-")
    nums = []
    for part in core.split("."):
        try:
            nums.append(int(part))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    if not pre:
        return (nums[0], nums[1], nums[2], 1, ())  # 안정판: 4번째 1 (prerelease보다 높음)
    pre_key = []
    for token in pre.replace("-", ".").split("."):
        if token.isdigit():
            pre_key.append((0, int(token), ""))  # 숫자 식별자 < 영문 식별자 (semver)
        else:
            pre_key.append((1, 0, token))
    return (nums[0], nums[1], nums[2], 0, tuple(pre_key))


def update_decision(current, manifest):
    """현재 버전 + stable 매니페스트 -> 업데이트 판단(순수). forced = 최소버전 미만."""
    target = str(manifest.get("version", "")).strip()
    minimum = str(manifest.get("minimumAgentVersion", target)).strip()
    cur_k = _version_key(current)
    assets = manifest.get("assets", {}) or {}
    exe = assets.get("exe", {}) or {}
    return {
        "current": current,
        "target": target,
        "minimum": minimum,
        "update_available": bool(target) and _version_key(target) > cur_k,
        "forced": bool(minimum) and cur_k < _version_key(minimum),
        "asset_url": exe.get("url"),
        "sha256": exe.get("sha256"),
    }


def manifest_url_for(server, override=None):
    if override:
        return override
    env = os.environ.get("MCPWORLD_UPDATE_MANIFEST_URL")
    if env:
        return env
    return f"{server.rstrip('/')}/release/stable.json"


def fetch_manifest(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": f"MCPWorld-Agent/{AGENT_VERSION}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))


def check_for_update(server, manifest_url=None, current=AGENT_VERSION):
    url = manifest_url_for(server, manifest_url)
    decision = update_decision(current, fetch_manifest(url))
    decision["manifest_url"] = url
    return decision


def load_local_mcp_config(config_path=None):
    paths = [Path(config_path)] if config_path else [path for path in DEFAULT_CONFIG_PATHS if path]
    for path in paths:
        if path.is_file():
            with path.open("r", encoding="utf-8") as handle:
                config = json.load(handle)
            mcps = config.get("mcps") or []
            return {
                "path": str(path),
                "mcps": {str(item.get("id") or "").lower(): item for item in mcps if item.get("id")},
            }
    return {"path": None, "mcps": {}}


def find_executable(candidates):
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def app_status(label, candidates, arguments):
    executable = find_executable(candidates)
    return {
        "available": executable is not None,
        "app": label,
        "executable": executable,
        "arguments": arguments,
        "note": "Local app was found on PATH." if executable else "Local app was not found on PATH. Install the target app or add it to PATH.",
    }


def get_mcp_entry(config, target):
    mcp_id = MCP_ID_ALIASES.get(target, target)
    entry = config["mcps"].get(mcp_id)
    if not entry:
        raise ValueError(
            f"Local MCP config does not contain '{mcp_id}'. Set MCPWORLD_LOCAL_MCP_CONFIG or add the MCP entry."
        )
    return mcp_id, entry


def local_mcp_url(entry):
    if entry.get("local_url"):
        return entry["local_url"].rstrip("/")
    port = entry.get("local_port")
    if not port:
        raise ValueError("Local MCP entry is missing local_port or local_url.")
    return f"http://127.0.0.1:{int(port)}/mcp"


def call_local_mcp(entry, method, params):
    payload = {"jsonrpc": "2.0", "id": f"mcpworld-{int(time.time() * 1000)}", "method": method, "params": params}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        local_mcp_url(entry),
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise ValueError(f"Local MCP endpoint is not reachable: {exc}") from exc
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    if isinstance(body, dict) and body.get("error"):
        raise ValueError(json.dumps(body["error"], ensure_ascii=False))
    return body.get("result", body) if isinstance(body, dict) else body


def mcp_status(target, config):
    mcp_id, entry = get_mcp_entry(config, target)
    result = {
        "available": True,
        "mcpId": mcp_id,
        "name": entry.get("name") or mcp_id,
        "configPath": config["path"],
        "localUrl": local_mcp_url(entry),
        "appHint": entry.get("app_hint"),
    }
    try:
        result["tools"] = call_local_mcp(entry, "tools/list", {})
        result["reachable"] = True
    except Exception as exc:
        result["reachable"] = False
        result["error"] = str(exc)
    return result


def mcp_tool_call(target, arguments, config):
    tool = arguments.get("tool") or arguments.get("name")
    tool_arguments = arguments.get("arguments") or {}
    if not tool:
        raise ValueError("Missing MCP tool name. Pass {'tool': '<tool_name>', 'arguments': {...}}.")
    _mcp_id, entry = get_mcp_entry(config, target)
    return call_local_mcp(entry, "tools/call", {"name": tool, "arguments": tool_arguments})


def run_adapter(tool_name, arguments, config=None):
    config = config or load_local_mcp_config()
    if tool_name == "system.ping":
        return {
            "pong": True,
            "device": platform.node() or "Windows PC",
            "platform": platform.platform(),
            "arguments": arguments,
            "localMcpConfig": config["path"],
        }

    status_tools = {
        "word.status": ("Word", ["WINWORD.EXE", "winword"]),
        "powerpoint.status": ("PowerPoint", ["POWERPNT.EXE", "powerpnt"]),
        "excel.status": ("Excel", ["EXCEL.EXE", "excel"]),
        "cad.status": ("CAD", ["ZWCAD.exe", "acad.exe", "gstarcad.exe", "zwcad", "acad", "gstarcad"]),
        "hwp.status": ("Hancom HWP", ["Hwp.exe", "hwp"]),
        "photoshop.status": ("Photoshop", ["Photoshop.exe", "photoshop"]),
        "blender.status": ("Blender", ["blender.exe", "blender"]),
    }
    if tool_name.endswith(".status") and not tool_name.endswith(".mcp.status"):
        target = tool_name.split(".", 1)[0]
        if tool_name in status_tools:
            label, candidates = status_tools[tool_name]
            result = app_status(label, candidates, arguments)
        else:
            # No-app connector (e.g. localcode): there is no desktop app process to
            # probe; availability is determined by local MCP reachability below.
            result = {
                "available": True,
                "app": target,
                "executable": None,
                "arguments": arguments,
                "note": "No local desktop app required; this connector relays to a local MCP server.",
            }
        try:
            result["mcp"] = mcp_status(target, config)
        except Exception as exc:
            result["mcp"] = {"reachable": False, "error": str(exc), "configPath": config["path"]}
        return result

    if tool_name.endswith(".mcp.status"):
        return mcp_status(tool_name.split(".", 1)[0], config)

    if tool_name.endswith(".mcp.call"):
        return mcp_tool_call(tool_name.split(".", 1)[0], arguments, config)

    raise ValueError(f"Unsupported MCPWorld tool: {tool_name}")


def poll_once(server, email, agent_id, config):
    call_response = post_json(
        f"{server.rstrip('/')}/api/agent/poll",
        {"email": email, "agentId": agent_id},
    )
    call = call_response.get("call")
    if not call:
        print("No queued tool calls.")
        return call_response

    call_id = call["id"]
    tool_name = call["toolName"]
    arguments = call.get("arguments") or {}
    try:
        result = run_adapter(tool_name, arguments, config)
        status = "done"
        error = None
    except Exception as exc:
        result = None
        status = "error"
        error = str(exc)

    result_response = post_json(
        f"{server.rstrip('/')}/api/agent/result",
        {"callId": call_id, "status": status, "result": result, "error": error},
    )
    print(json.dumps({"call": call, "result": result_response}, ensure_ascii=False, indent=2))
    return result_response


def main():
    parser = argparse.ArgumentParser(description="MCP World local agent bootstrap")
    parser.add_argument("--server", default="https://www.tornado616.cloud/mcpworld")
    parser.add_argument("--email", default=os.environ.get("MCPWORLD_AGENT_EMAIL", ""))
    parser.add_argument("--device-name", default=platform.node() or "Windows PC")
    parser.add_argument("--agent-id", default="")
    parser.add_argument("--mcp-config", default=os.environ.get("MCPWORLD_LOCAL_MCP_CONFIG", ""), help="Path to the local MCP World config.json.")
    parser.add_argument("--poll-once", action="store_true", help="Fetch and execute one queued tool call, then exit.")
    parser.add_argument("--poll-interval", type=int, default=0, help="Poll continuously every N seconds. Use 0 to only register.")
    parser.add_argument("--version", action="store_true", help="Print the agent version and exit.")
    parser.add_argument("--check-update", action="store_true", help="Check the stable channel for a newer agent and exit.")
    parser.add_argument("--manifest-url", default="", help="Override the update manifest URL (default {server}/release/stable.json).")
    args = parser.parse_args()

    if args.version:
        print(AGENT_VERSION)
        return
    if args.check_update:
        print(json.dumps(check_for_update(args.server, args.manifest_url or None), ensure_ascii=False, indent=2))
        return
    if not args.email:
        parser.error("--email or MCPWORLD_AGENT_EMAIL is required")

    local_config = load_local_mcp_config(args.mcp_config or None)

    response = post_json(
        f"{args.server.rstrip('/')}/api/agent/register",
        {"email": args.email, "deviceName": args.device_name, "agentId": args.agent_id},
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))
    agent_id = response.get("agentId") or args.agent_id

    if args.poll_once:
        poll_once(args.server, args.email, agent_id, local_config)
        return

    if args.poll_interval > 0:
        print(f"Polling {args.server.rstrip('/')} every {args.poll_interval}s as {agent_id}.")
        while True:
            poll_once(args.server, args.email, agent_id, local_config)
            time.sleep(args.poll_interval)
        return

    print("Agent registration complete. Use --poll-once or --poll-interval 5 to receive VPS tool calls.")


if __name__ == "__main__":
    main()
