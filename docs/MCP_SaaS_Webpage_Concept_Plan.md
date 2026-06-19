# MCP World SaaS 샘플 웹페이지 제작 계획

작성일: 2026-06-18 KST
대상 폴더: `C:/Users/USER/Desktop/MCP 폴더/main`
참고 로컬 소스: `C:/scratch/mcpworld`
현재 작업 상태: `planning_required`

> 이 문서는 실제 웹페이지 제작 전에 사용할 기획서입니다. 아직 결제 연동, 개인정보 처리방침 확정, 서버 배포는 수행하지 않았습니다.

---

## 1. 프로젝트 컨셉

### 1.1 서비스 한 줄 정의

ChatGPT 웹브라우저에서 사용자의 로컬 PC에 있는 CAD, PowerPoint, Excel, HWP, Photoshop, Blender 같은 MCP 도구를 안전하게 연결해 주는 로컬 MCP 게이트웨이 SaaS.

### 1.2 사용자 문제

기존 사용자는 다음 문제를 겪는다.

1. CAD, PPT, Excel, HWP, Photoshop 같은 로컬 프로그램을 AI와 연결하려면 MCP 서버, 포트, 터널, 커넥터 설정을 직접 관리해야 한다.
2. ChatGPT 웹은 사용자의 `127.0.0.1` 로컬 주소에 직접 접근할 수 없다.
3. 로컬 파일이나 도면을 매번 업로드하고 긴 문맥으로 설명하면 토큰 부담이 커지고, 요금제 변경 압박이 생긴다.
4. 프로그램별 MCP 서버를 각각 켜고 끄는 과정이 초보자에게 어렵다.
5. 공개 URL을 잘못 열면 로컬 프로그램과 파일이 외부에 노출될 수 있다.

### 1.3 제안 가치

이 서비스는 사용자가 복잡한 터미널 명령을 몰라도 다음 흐름으로 로컬 MCP를 사용할 수 있게 만든다.

```text
사용자 회원가입
  -> Windows 로컬 에이전트 설치
  -> 로컬 프로그램 실행
  -> MCP World 또는 경량 Agent가 MCP 서버 실행
  -> 사용자별 보안 터널 생성
  -> ChatGPT 커넥터 URL 발급
  -> ChatGPT 웹에서 CAD/PPT/Excel/HWP/Photoshop 작업
```

### 1.4 중요한 표현 주의

마케팅 문구에서 “토큰이 안 든다”라고 단정하면 안 된다. ChatGPT 사용량과 토큰 정책은 OpenAI/ChatGPT 요금제에 의해 결정된다. 안전한 표현은 다음과 같다.

```text
긴 파일 설명과 반복 업로드를 줄이고, 로컬 프로그램 상태를 직접 MCP로 확인해 작업 흐름을 단축합니다.
```

또는

```text
브라우저에서 로컬 MCP를 쉽게 연결해 CAD·PPT 작업을 더 적은 반복 설명으로 진행할 수 있게 돕습니다.
```

---

## 2. OpenCrab 사이트에서 참고할 구조

OpenCrab 사이트는 다음 구조를 참고 대상으로 삼는다.

1. Hero 섹션: 서비스 정체성, 핵심 키워드, CTA
2. Architecture 섹션: 제품 흐름을 한눈에 보여주는 구조도
3. Workflow 섹션: 사용자가 따라갈 단계별 흐름
4. Target 섹션: 주요 사용자군 구분
5. Use cases 섹션: 실제 사용 사례 나열
6. Pricing 섹션: Free / Pro / Expert 식의 단순 요금제
7. Policy 섹션: 약관, 개인정보 처리방침, 환불 정책

이 사이트와 비슷한 정보 구조를 사용하되, 본 서비스는 OpenCrab의 지식팩/Graph RAG 방향이 아니라 “로컬 MCP 연결과 프로그램 제어”를 중심에 둔다.

---

## 3. 차별화 포지션

