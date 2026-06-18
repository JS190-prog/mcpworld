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
}
```

Then reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Demo Credentials

- User login: `demo` / `demo1234`
- Admin token: `mcpworld-admin-2026`

## Production TODO

- Replace demo login with real OAuth/email authentication.
- Add billing provider hosted checkout and subscription webhooks.
- Implement the real `/mcpworld/relay/...` MCP session router on the VPS.
- Build and sign the Windows local agent installer.
- Store audit logs for admin actions and connector issuance.
