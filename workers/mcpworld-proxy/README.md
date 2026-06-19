# MCPWorld Cloudflare Worker proxy

This Worker hides the direct VPS MCPWorld endpoint behind a public Worker URL.

Recommended public URL shape:

```text
https://mcpworld-proxy.YOUR_SUBDOMAIN.workers.dev/mcpworld/{issued-key}/mcp
```

The Worker forwards that request to:

```text
https://www.tornado616.cloud/mcpworld/mcp?key={issued-key}
```

Set `MCPWORLD_PROXY_PUBLIC_BASE` on the VPS API service to the public Worker prefix without the issued key:

```text
MCPWORLD_PROXY_PUBLIC_BASE=https://mcpworld-proxy.YOUR_SUBDOMAIN.workers.dev/mcpworld
```

Then new dashboard connector sessions will return Worker proxy links instead of direct VPS links.

Optional single private connector mode:

```bash
wrangler secret put MCPWORLD_CONNECTOR_KEY
```

With that secret, `/mcpworld/mcp` forwards using the secret key. For per-user SaaS sessions, prefer `/mcpworld/{issued-key}/mcp`.