### 3.1 OpenCrab과의 차이

| 구분 | OpenCrab 참고 구조 | MCP World SaaS 방향 |
|---|---|---|
| 핵심 가치 | 문서 지식화, 팩, 검색·질의 | 로컬 프로그램 -> MCP -> ChatGPT 웹 연결 |
| 주요 사용자 | 연구자, 도메인 전문가, AI 빌더 | CAD/PPT/Excel/HWP/Photoshop 실무자 |
| 주요 산출물 | 지식팩, 그래프, 근거 기반 답변 | 로컬 도구 연결 세션, 작업 결과 파일 |
| 핵심 기술 | 문서 구조화, 팩, 질의 | local agent, reverse tunnel, connector, permission gate |
| 보안 초점 | 업로드 문서와 지식 데이터 격리 | 사용자의 로컬 앱·파일 접근 제한과 터널 보안 |

### 3.2 웹페이지 대표 문구

```text
ChatGPT 웹에서 로컬 CAD와 PowerPoint를 바로 연결하세요.
```

```text
복잡한 터널, 포트, MCP 서버 실행을 한 번의 대시보드로 관리합니다.
```

```text
파일을 계속 업로드하지 않고, 열려 있는 로컬 프로그램을 MCP로 안전하게 제어합니다.
```

```text
CAD·PPT 실무자를 위한 브라우저 기반 로컬 MCP 게이트웨이.
```

---

## 4. 대상 MCP 프로그램 분류

`C:/scratch/mcpworld` README와 문서 기준으로 샘플 사이트에 노출할 MCP 카테고리는 다음과 같다.

### 4.1 1차 공개 대상

1. Office MCP
   - PowerPoint 슬라이드 제작·수정
   - Excel 워크북 수정·서식 유지
   - 발표자료 노트, 애니메이션, 번역 보조

2. CAD MCP
   - AutoCAD, GstarCAD, ZWCAD 계열 도면 제어
   - 현재 열린 도면 확인
   - 레벨값, 치수, 텍스트, 레이어 기반 작업

3. HWP MCP
   - 한글 문서 생성·수정
   - 표, 문단, 양식 문서 자동화

4. Photoshop MCP
   - 레이어, 문서, 이미지 편집 보조
   - 배경, 선택 영역, 간단 합성 작업

5. Blender MCP
   - 3D 장면 생성·수정·렌더 보조
   - 모델 배치와 시각화

### 4.2 2차 확장 대상

1. Local Code MCP
   - 프로젝트 폴더 읽기·수정·패치 검증
   - 개발자용 요금제 또는 운영자 도구로 분리 권장

2. CLIP/sidecar 계열
   - 이미지·도면·문서 시각 검색 보조

3. Flow API, 법령, 통계, 건축 데이터 MCP
   - 도메인별 부가 기능으로 별도 확장 기능 영역에서 노출 가능

---

## 5. 샘플 웹페이지 정보구조

대상 폴더 `main`에는 아래 구조로 샘플 웹페이지를 만들면 좋다.

```text
main/
  index.html
  styles.css
  app.js
  assets/
    logo.svg
    hero-architecture.svg
  docs/
    service-plan.md
    privacy-checklist.md
    payment-checklist.md
    mcp-tool-map.md
```

정적 HTML 샘플을 먼저 만들고, 이후 Next.js 또는 SvelteKit으로 옮긴다.

### 5.1 index.html 섹션 구성

1. Navigation
   - 로고
   - Features
   - Workflow
   - MCP Tools
   - Pricing
   - Security
   - Guide
   - Sign in / Start

2. Hero
   - 메인 카피
   - 서브 카피
   - CTA 버튼: “Start local MCP”, “View guide”
   - 오른쪽: MCP 연결 흐름 다이어그램

3. Problem
   - ChatGPT 웹은 로컬 주소에 직접 접근할 수 없음
   - 프로그램별 MCP 서버 실행이 어려움
   - 파일 반복 업로드와 긴 설명이 번거로움

