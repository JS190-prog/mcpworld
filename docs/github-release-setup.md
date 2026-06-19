# GitHub release setup for MCPWorld Agent

## Recommended public links

Replace `OWNER/REPO` after creating the public repository.

- Repository: `https://github.com/OWNER/REPO`
- Latest release: `https://github.com/OWNER/REPO/releases/latest`
- Issues: `https://github.com/OWNER/REPO/issues`
- Discussions: `https://github.com/OWNER/REPO/discussions`

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
powershell -ExecutionPolicy Bypass -File .\scripts\prepare_agent_release.ps1 -Version 0.2.0-beta.1 -GitHubRepo OWNER/REPO
```

The script writes:

- `release/latest.json`
- `release/SHA256SUMS.txt`

## Site integration

Update `site-config.js` once the repo exists:

```js
githubRepo: 'https://github.com/OWNER/REPO',
githubReleases: 'https://github.com/OWNER/REPO/releases/latest',
githubIssues: 'https://github.com/OWNER/REPO/issues',
githubDiscussions: 'https://github.com/OWNER/REPO/discussions'
```

Then upload the site to the VPS. Download buttons should send users to GitHub Releases instead of serving binaries from the VPS.
