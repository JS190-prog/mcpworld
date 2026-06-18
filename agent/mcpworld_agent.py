#!/usr/bin/env python3
import argparse
import json
import platform
import urllib.request


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="MCP World local agent bootstrap")
    parser.add_argument("--server", default="https://www.tornado616.cloud/mcpworld")
    parser.add_argument("--email", default="demo@mcpworld.local")
    parser.add_argument("--device-name", default=platform.node() or "Windows PC")
    parser.add_argument("--agent-id", default="")
    args = parser.parse_args()

    response = post_json(
        f"{args.server.rstrip('/')}/api/agent/register",
        {"email": args.email, "deviceName": args.device_name, "agentId": args.agent_id},
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))
    print("Agent registration complete. MCP streaming transport is configured in the next release step.")


if __name__ == "__main__":
    main()
