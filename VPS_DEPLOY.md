# MCP World VPS Deploy Guide

This folder is a static SaaS prototype. It can be hosted under:

```text
https://www.tornado616.cloud/mcpworld/
```

## Upload To Subfolder

```bash
sudo mkdir -p /var/www/mcpworld
sudo rsync -av ./ /var/www/mcpworld/
sudo chown -R www-data:www-data /var/www/mcpworld
```

## Nginx Subpath Example

Use this when the same domain already serves another site at `/`.

```nginx
server {
  listen 80;
  server_name www.tornado616.cloud tornado616.cloud;

  location /mcpworld/ {
    alias /var/www/mcpworld/;
    index index.html;
    try_files $uri $uri/ /mcpworld/index.html;
  }

  location = /mcpworld/mcp {
    proxy_pass http://127.0.0.1:33210/mcp;
    proxy_http_version 1.1;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  location ^~ /mcpworld/api/ {
    proxy_pass http://127.0.0.1:33210/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  location ^~ /mcpworld/relay/ {
    proxy_pass http://127.0.0.1:33210/relay/;
    proxy_http_version 1.1;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

Then reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## API Service

```bash
sudo mkdir -p /var/lib/mcpworld
sudo chown -R www-data:www-data /var/lib/mcpworld
sudo cp deploy/mcpworld-api.service /etc/systemd/system/mcpworld-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now mcpworld-api
```

Optional production environment variables:

```text
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI
BILLING_PROVIDER
BILLING_CHECKOUT_URL
BILLING_WEBHOOK_SECRET
MCPWORLD_PROXY_PUBLIC_BASE=https://mcpworld.tornado616.cloud/mcpworld
```

## Demo Credentials

- User login: `demo` / `demo1234`
- Admin console: `/mcpworld/admin/`
- Admin token: `mcpworld-admin-2026`

## Production TODO

- Replace demo login with real OAuth/email authentication.
- Add billing provider hosted checkout and subscription webhooks.
- Deploy the Cloudflare Worker proxy in `workers/mcpworld-proxy/` if public MCP links should hide the direct VPS route.
- Build and sign the Windows local agent installer.
- Store audit logs for admin actions and connector issuance.
