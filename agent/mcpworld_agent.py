#!/usr/bin/env python3
import argparse
import json
import platform
import shutil
import time
import urllib.request

AGENT_VERSION = "0.2.0-beta.1"


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))


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


def run_adapter(tool_name, arguments):
    if tool_name == "system.ping":
        return {
            "pong": True,
            "device": platform.node() or "Windows PC",
            "platform": platform.platform(),
            "arguments": arguments,
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
    if tool_name in status_tools:
        label, candidates = status_tools[tool_name]
        return app_status(label, candidates, arguments)

    raise ValueError(f"Unsupported MCPWorld tool: {tool_name}")


def poll_once(server, email, agent_id):
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
        result = run_adapter(tool_name, arguments)
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
    parser.add_argument("--email", default="demo@mcpworld.local")
    parser.add_argument("--device-name", default=platform.node() or "Windows PC")
    parser.add_argument("--agent-id", default="")
    parser.add_argument("--poll-once", action="store_true", help="Fetch and execute one queued tool call, then exit.")
    parser.add_argument("--poll-interval", type=int, default=0, help="Poll continuously every N seconds. Use 0 to only register.")
    parser.add_argument("--version", action="store_true", help="Print the agent version and exit.")
    args = parser.parse_args()

    if args.version:
        print(AGENT_VERSION)
        return

    response = post_json(
        f"{args.server.rstrip('/')}/api/agent/register",
        {"email": args.email, "deviceName": args.device_name, "agentId": args.agent_id},
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))
    agent_id = response.get("agentId") or args.agent_id

    if args.poll_once:
        poll_once(args.server, args.email, agent_id)
        return

    if args.poll_interval > 0:
        print(f"Polling {args.server.rstrip('/')} every {args.poll_interval}s as {agent_id}.")
        while True:
            poll_once(args.server, args.email, agent_id)
            time.sleep(args.poll_interval)
        return

    print("Agent registration complete. Use --poll-once or --poll-interval 5 to receive VPS tool calls.")


if __name__ == "__main__":
    main()