4. Architecture
   - Browser
   - SaaS Control Plane
   - Per-user Secure Tunnel
   - Local MCP Agent
   - Local Apps

5. Tool Cards
   - PowerPoint
   - Excel
   - CAD
   - HWP
   - Photoshop
   - Blender

6. Workflow
   - Install
   - Connect
   - Authorize
   - Work in ChatGPT
   - Stop tunnel

7. Security
   - 사용자별 터널
   - 세션 만료
   - 명령 권한 제한
   - 로컬 파일 직접 업로드 최소화
   - 로그 마스킹
   - 결제정보 직접 저장 금지

8. Pricing
   - Free
   - Pro
   - Studio
   - Team 또는 Expert

9. Policies
   - Terms
   - Privacy
   - Refunds
   - Security

10. Footer
   - Contact
   - 사업자 정보
   - 정책 링크

---

## 6. 권장 서비스 아키텍처

### 6.1 최소 MVP 구조

```text
ChatGPT Web Connector
  -> https://your-domain.com/u/{user}/mcp/{tool}
  -> SaaS Auth Gateway
  -> User Session Router
  -> VPS Reverse Tunnel Endpoint
  -> User Local Agent
  -> Local MCP Server
  -> Local Application
```

### 6.2 구성 요소

1. Web Frontend
   - landing page
   - dashboard
   - login/signup
   - billing portal
   - connector URL 발급 화면

2. Control Plane API
   - 사용자 인증
   - 구독 권한 확인
   - 세션 발급
   - 터널 상태 확인
   - MCP별 권한 정책 제공

3. Local Agent
   - Windows 전용 1차 버전
   - MCP World와 통합 또는 MCP World 경량화 버전
   - 사용자의 로컬 MCP 서버 시작·중지
   - 사용자별 세션 토큰으로 VPS에 outbound 연결
   - 서버와 터널 상태 표시

4. VPS Relay
   - nginx 또는 Caddy reverse proxy
   - per-user route
   - auth middleware
   - rate limit
   - request log redaction
   - tunnel timeout

5. Billing System
   - Paddle, Toss Payments, Stripe 중 선택
   - hosted checkout 사용
   - 카드번호 직접 저장 금지
   - 웹훅으로 구독 상태만 저장

6. Admin Console
   - 사용자 상태
   - 결제 상태
   - 터널 상태
   - abuse 탐지
   - 계정 정지
   - 환불 처리 링크

---

## 7. 개인정보 보호 설계

### 7.1 기본 원칙

1. 카드번호, CVC, 전체 결제 민감정보를 직접 저장하지 않는다.
2. 사용자의 로컬 파일 내용은 기본적으로 서버에 저장하지 않는다.
3. 로그에는 파일 내용, 전체 경로, 원문 문서 내용, 공개 URL 토큰을 남기지 않는다.
4. 사용자가 명시적으로 요청한 경우에만 파일 업로드 또는 원격 처리를 허용한다.
5. 사용자별 터널과 MCP 접근 권한을 분리한다.
6. 모든 세션은 만료 시간을 둔다.
7. 연결 종료 버튼을 웹과 로컬 에이전트 양쪽에 둔다.
8. 약관, 개인정보 처리방침, 환불 정책을 결제 전에 노출한다.

### 7.2 수집 정보 최소화

| 구분 | 수집 가능 | 저장 여부 | 비고 |
|---|---|---|---|
| 계정 이메일 | 가능 | 저장 | 로그인·결제 식별 |
| 결제 customer id | 가능 | 저장 | PG 식별자만 저장 |
| 구독 상태 | 가능 | 저장 | active, canceled 등 |
| 로컬 MCP 상태 | 가능 | 짧게 저장 | online/offline 정도 |
| 로컬 파일 경로 | 원칙적 비저장 | 가능하면 마스킹 | 전체 경로 노출 금지 |
| 문서 내용 | 기본 비저장 | 사용자가 업로드할 때만 | 별도 동의 필요 |
| 요청 로그 | 제한 저장 | 마스킹 필수 | 토큰, 키, 경로 제거 |

