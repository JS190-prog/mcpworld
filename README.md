# MCPWorld

MCPWorld is a beta SaaS gateway for routing approved MCP-style tool calls from a hosted VPS to one locally installed Windows agent.

## Beta architecture

- Users install MCPWorld Agent once.
- The VPS owns login, sessions, tool catalog, queueing, audit logs, and admin views.
- The local agent polls the VPS over outbound HTTPS and executes built-in adapters.
- Large installer files are distributed through GitHub Releases to keep VPS bandwidth low.

## Current beta scope

The current beta focuses on the minimum real operating path:

- `system.ping`
- `word.status`
- `powerpoint.status`
- `excel.status`
- `cad.status`
- `hwp.status`
- `photoshop.status`
- `blender.status`

Status adapters only check local app availability. Deeper file or UI automation should be added later with explicit allowlists and audit logging.

## Downloads

Use GitHub Releases:

- Latest release: https://github.com/JS190-prog/mcpworld/releases/tag/v0.2.0-beta.1
- Issues: https://github.com/JS190-prog/mcpworld/issues
- Discussions: https://github.com/JS190-prog/mcpworld/discussions

## Local smoke checks

```powershell
python -m py_compile .ackend\mcpworld_api.py .gent\mcpworld_agent.py
node --check .pp.js
node --check .\dashboard.js
node --check .dmindmin.js
powershell -ExecutionPolicy Bypass -File .\scripts\prepare_agent_release.ps1 -Version 0.2.0-beta.1 -GitHubRepo JS190-prog/mcpworld
```

## Important beta note

MCPWorld removes the need to install a separate MCP server for every supported app. It does not remove the need for the target local application itself when a tool controls Word, CAD, HWP, Photoshop, Blender, or similar software.
