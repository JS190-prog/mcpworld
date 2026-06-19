# MCPWorld beta test runbook

## Beta goal

Run the smallest real operating path before adding deep app automation:

1. User opens the MCPWorld site.
2. User downloads MCPWorld Agent from GitHub Releases.
3. Agent registers with the VPS API.
4. VPS issues a connector session.
5. A tool call is queued.
6. Agent polls the VPS over outbound HTTPS.
7. Agent returns a result.
8. Admin can inspect users, sessions, logs, and incidents.

## Release hosting model

Large binaries should live on GitHub Releases, not on the VPS.

- `MCPWorld-Agent-Setup.exe`: general Windows users.
- `MCPWorld-Agent-Setup.msi`: managed or enterprise deployment.
- `mcpworld-agent.zip`: manual install, smoke test, and recovery.
- `SHA256SUMS.txt`: checksum verification.
- `latest.json`: update manifest pointing to GitHub release assets.

The VPS should serve only the site, API, dashboard, admin console, and a small manifest or links page.

## Beta 1 acceptance checklist

- [ ] GitHub repository URL replaces `OWNER/REPO` in `site-config.js`.
- [ ] GitHub Releases has a `v0.2.0-beta.1` release.
- [ ] Release includes ZIP, EXE if available, MSI if available, and checksums.
- [ ] Main site download link opens GitHub Releases latest page.
- [ ] Dashboard install button opens GitHub Releases latest page.
- [ ] `/api/health` returns `ok: true` on the VPS.
- [ ] `/api/tools/catalog` returns at least `system.ping`.
- [ ] Agent registration succeeds for the beta account.
- [ ] `system.ping` returns `done` through the queued tool-call flow.
- [ ] First beta tester can file a GitHub Issue or Discussion.

## Smoke test commands

Local API smoke test should cover:

```text
GET /api/tools/catalog
POST /api/auth/login
POST /api/sessions/issue
POST /api/tool-calls/enqueue
POST /api/agent/register
POST /api/agent/poll
POST /api/agent/result
GET /api/tool-calls/{call_id}
```

## Rollback

Use git commits for site/API rollback and GitHub Releases for binary rollback. If a bad agent is published, mark the release as pre-release or remove the affected asset, then publish a corrected manifest.