### 7.3 사용자 권리 처리

대시보드에 다음 기능을 둔다.

1. 계정 삭제 요청
2. 결제 포털 이동
3. 연결된 로컬 에이전트 해제
4. 세션 전체 만료
5. 로그 삭제 요청 또는 보관기간 안내
6. 개인정보 열람·정정·삭제·처리정지 요청 이메일

### 7.4 개인정보 처리방침에 들어갈 항목

1. 개인정보처리자 정보
2. 수집 항목
3. 처리 목적
4. 보유·이용 기간
5. 제3자 제공 여부
6. 처리 위탁 업체
7. 국외 이전 여부
8. 파기 절차
9. 정보주체 권리
10. 쿠키·로그 수집
11. 안전성 확보 조치
12. 문의처
13. 변경 고지 방식

---

## 8. 결제 시스템 계획

### 8.1 결제 방식

초기에는 직접 카드정보를 다루지 않는 hosted checkout 방식이 가장 안전하다.

권장 선택지:

1. Paddle
   - Merchant of Record 구조가 장점
   - 글로벌 SaaS 구독에 적합
   - 해외 SaaS형 요금제 운영 참고에 적합

2. Toss Payments
   - 국내 사용자 대상 결제 UX에 유리
   - 카드, 계좌, 간편결제 대응
   - 한국 사업자·정산·세금계산서 흐름 검토 필요

3. Stripe
   - 글로벌 SaaS에 적합
   - 한국 사업자 지원 범위와 정산 구조는 최신 확인 필요

### 8.2 저장할 결제 데이터

서버 DB에는 아래만 저장한다.

```text
user_id
plan_id
billing_provider
provider_customer_id
provider_subscription_id
subscription_status
current_period_start
current_period_end
cancel_at_period_end
last_webhook_event_id
```

저장하지 말아야 할 것:

```text
card_number
cvc
full billing address unless required
raw payment credential
checkout session secret
```

### 8.3 웹훅 보안

1. 결제사 웹훅 서명 검증
2. event id 멱등 처리
3. 성공·실패 이벤트 모두 기록
4. 구독 상태 변경 후 entitlement 테이블 갱신
5. webhook raw body는 필요 최소 기간만 보관
6. 결제 실패 시 grace period 정책 명시

### 8.4 환불 정책 초안

1. 결제 후 7일 이내 환불 요청 가능
2. 단, 유료 기능이 실질적으로 사용되어 로컬 MCP 세션, 파일 처리, AI 분석, 외부 연동이 시작된 경우 환불 제한 가능
3. 중복 결제, 명백한 결제 오류, 회사 귀책 장기 장애는 우선 환불 검토
4. 구독 취소는 다음 결제일부터 적용
5. 강행 법규와 충돌하면 법규 우선

---

## 9. 요금제 초안

### 9.1 Free

목적: 체험과 설치 검증

기능:

- 공개 가이드 열람
- 로컬 에이전트 설치
- 연결 상태 테스트
- 1개 MCP까지 짧은 세션
- 커뮤니티 지원

제한:

- 세션 시간 제한
- 동시 MCP 제한
- 고위험 MCP 제한 가능

### 9.2 Pro

목적: 개인 실무자

기능:

- PowerPoint, Excel, HWP, CAD 기본 연결
- 사용자별 보안 터널
- 대시보드 세션 관리
- 커넥터 URL 발급
- 기본 로그 마스킹

추천 사용자:

- PPT 제작자
- CAD 도면 검토자
- 한글 문서 작업자

### 9.3 Studio

목적: 고급 크리에이터와 설계·문서 작업자

기능:

- Pro 전체
- Photoshop, Blender 연결
- 여러 MCP 동시 세션
- 긴 세션 시간
- 우선 지원

