# MCPWorld beta first-use guide

This guide is for beta testers who want to try the hosted MCPWorld site with the Windows agent distribution.

## 1. Open the beta site

Use the hosted site:

- https://www.tornado616.cloud/mcpworld/

Open the dashboard from the main page or go directly to:

- https://www.tornado616.cloud/mcpworld/dashboard.html

## 2. Download the agent

Download the current beta agent from GitHub Releases:

- https://github.com/JS190-prog/mcpworld/releases/tag/v0.2.0-beta.1

Recommended files:

- `MCPWorld-Agent-Setup.exe`: normal Windows beta install path.
- `MCPWorld-Agent-Setup.msi`: managed or enterprise install path.
- `mcpworld-agent.zip`: manual recovery or smoke-test package.
- `SHA256SUMS.txt`: checksum verification.

The installers are beta builds and may show a Windows SmartScreen warning because code signing is not configured yet.

## 3. Confirm the agent version

If you use the standalone executable, confirm the version before testing:

```powershell
mcpworld-agent.exe --version
```

Expected beta version:

```text
0.2.0-beta.1
```

## 4. Sign in to the dashboard

For the current beta, use the demo account shown on the site:

```text
ID: demo
Password: demo1234
```

After sign-in, the dashboard should show the local agent area and supported tool cards.

## 5. What should work in this beta

The beta is focused on the minimum hosted relay path:

1. The VPS API is reachable.
2. The tool catalog includes `system.ping`.
3. The agent can register against the beta account.
4. A `system.ping` call can be queued.
5. The agent can poll the VPS and return a result.

Current app adapters only check whether local applications appear available. Deep Word, CAD, HWP, Photoshop, or Blender automation is not part of this beta acceptance path yet.

## 6. Where to ask questions or report issues

Use public GitHub channels so known issues are visible to other testers:

- Setup questions: https://github.com/JS190-prog/mcpworld/discussions
- Bugs and connection failures: https://github.com/JS190-prog/mcpworld/issues/new/choose
- Release downloads: https://github.com/JS190-prog/mcpworld/releases/tag/v0.2.0-beta.1

## 7. Do not post private data

Do not upload or paste:

- Local documents, drawings, spreadsheets, or customer files.
- API keys, tokens, session IDs, cookies, or passwords.
- Payment information.
- Full local paths that reveal private names or client names.
- Screenshots containing confidential documents or account details.

Sanitize logs before posting them to GitHub Issues or Discussions.

## 8. Quick beta checklist

- [ ] Site opens.
- [ ] Dashboard opens.
- [ ] Agent release page opens.
- [ ] Agent version is `0.2.0-beta.1`.
- [ ] Demo login works.
- [ ] `system.ping` or the dashboard status flow can be tested.
- [ ] Questions and bugs can be filed through GitHub.