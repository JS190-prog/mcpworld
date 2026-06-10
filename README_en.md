# MCP World — Unified Controller for Blender / CAD / Photoshop / HWP / Office

[한국어](README.md) | **English**

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![MCP](https://img.shields.io/badge/MCP-Model_Context_Protocol-orange)

> ### 🌐 Use local MCP servers from **ChatGPT (web browser)** — not just Claude
> MCP is commonly thought to connect only with desktop clients like Claude Desktop.
> **MCP World** exposes your local MCP servers via **SSH reverse tunnel → public URL**
> and connects them directly to the **ChatGPT Developer-mode connector**. So you can
> control Blender, CAD, Photoshop, Hangul (HWP), and Office in natural language
> straight from **ChatGPT on the web** — no separate desktop app required.

![MCP World GUI](docs/screenshot.png)

A GUI to start/stop local MCPs (servers + VPS reverse tunnels) that connect to ChatGPT web, all from one window.

> ⚠️ **Windows 11 only.** It does not run on macOS or Linux.
> The controlled apps (Hangul/HWP, MS Office, Photoshop, CAD) all rely on **Windows COM automation**, and the launch paths in `config.json` are hardcoded as `C:/...\Scripts\*.exe`.

## Setup (first time)

1. Copy `config.example.json` to `config.json`.
2. Fill in your own environment:
   - `vps_ssh` — VPS SSH target (e.g. `root@YOUR_VPS_IP`)
   - `public_base` — public domain (e.g. `https://YOUR_DOMAIN`)
   - each MCP's `cwd` / `server` / `install` paths & repo URLs
3. `config.json` is in `.gitignore` and never committed (keeps your settings private).

> For VPS nginx routing, see **"Add a new MCP on the VPS"** below.

> ℹ️ All five MCPs install automatically from **public repos (github.com/JS190-prog/*)**
> or PyPI (`uvx`). `config.example.json` already points to the real repos — just fill in
> your **VPS/domain** and they clone & install on start. To customize, fork each repo
> and change its `install` URL.

## Layout
- `mcpworld.pyw` — the GUI (tkinter + pystray tray)
- `config.json` — MCP definitions (ports, paths, launch commands, env)
- `.venv\` — dedicated virtualenv (pystray, pillow)
- `logs\` — per-MCP server/tunnel logs (`<id>-server.log`, `<id>-tunnel.log`)

## Managed MCPs
| MCP | Local port | VPS port | Public URL |
|---|---|---|---|
| Blender | 18000 | 8010 | https://YOUR_DOMAIN/bmcp/mcp |
| CAD | 18001 | 8011 | https://YOUR_DOMAIN/cmcp/mcp |
| Photoshop | 8002 | 8012 | https://YOUR_DOMAIN/pmcp/mcp |
| HWP 2024 | 18004 | 8014 | https://YOUR_DOMAIN/hmcp/mcp |
| Office | 18005 | 8015 | https://YOUR_DOMAIN/omcp/mcp |
| Local Code | 18006 | 8017 | https://YOUR_DOMAIN/lcmcp/mcp |

Each row: **Server** (local port) + **Tunnel** (SSH reverse tunnel) status lights → both green means it's usable from ChatGPT.

## Run
- Double-click the desktop **`MCP World`** shortcut, or
- `\.venv\Scripts\pythonw.exe mcpworld.pyw`

## Usage
1. **▶ Start All** — launch all servers → wait for ports → connect reverse tunnels
2. When each MCP's status lights (server & tunnel) turn green, it's ready
3. Launch each target app (Blender / ZWCAD / Photoshop / Hangul / Office) and open your document
   - HWP & Office can auto-launch via the `env` setting in `config.json`
4. Add the URLs above to ChatGPT's Developer-mode connector (auth = none)
5. When done, **■ Stop All**

> The **⚙ Settings** button lets you edit every MCP's ports / paths / env / launch command in the GUI (applied after restart).

---

## CAD file upload note

A file uploaded to ChatGPT web lives under OpenAI's sandbox path `/mnt/data/...`. The CAD MCP server, running on your local Windows PC, cannot read that path directly.

So this is **not** treated as something it can open automatically:

```json
{ "file_path": "/mnt/data/plan.dwg" }
```

Previously it would take just the basename of `/mnt/data/plan.dwg` and search `C:\cad-mcp\workspace`, `C:\cad-mcp\inbox`, and `Downloads` for a same-named file — but that can wrongly open an old cached drawing, so it was removed.

Safe paths the CAD MCP accepts:

- Open the original drawing in CAD yourself, then use active-document tools such as `get_active_document_info`, `list_text_entities`, `update_entity`, `save_as_generated`.
- A file is treated as an upload only when its actual bytes arrive via `upload_and_open_drawing(file_base64=...)` or `upload_drawing_chunk`.
- Only an explicit local Windows path, or a file you placed directly in `C:\cad-mcp\inbox`, is opened.

`file_id` alone is rejected too: the local server cannot fetch the bytes by itself unless a separate bridge sends them.

---

## Add a new MCP on the VPS (How-To)

To use a new tool (MCP) from ChatGPT, just do **① local registration → ② VPS exposure (nginx) → ③ ChatGPT connection**.

**Connection flow**
```
ChatGPT  ──HTTPS──▶  https://YOUR_DOMAIN/<path>/mcp
                          │  (VPS nginx reverse proxy)
                          ▼
                     VPS 127.0.0.1:<vps_port>
                          │  (SSH reverse tunnel — auto-created by the GUI)
                          ▼
                     Your PC 127.0.0.1:<local_port>
                          │  (local MCP server)
                          ▼
                     Target app (Blender / Hangul / Office ...)
```

### Step 1 — Local registration (`config.json`)

Add it via the **⚙ Settings** button, or append an entry to the `mcps` array in `config.json`:

```json
{
  "id": "myapp",
  "name": "My App",
  "local_port": 18006,
  "vps_port": 8016,
  "path": "/amcp/",
  "cwd": "C:/path/to/server",
  "server": ["C:/path/to/python.exe", "server.py", "--port", "18006"],
  "env": { "MY_FLAG": "1" }
}
```

| Field | Meaning |
|---|---|
| `id` | unique id (also used for log filenames) |
| `local_port` | a free local port |
| `vps_port` | a free VPS port (avoid overlaps in the 8010+ range) |
| `path` | public path (e.g. `/amcp/`) → URL becomes `.../amcp/mcp` |
| `cwd` / `server` | server working dir / launch command (array) |
| `env` | (optional) env vars for the server (e.g. HWP auto-launch `HWP_MCP_ALLOW_LAUNCH=1`) |

> **stdio-based MCPs** are wrapped with `mcp-proxy` to expose them over HTTP (CAD / HWP / Office use this). Example:
> ```
> "server": ["C:/cad-mcp/.proxy-venv/Scripts/mcp-proxy.exe",
>            "--host", "127.0.0.1", "--port", "18006",
>            "--transport", "streamablehttp", "--pass-environment", "--",
>            "C:/path/python.exe", "server.py"]
> ```

Restart the GUI → click **Start** on the new row → when the server light is green, local registration is complete.

### Step 2 — VPS exposure (nginx routing)

SSH into the VPS and add a `location` block to the nginx config:

```bash
ssh root@YOUR_VPS_IP
nano /etc/nginx/sites-available/automaton-dashboard-http.conf
```

Add the block below — change only **`/amcp/` (path) and `8016` (vps_port)**:

```nginx
# === amcp (ChatGPT connector) BEGIN ===
location ^~ /amcp/ {
    rewrite ^/amcp/(.*)$ /$1 break;
    proxy_pass http://127.0.0.1:8016;   # ← vps_port
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 24h;
    proxy_send_timeout 24h;
    client_max_body_size 150M;
}
# === amcp END ===
```

Then **always validate and apply** (never reload on a syntax error — it would take down other services too):

```bash
nginx -t && systemctl reload nginx
```

> **Revert:** delete the whole `# === amcp BEGIN/END ===` block and run `nginx -t && systemctl reload nginx` again. Existing blocks are marked with the same `# === <name> BEGIN/END ===` comments, so they're easy to find.

### Step 3 — Connect ChatGPT

Add the public URL to ChatGPT's Developer-mode connector (auth = none):

```
https://YOUR_DOMAIN/amcp/mcp
```

- Use the row's **📋 URL** button in the GUI to copy the address.
- **If you change tools**, remove and re-add the connector to refresh the tool list.

---

## Notes
- ChatGPT only works while **your PC is on** and the server + tunnel are alive.
- The window's X button minimizes to the tray (keeps running). The tray icon quits.
- "Quit (keep servers)" closes only the GUI; servers/tunnels keep running in the background → to fully stop, use **Stop All** first.
- It is an unauthenticated public endpoint, so only turn it on while in use.

## ⚠️ Disclaimer

The MCPs connected through mcpworld let AI models directly control local applications (Blender, CAD, Photoshop, HWP, Office, local code) and execute AI-generated commands/code. AI behavior may differ from expectations and can damage documents, files, or data. The authors take no responsibility for any damage caused by using this software. Always back up important data, and keep the public tunnel on only while in use. (See the no-warranty clause in the LICENSE.)