### 9.4 Team 또는 Expert

목적: 사무실·팀 단위

기능:

- 팀 멤버 관리
- 중앙 결제
- 세션 감사 로그
- MCP별 권한 정책
- 전용 서브도메인 또는 전용 relay
- 온보딩 지원

---

## 10. 보안 정책

### 10.1 절대 금지 구조

아래 구조는 피한다.

```text
공용 URL 하나를 모든 사용자가 공유
인증 없는 MCP endpoint 공개
사용자별 토큰 없는 reverse tunnel
로컬 파일 전체 접근 허용
C:/ 전체 allowed root 허용
카드정보 직접 저장
로그에 원문 문서·전체 파일경로 저장
```

### 10.2 권장 구조

```text
사용자별 세션 URL
짧은 만료시간
JWT 또는 signed session token
MCP별 권한 scope
서버측 entitlement check
로컬 에이전트 confirmation gate
위험 작업 preview
세션 종료 버튼
rate limit
IP/UA 이상징후 탐지
```

### 10.3 MCP별 권한 예시

| MCP | 기본 권한 | 위험 권한 | 기본 정책 |
|---|---|---|---|
| Office | 현재 열린 문서 읽기·수정 | 파일 저장/덮어쓰기 | 저장 전 확인 |
| CAD | 현재 도면 정보 조회 | 도면 수정/저장 | 복사본 저장 권장 |
| HWP | 문서 생성·표 작성 | 원본 덮어쓰기 | 새 파일 우선 |
| Photoshop | 레이어 정보/간단 편집 | 원본 이미지 덮어쓰기 | 새 문서 저장 |
| Blender | 장면 조회/오브젝트 추가 | 외부 스크립트 실행 | 제한 필요 |
| Local Code | 프로젝트 읽기 | 코드 수정·명령 실행 | 개발자 전용 |

---

## 11. 참고 사이트 및 MCP 도구 정보 수집 계획

### 11.1 수집 대상

1. OpenCrab 사이트 구조
   - hero
   - architecture
   - workflow
   - target
   - use cases
   - pricing
   - terms/privacy/refunds

2. 로컬 `mcpworld` 문서
   - README
   - PRIVACY
   - MCP tool structure analysis
   - config.example
   - docs changelog

3. MCP별 사용 시나리오
   - CAD level plan correction
   - PPT production review
   - price survey table
   - HWP document automation
   - Photoshop editing
   - Blender current scene editing

### 11.2 도구 분류안

```text
tools/
  office-ppt
  office-excel
  cad-drawing
  hwp-document
  photoshop-design
  blender-visualization
  local-code-dev
```

각 도구 문서에는 다음 파일을 둔다.

```text
README.md
capabilities.md
security-scope.md
sample-prompts.md
pricing-fit.md
privacy-risk.md
```

### 11.3 OpenCrab 관련 범위

OpenCrab은 사이트 구조와 정책 페이지 배치 방식을 참고하는 대상으로만 사용한다. 본 SaaS 프로그램의 제공 MCP 목록에는 포함하지 않는다.

현재는 `planning_required` 상태다.

---

## 12. 기술 스택 제안

### 12.1 MVP 정적 사이트

```text
HTML
CSS
Vanilla JS
```

장점:

- 빠르게 시안 제작 가능
- 배포 쉬움
- 디자인 방향 검증에 적합

### 12.2 SaaS 실제 구현

```text
Frontend: Next.js 또는 SvelteKit
Backend: FastAPI 또는 NestJS
DB: PostgreSQL / Supabase
Auth: Supabase Auth, Auth.js, Clerk 중 선택
Billing: Paddle/Toss/Stripe hosted checkout
Relay: nginx/Caddy + per-user tunnel broker
Local Agent: Python 또는 Tauri Windows app
Monitoring: Sentry + structured logs
```

### 12.3 로컬 에이전트 구현 방향

