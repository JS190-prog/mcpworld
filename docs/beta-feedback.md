# Beta feedback intake

MCPWorld beta feedback should be routed through GitHub so public testers can see known issues and the VPS does not carry large support attachments.

## User routes

- Setup questions and general Q&A: GitHub Discussions
- Reproducible bugs: GitHub Issues, `Bug report`
- Agent registration, polling, or tool-call routing failures: GitHub Issues, `Connection problem`
- New connector or dashboard requests: GitHub Issues, `Feature request`

## Triage labels

- `beta`: all beta feedback
- `bug`: reproducible product defect
- `connection`: agent-to-VPS or queued tool-call problem
- `enhancement`: requested improvement
- `security`: local access, token, consent, or permission risk
- `docs`: documentation gap

## Operator triage order

1. Confirm whether the report contains secrets, private documents, or personal data. If it does, ask the reporter to remove it and rotate affected credentials.
2. Identify the failing step: download, install, version check, register, poll, enqueue, result, or admin review.
3. Reproduce with `system.ping` before debugging app-specific adapters.
4. If the issue affects all users, check VPS `/api/health`, `/api/tools/catalog`, and admin logs before changing the agent.
5. If the issue affects one user, check their agent version, Windows version, firewall/proxy context, and sanitized output.
6. Link the issue to the release tag that introduced or fixed it.

## Privacy rules for public reports

Do not ask beta users to upload local documents, proprietary drawings, raw screenshots containing customer data, API tokens, session IDs, payment details, or full local paths unless they have been sanitized.

## First beta acceptance signal

The beta feedback path is ready when a tester can open the website, download from the GitHub Release, ask a setup question in Discussions, and file a structured issue without needing private chat.
