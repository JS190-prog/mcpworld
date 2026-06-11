# MCP World

MCP World는 Blender, CAD, Photoshop, HWP, Office 같은 여러 로컬 MCP 서버를 한 창에서 켜고 끄는 Windows용 통합 컨트롤러입니다.

쉽게 말하면, ChatGPT가 내 PC의 여러 프로그램을 사용할 수 있도록 “서버 실행”과 “외부 연결 터널”을 한 번에 관리해 주는 실행 버튼 모음입니다.

예를 들어 이런 상황에서 사용합니다.

```text
ChatGPT에서 Blender MCP를 쓰고 싶다.
CAD MCP도 같이 켜고 싶다.
HWP나 Office MCP도 필요할 때만 켜고 싶다.
각 서버와 터널 상태를 한 화면에서 보고 싶다.
```

---

## 이런 사람에게 좋습니다

- 여러 MCP 서버를 매번 터미널에서 따로 실행하기 번거로운 사람
- ChatGPT 웹에서 로컬 Blender, CAD, Photoshop, HWP, Office를 연결해 쓰고 싶은 사람
- 서버가 켜졌는지, 터널이 연결됐는지 한눈에 확인하고 싶은 사람
- MCP 포트, 실행 경로, 공개 URL을 한 곳에서 관리하고 싶은 사람

---

## 처음 이해해야 할 핵심

ChatGPT 웹은 내 PC의 `127.0.0.1` 주소에 직접 접속할 수 없습니다. 그래서 MCP World는 다음 구조를 사용합니다.

```text
ChatGPT
  ↓ HTTPS 공개 URL
VPS nginx
  ↓ SSH 역터널
내 PC의 MCP 서버
  ↓
Blender / CAD / Photoshop / HWP / Office
```

MCP World 창에서 각 MCP의 상태등이 모두 초록색이면, ChatGPT에서 해당 도구를 사용할 준비가 된 것입니다.

각 행에는 보통 두 가지 상태가 있습니다.

- 서버: 내 PC에서 MCP 서버가 실행 중인지
- 터널: 외부 공개 URL이 내 PC 서버로 연결되는지

둘 다 초록색이어야 ChatGPT 웹에서 안정적으로 사용할 수 있습니다.

---

## 중요한 제한사항

이 프로그램은 Windows 11 환경을 기준으로 작성되었습니다. macOS나 Linux에서는 그대로 동작하지 않을 가능성이 큽니다.

이유는 다음과 같습니다.

- 한글, Office, Photoshop, CAD 제어가 Windows COM 자동화에 의존합니다.
- 설정 경로가 `C:/...` 형식의 Windows 경로를 기준으로 합니다.
- 실행 파일 경로가 `.venv\Scripts\python.exe` 같은 Windows 가상환경 구조를 사용합니다.

---

## 관리 대상 MCP 예시

| MCP | 하는 일 | 공개 URL 예시 |
|---|---|---|
| Blender | 3D 장면 생성, 오브젝트 배치, 렌더링 보조 | `https://YOUR_DOMAIN/bmcp/mcp` |
| CAD | AutoCAD/GstarCAD/ZWCAD 도면 제어 | `https://YOUR_DOMAIN/cmcp/mcp` |
| Photoshop | Photoshop 문서와 레이어 자동화 | `https://YOUR_DOMAIN/pmcp/mcp` |
| HWP | 한글 문서 생성, 표 작성, 저장 | `https://YOUR_DOMAIN/hmcp/mcp` |
| Office | Excel, PowerPoint 등 Office 자동화 | `https://YOUR_DOMAIN/omcp/mcp` |
| Local Code | 로컬 MCP 코드 읽기/패치/백업 | `https://YOUR_DOMAIN/lcmcp/mcp` |
| OpenCrab Ingest | 문서 폴더를 OpenCrab Pack ZIP으로 생성 | 환경 설정에 따름 |

실제 포트와 URL은 `config.json` 설정에 따라 달라질 수 있습니다.

---

## 파일 구성