1차는 기존 MCP World를 기반으로 한다.

개선 방향:

```text
mcpworld.pyw를 그대로 웹 SaaS에 붙이지 말고,
Local Agent 기능을 분리한다.
```

분리할 모듈:

```text
config_manager
process_manager
tunnel_manager
mcp_service_manager
permission_gate
health_reporter
```

---

## 13. MVP 제작 순서

### 13.1 1단계: 정적 랜딩 페이지

대상 파일:

```text
index.html
styles.css
app.js
```

구현 내용:

1. OpenCrab 느낌의 dark/light 대응 레이아웃
2. Hero + architecture diagram
3. MCP tool cards
4. workflow timeline
5. pricing cards
6. security checklist
7. footer policy links

### 13.2 2단계: 문서 페이지

```text
/docs/privacy-checklist.md
/docs/payment-checklist.md
/docs/mcp-tool-map.md
/docs/local-agent-guide.md
```

### 13.3 3단계: 대시보드 목업

```text
dashboard.html
```

포함 요소:

- 로그인 사용자 표시
- 구독 상태
- 로컬 에이전트 온라인/오프라인
- MCP별 상태등
- 커넥터 URL 복사 버튼
- 세션 종료 버튼

### 13.4 4단계: 실제 SaaS 전환

1. Auth 붙이기
2. DB schema 작성
3. 결제 checkout 붙이기
4. webhook으로 entitlement 갱신
5. local agent pairing flow 제작
6. tunnel broker 개발
7. per-user MCP route 발급
8. 보안 테스트

---

## 14. DB 초안

```sql
users
  id
  email
  created_at

subscriptions
  id
  user_id
  provider
  provider_customer_id
  provider_subscription_id
  plan_id
  status
  current_period_end

local_agents
  id
  user_id
  device_name
  device_fingerprint_hash
  last_seen_at
  revoked_at

mcp_sessions
  id
  user_id
  agent_id
  tool_id
  public_route_hash
  token_hash
  status
  expires_at
  created_at
  ended_at

mcp_tools
  id
  name
  category
  risk_level
  default_enabled

usage_events
  id
  user_id
  session_id
  event_type
  metadata_redacted
  created_at
```

---

## 15. 약관 초안 방향

### 15.1 서비스 약관 핵심 조항

1. 서비스 정의
2. 로컬 에이전트와 MCP 연결의 위험 고지
3. 사용자의 로컬 프로그램·파일 백업 책임
4. 금지 행위
5. 구독 결제와 자동갱신
6. 환불 기준
7. 서비스 중단과 제한
8. 지식재산권
9. 면책과 책임 제한
10. 준거법과 분쟁 해결
11. 문의처

### 15.2 반드시 넣을 고지

```text
이 서비스는 사용자의 로컬 프로그램을 MCP를 통해 제어할 수 있습니다.
AI 명령은 예상과 다르게 동작할 수 있으므로, 중요한 파일은 반드시 복사본으로 작업해야 합니다.
```

```text
사용자는 본인이 접근 권한을 가진 파일과 프로그램만 연결해야 합니다.
```

```text
회사는 사용자가 연결한 로컬 프로그램, 제3자 소프트웨어, AI 모델의 결과 정확성을 보장하지 않습니다.
```

---

## 16. 개인정보·결제 체크리스트

### 16.1 공개 전 필수

- [ ] 개인정보 처리방침 작성
- [ ] 서비스 약관 작성
- [ ] 환불 정책 작성
- [ ] 사업자 정보 표시
- [ ] 결제 전 요금·자동갱신·환불 조건 표시
- [ ] 결제 PG 약관 연결
- [ ] 위탁 업체 목록 작성
- [ ] 국외 이전 여부 확인
- [ ] 로그 보관기간 결정
- [ ] 계정 삭제 요청 절차 마련

### 16.2 보안 필수

