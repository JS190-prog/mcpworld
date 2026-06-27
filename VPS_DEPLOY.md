# MCP World VPS Deploy Guide

This folder contains the MCP World landing page, dashboard, API service, and local-agent release files. It can be hosted under:

```text
https://www.tornado616.cloud/mcpworld/
```

## 검증형 배포 스크립트 (권장)

코드 수정 후 VPS로 바로 안전하게 업데이트하려면 `deploy/deploy.sh`를 쓰세요. rsync 불필요(tar+ssh).

```bash
# 배포될 파일만 미리보기 (원격 미접촉)
DRY_RUN=1 bash deploy/deploy.sh

# 실제 배포: 로컬 테스트 -> 업로드(.new) -> 원자적 스왑(.old=롤백) -> 재시작 -> 헬스체크
bash deploy/deploy.sh
```

동작:
1. **로컬 테스트** 통과해야 진행(실패면 VPS를 건드리지 않고 중단).
2. tar로 `/var/www/mcpworld.new`에 업로드 후 **원자적 스왑**(현재 버전은 `.old`로 보존).
3. `nginx -t` → `systemctl restart mcpworld-api` → `nginx reload`.
4. **헬스체크**(`systemctl is-active` + 포트 응답). 실패 시 **`.old`로 자동 롤백**.

즉 깨진 코드가 라이브로 남지 않습니다. `DB(/var/lib/mcpworld)`·시크릿(`/etc/mcpworld/session.env`)은 동기화 대상이 아니라 보존됩니다.

환경변수로 조정: `MCPWORLD_SSH`(기본 `myserver-root`), `MCPWORLD_REMOTE_DIR`, `MCPWORLD_SERVICE`, `PYTHON_BIN`.

> 선택: local-code-mcp의 `allowed_command_specs`에 이 스크립트를 등록하면, 운영자(admin)가 ChatGPT를 통해 `mcp_run_known_command`(confirm=true)로 배포를 트리거할 수 있습니다. 단 라이브 배포라 신중히.

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

  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-Frame-Options "SAMEORIGIN" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;
  add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
  add_header Content-Security-Policy "default-src 'self'; base-uri 'self'; frame-ancestors 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' https://mcpworld.tornado616.cloud" always;

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
MCPWORLD_SESSION_SECRET
MCPWORLD_ADMIN_EMAILS=admin@example.com
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI
BILLING_PROVIDER
BILLING_CHECKOUT_URL
BILLING_WEBHOOK_SECRET
MCPWORLD_PROXY_PUBLIC_BASE=https://mcpworld.tornado616.cloud/mcpworld
```

`MCPWORLD_SESSION_SECRET` should be a long random value and should be stored outside the repository, for example in `/etc/mcpworld/session.env`.

Demo seed users are disabled by default. For an isolated staging environment only, set both `MCPWORLD_ENABLE_DEMO_DATA=1` and `MCPWORLD_DEMO_PASSWORD=<temporary-password>` before first database initialization.

## Admin Access

- Admin console: `/mcpworld/admin/`
- Admin users are controlled by `MCPWORLD_ADMIN_EMAILS`.
- The admin console requires a logged-in session for one of those emails.

## Production TODO

- Add billing provider hosted checkout and subscription webhooks.
- Deploy the Cloudflare Worker proxy in `workers/mcpworld-proxy/` if public MCP links should hide the direct VPS route.
- Build and sign the Windows local agent installer.
- Store audit logs for admin actions and connector issuance.