| 파일/폴더 | 설명 |
|---|---|
| `mcpworld.pyw` | GUI 본체입니다. tkinter와 트레이 아이콘을 사용합니다. |
| `config.json` | MCP 목록, 포트, 경로, 실행 명령, 환경변수를 저장합니다. |
| `.venv\` | MCP World 실행용 Python 가상환경입니다. |
| `logs\` | 서버와 터널 로그가 저장됩니다. |

---

## 5분 시작 순서

### 1. MCP World 실행

바탕화면의 `MCP World` 바로가기를 더블클릭합니다.

또는 폴더에서 직접 실행합니다.

```powershell
cd C:\scratch\mcpworld
.\.venv\Scripts\pythonw.exe mcpworld.pyw
```

### 2. 필요한 프로그램을 미리 실행

사용하려는 MCP에 따라 대상 프로그램을 열어 둡니다.

- Blender MCP: Blender 실행
- CAD MCP: AutoCAD, GstarCAD 또는 ZWCAD 실행
- Photoshop MCP: Photoshop 실행
- HWP MCP: 한컴오피스 한글 실행
- Office MCP: Excel 또는 PowerPoint 실행

일부 MCP는 설정에 따라 자동 실행될 수 있지만, 처음 테스트할 때는 직접 실행해 두는 것이 문제 파악에 쉽습니다.

### 3. 전체 시작 또는 개별 시작

- 모든 MCP를 한 번에 켜려면 `▶ 전체 시작`
- 하나만 켜려면 해당 행의 시작 버튼

### 4. 상태등 확인

각 MCP 행에서 서버와 터널 상태가 모두 초록색인지 확인합니다.

### 5. ChatGPT 커넥터에 URL 등록

ChatGPT 개발자 모드 커넥터에 해당 공개 URL을 추가합니다. 인증 방식은 설정에 따라 다르지만, 현재 구성은 보통 “인증 없음” 방식입니다.

### 6. 사용 후 중지

작업이 끝나면 `■ 전체 중지`로 서버와 터널을 끕니다.

---

## 처음 해볼 만한 요청 예시

Blender가 초록색이면:

```text
Blender 연결 상태를 확인하고 현재 장면 정보를 알려줘.
```

CAD가 초록색이면:

```text
현재 CAD에서 열린 도면 정보를 확인해줘.
```

Photoshop이 초록색이면:

```text
Photoshop 연결 상태를 확인해줘.
```

HWP가 초록색이면:

```text
한글 새 문서를 만들고 제목을 넣어줘.
```

OpenCrab Ingest가 초록색이면:

```text
OpenCrab Ingest MCP 상태를 확인해줘.
```

---

## GUI에서 자주 쓰는 기능

| 기능 | 설명 |
|---|---|
| `▶ 전체 시작` | 등록된 MCP 서버와 터널을 한 번에 시작합니다. |
| `■ 전체 중지` | 실행 중인 서버와 터널을 중지합니다. |
| 개별 시작/중지 | 특정 MCP만 켜거나 끕니다. |
| 상태등 | 서버와 터널 연결 상태를 색상으로 보여줍니다. |
| `📋 URL` | ChatGPT 커넥터에 넣을 공개 URL을 복사합니다. |
| `⚙ 설정` | 포트, 경로, 실행 명령, 환경변수를 편집합니다. |
| 로그 확인 | 서버 또는 터널 오류를 확인할 때 사용합니다. |

---

## 새 MCP를 추가하는 기본 흐름

새 도구를 ChatGPT에서 쓰려면 보통 3단계가 필요합니다.

1. MCP World의 `config.json`에 로컬 서버 정보를 등록합니다.
2. VPS nginx에 공개 경로를 추가합니다.
3. ChatGPT 커넥터에 공개 URL을 등록합니다.

`config.json` 예시는 다음과 같습니다.

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

각 값의 의미는 다음과 같습니다.

| 필드 | 의미 |
|---|---|
| `id` | MCP 고유 이름입니다. 로그 파일명에도 사용됩니다. |
| `name` | GUI에 보이는 이름입니다. |
| `local_port` | 내 PC에서 서버가 사용하는 포트입니다. |
| `vps_port` | VPS에서 역터널로 받는 포트입니다. |
| `path` | 공개 URL 경로입니다. 예: `/amcp/` → `/amcp/mcp` |
| `cwd` | 서버 실행 폴더입니다. |
| `server` | 서버 실행 명령입니다. |
| `env` | 서버에 전달할 환경변수입니다. |

stdio 방식 MCP는 `mcp-proxy`로 감싸 HTTP 방식으로 노출해야 할 수 있습니다. CAD, HWP, Office 같은 MCP가 이 방식일 수 있습니다.

---

## VPS nginx에 새 경로를 추가하는 예시

VPS에 접속합니다.

```bash
ssh root@YOUR_VPS_IP
```

nginx 설정 파일을 엽니다.

```bash
nano /etc/nginx/sites-available/automaton-dashboard-http.conf
```

아래 블록을 추가합니다. `/amcp/`와 `8016`은 실제 값으로 바꿉니다.

```nginx
location ^~ /amcp/ {
    rewrite ^/amcp/(.*)$ /$1 break;
    proxy_pass http://127.0.0.1:8016;
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
```

적용 전 반드시 문법 검사를 합니다.

```bash
nginx -t && systemctl reload nginx
```

문법 오류가 있으면 reload하지 마세요. 기존 연결까지 영향을 줄 수 있습니다.

---

## CAD 파일 업로드 관련 주의사항

ChatGPT 웹에 업로드한 파일의 `/mnt/data/...` 경로는 OpenAI 샌드박스 내부 경로입니다. 내 Windows PC의 CAD MCP 서버는 이 경로를 직접 읽을 수 없습니다.

따라서 CAD 작업은 다음 방식이 안전합니다.

- 사용자가 원본 도면을 CAD에서 직접 열어 둡니다.
- MCP는 현재 열린 도면을 기준으로 정보를 확인하거나 수정합니다.
- 수정본은 새 이름으로 저장합니다.
- 업로드 파일을 직접 열어야 한다면 실제 파일 bytes를 전달하는 별도 bridge가 필요합니다.

파일명만 보고 다운로드 폴더나 임시 폴더에서 자동 검색하는 방식은 오래된 캐시 파일을 잘못 열 수 있으므로 피해야 합니다.

---

## 보안 주의사항

현재 구성은 공개 URL을 통해 로컬 MCP를 사용할 수 있게 만드는 구조입니다. 따라서 다음 원칙을 지키는 것이 좋습니다.

- 필요할 때만 서버와 터널을 켭니다.
- 작업이 끝나면 `전체 중지`를 누릅니다.
- 공개 URL과 API Key를 GitHub README나 공개 문서에 그대로 올리지 않습니다.
- 중요한 문서는 복사본으로 작업합니다.
- 도구가 실제 파일을 수정하는 경우 결과를 직접 확인합니다.

---

## 잘 안 될 때 확인할 것

- MCP World가 실행 중인지 확인합니다.
- 해당 MCP의 서버 상태등이 초록색인지 확인합니다.
- 터널 상태등도 초록색인지 확인합니다.
- 대상 프로그램이 실행되어 있는지 확인합니다.
- `config.json`의 경로와 포트가 실제 환경과 맞는지 확인합니다.
- 포트가 다른 프로그램과 충돌하지 않는지 확인합니다.
- `logs` 폴더에서 서버 로그와 터널 로그를 확인합니다.
- 설정을 바꿨다면 MCP World 또는 해당 MCP를 다시 시작합니다.

---

## 초보자를 위한 사용 팁

- 처음에는 MCP 하나만 켜서 테스트하세요.
- 연결 상태 확인 요청부터 시작하세요.
- 실제 파일 수정 전에는 테스트 파일이나 복사본을 사용하세요.
- URL을 등록한 뒤 도구 목록이 안 보이면 커넥터를 삭제하고 다시 추가해 보세요.
- 서버는 켜졌는데 ChatGPT에서 안 되면 터널 또는 nginx 설정을 먼저 의심하세요.

---

## 면책 조항

MCP World는 여러 로컬 MCP 서버와 외부 연결 터널을 쉽게 관리하기 위한 도구입니다. 연결된 MCP는 Blender, CAD, Photoshop, HWP, Office 등 실제 프로그램과 파일을 수정할 수 있습니다. AI 명령은 예상과 다르게 동작할 수 있으므로 중요한 파일은 반드시 백업한 뒤 사용하세요.

공개 URL, VPS 설정, API Key, 로컬 파일 권한 관리는 사용자 책임입니다. 외부에 공유되는 문서에는 민감한 주소나 키가 포함되지 않도록 주의하세요.

### 보안 경고

VPS 역터널로 공개된 MCP URL은 기본 무인증입니다. URL을 아는 누구나 로컬 프로그램을 제어할 수 있으므로 URL을 외부에 공유하지 말고, 사용하지 않을 때는 터널을 꺼두세요. 무인증 공개 운영으로 발생하는 보안 사고에 대해 개발자는 책임을 지지 않습니다.

### 상표 고지

Blender, AutoCAD, ZWCAD, Photoshop, 한컴오피스 한글, Microsoft Office, ChatGPT 등은 각 소유자의 상표입니다. 이 프로젝트는 Blender Foundation, Autodesk, ZWSOFT, Adobe, 한글과컴퓨터, Microsoft, OpenAI와 무관한 독립 프로젝트입니다.