- [ ] HTTPS 강제
- [ ] 사용자별 tunnel route
- [ ] session token 만료
- [ ] webhook signature 검증
- [ ] rate limit
- [ ] audit log redaction
- [ ] 관리자 2FA
- [ ] secret manager 사용
- [ ] config.json 공개 금지
- [ ] nginx 설정 공개 금지
- [ ] 공개 레포 privacy scan

---

## 17. 샘플 사이트 첫 화면 문안

### Hero title

```text
ChatGPT 웹에서 로컬 CAD와 PowerPoint를 연결하세요.
```

### Hero subtitle

```text
MCP World는 복잡한 서버 실행, 포트, 터널, 커넥터 설정을 한곳에서 관리해 CAD·PPT·Excel·HWP 실무자가 브라우저에서 로컬 MCP를 쉽게 사용할 수 있게 돕습니다.
```

### CTA

```text
Start local MCP
View setup guide
```

### Architecture caption

```text
ChatGPT -> SaaS Gateway -> Secure Tunnel -> Local MCP -> CAD / Office / HWP / Photoshop
```

### Security headline

```text
공개 URL이 아니라 사용자별 세션으로 연결합니다.
```

### Security body

```text
각 MCP 연결은 사용자 계정, 구독 권한, 세션 만료, 로컬 승인 절차를 통과해야 합니다. 작업이 끝나면 터널을 즉시 종료할 수 있습니다.
```

---

## 18. 바로 다음 작업 제안

아래 순서로 진행한다.

1. `index.html`, `styles.css`, `app.js` 정적 랜딩 페이지 생성
2. OpenCrab과 유사한 섹션 배치 적용
3. MCP World 컨셉에 맞게 문구 전면 수정
4. `/docs`에 개인정보·결제·보안 체크리스트 문서 생성
5. 대시보드 목업 추가
6. 실제 결제·인증·터널 기능은 별도 브랜치 또는 별도 프로젝트로 구현

---

## 19. 현 시점 결론

샘플 웹페이지는 단순한 “MCP 모음 사이트”가 아니라 “ChatGPT 웹브라우저에서 로컬 MCP를 안전하게 쓰게 해주는 SaaS 게이트웨이”로 잡아야 한다.

가장 중요한 설계 원칙은 다음이다.

```text
1. 로컬 MCP endpoint를 인증 없이 공개하지 않는다.
2. 사용자별 세션과 구독 권한으로 라우팅한다.
3. 결제 정보는 직접 저장하지 않는다.
4. 로컬 파일 내용과 경로는 최소 수집·마스킹한다.
5. CAD/PPT/HWP 같은 원본 파일 수정은 항상 복사본 저장과 사용자 확인을 우선한다.
```

이 원칙을 지키면 OpenCrab과 비슷한 SaaS 정보 구조를 참고하면서도, 본 서비스만의 핵심 차별점인 “브라우저 기반 로컬 MCP 연결”을 명확하게 보여줄 수 있다.

---

## 20. 약관·동의 UI 추가 반영 사항

오픈소스 검토 결과와 국내 법령 점검 결과를 반영해 `docs` 폴더에 정책 문서를 추가한다.

추가 문서:

```text
docs/privacy-policy-outline.md
docs/terms-and-policy-map.md
docs/business-disclosure.md
docs/consent-ui-plan.md
docs/local-agent-risk-notice.md
docs/data-retention-and-processing.md
```

핵심 반영 방향:

1. 사업자 정보 고지 문서를 별도로 둔다.
2. 처리방침 필수 항목을 체크리스트화한다.
3. 로그인, 결제, 로컬 에이전트, 자동 수집 정보를 항목별로 분리한다.
4. 필수 동의와 선택 동의를 분리한다.
5. 쿠키 설정 범주를 나눈다.
6. 로컬 에이전트 설치 전 별도 고지 화면을 둔다.
7. 자동 판단 사용 여부는 조건부 고지 항목으로 관리한다.
8. 회사 책임을 전부 배제하는 표현은 사용하지 않는다.
