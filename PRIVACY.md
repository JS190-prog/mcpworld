# Public publish privacy guard

This repository is intended to be public. Before pushing or publishing releases, check that no private runtime secrets are included.

Do not commit:

- `.env` files
- API keys, OAuth client secrets, webhook secrets, tokens, or passwords
- SSH keys, private certificates, `.pem`, `.key`, or credential files
- real customer data or billing data
- private VPS login credentials

Allowed public placeholders:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `BILLING_WEBHOOK_SECRET`
- `YOUR_DOMAIN`

Recommended pre-push checks:

```powershell
git ls-files | rg -i "(^|/)(\.env|.*\.key|.*\.pem|.*secret.*|credentials|config\.json|.*\.conf\.remote)$"
git log --all --diff-filter=A --name-only --pretty=format: | rg -i "(^|/)(\.env|.*\.key|.*\.pem|.*secret.*|credentials|config\.json|.*\.conf\.remote)$"
```

If either command finds a sensitive file, stop and remove it from history before publishing.
