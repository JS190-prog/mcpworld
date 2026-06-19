# GitHub release setup for MCPWorld Agent

## Recommended public links

The planned public repository is `JS190-prog/mcpworld`.

- Repository: `https://github.com/JS190-prog/mcpworld`
- Latest release: `https://github.com/JS190-prog/mcpworld/releases/latest`
- Issues: `https://github.com/JS190-prog/mcpworld/issues`
- Discussions: `https://github.com/JS190-prog/mcpworld/discussions`

## Release asset policy

Upload large files to GitHub Releases. Keep the VPS light.

Required for beta:

- `mcpworld-agent.zip`
- `SHA256SUMS.txt`
- `latest.json`

Recommended for public beta:

- `MCPWorld-Agent-Setup.exe`
- `MCPWorld-Agent-Setup.msi`

## Prepare manifest

Run from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepare_agent_release.ps1 -Version 0.2.0-beta.1 -GitHubRepo JS190-prog/mcpworld
```

The script writes:

- `release/latest.json`
- `release/SHA256SUMS.txt`

## Site integration

Update `site-config.js` once the repo exists:

```js
githubRepo: 'https://github.com/JS190-prog/mcpworld',
githubReleases: 'https://github.com/JS190-prog/mcpworld/releases/latest',
githubIssues: 'https://github.com/JS190-prog/mcpworld/issues',
githubDiscussions: 'https://github.com/JS190-prog/mcpworld/discussions'
```

Then upload the site to the VPS. Download buttons should send users to GitHub Releases instead of serving binaries from the VPS.
