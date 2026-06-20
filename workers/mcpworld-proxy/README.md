# MCPWorld Cloudflare Worker proxy

This Worker hides the direct VPS MCPWorld endpoint behind a public Worker URL.

Recommended public URL shape:

```text
https://mcpworld.tornado616.cloud/mcpworld/{issued-key}/mcp
```

The Worker forwards that request to:

```text
https://www.tornado616.cloud/mcpworld/mcp?key={issued-key}
```

Set `MCPWORLD_PROXY_PUBLIC_BASE` on the VPS API service to the public Worker prefix without the issued key:

```text
MCPWORLD_PROXY_PUBLIC_BASE=https://mcpworld.tornado616.cloud/mcpworld
```

Then new dashboard connector sessions will return Worker proxy links instead of direct VPS links.

Optional single private connector mode:

```bash
wrangler secret put MCPWORLD_CONNECTOR_KEY
```

With that secret, `/mcpworld/mcp` forwards using the secret key. For per-user SaaS sessions, prefer `/mcpworld/{issued-key}/mcp`.


## Custom domain setup

Use `mcpworld.tornado616.cloud` as the production proxy host.

Cloudflare Worker Custom Domains require `tornado616.cloud` to be an active Cloudflare zone. If the domain still uses an external DNS provider, first move the zone to Cloudflare or add the custom domain in the Cloudflare dashboard after the zone is active.

Dashboard path:

```text
Workers & Pages -> mcpworld-proxy -> Settings -> Domains & Routes -> Add -> Custom Domain -> mcpworld.tornado616.cloud
```

After the domain is active, set the VPS API environment variable:

```text
MCPWORLD_PROXY_PUBLIC_BASE=https://mcpworld.tornado616.cloud/mcpworld
```
