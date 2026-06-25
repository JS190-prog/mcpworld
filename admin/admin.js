const ADMIN_AUTH_KEY = 'mcpworld_operator_unlocked';
const ADMIN_EMAILS = new Set(['sky7823a@gmail.com']);

const adminGate = document.querySelector('#adminGate');
const adminContent = document.querySelector('#adminContent');
const adminTokenInput = document.querySelector('#adminTokenInput');
const adminTokenSubmit = document.querySelector('#adminTokenSubmit');
const adminTokenMessage = document.querySelector('#adminTokenMessage');
const adminLockButton = document.querySelector('#adminLockButton');
const rangeSelect = document.querySelector('#rangeSelect');
const planSelect = document.querySelector('#planSelect');
const riskSelect = document.querySelector('#riskSelect');
const refreshAdminData = document.querySelector('#refreshAdminData');
const runTriageButton = document.querySelector('#runTriageButton');
const userSearchInput = document.querySelector('#userSearchInput');
const expireStaleButton = document.querySelector('#expireStaleButton');
const clearLogFilterButton = document.querySelector('#clearLogFilterButton');
const issueList = document.querySelector('#issueList');
const issueDetail = document.querySelector('#issueDetail');
const userTableBody = document.querySelector('#userTable tbody');
const sessionTableBody = document.querySelector('#sessionTable tbody');
const logTableBody = document.querySelector('#logTable tbody');
const actionFeed = document.querySelector('#actionFeed');
const adminToast = document.querySelector('#adminToast');

const kpiUsers = document.querySelector('#kpiUsers');
const kpiSessions = document.querySelector('#kpiSessions');
const kpiConnectors = document.querySelector('#kpiConnectors');
const kpiIssues = document.querySelector('#kpiIssues');
const kpiErrorRate = document.querySelector('#kpiErrorRate');
const kpiRelay = document.querySelector('#kpiRelay');

const users = [
  { id: 'u-1001', name: '데모 사용자', email: 'demo@mcpworld.local', plan: 'Pro', status: 'active', lastSeen: '2분 전', risk: 'normal', sessions: 3 },
  { id: 'u-1017', name: 'Flow Studio', email: 'ops@flowstudio.kr', plan: 'Team', status: 'active', lastSeen: '5분 전', risk: 'warning', sessions: 12 },
  { id: 'u-1024', name: 'CAD 검토자', email: 'cad24@example.com', plan: 'Pro', status: 'limited', lastSeen: '11분 전', risk: 'critical', sessions: 9 },
  { id: 'u-1033', name: '문서 자동화', email: 'hwpdesk@example.com', plan: 'Starter', status: 'active', lastSeen: '28분 전', risk: 'normal', sessions: 1 },
  { id: 'u-1040', name: '결제 확인 필요', email: 'billing40@example.com', plan: 'Studio', status: 'billing_hold', lastSeen: '1시간 전', risk: 'warning', sessions: 0 }
];

const sessions = [
  { id: 'ses-cad-82a', user: 'cad24@example.com', tool: 'CAD / ZWCAD', status: 'active', relay: '780ms', expires: '14분', risk: 'critical' },
  { id: 'ses-ppt-11f', user: 'ops@flowstudio.kr', tool: 'PowerPoint', status: 'active', relay: '210ms', expires: '42분', risk: 'warning' },
  { id: 'ses-xls-7c2', user: 'demo@mcpworld.local', tool: 'Excel', status: 'active', relay: '80ms', expires: '55분', risk: 'normal' },
  { id: 'ses-hwp-6d9', user: 'hwpdesk@example.com', tool: 'HWP', status: 'idle', relay: '120ms', expires: '8분', risk: 'warning' },
  { id: 'ses-blend-40e', user: 'demo@mcpworld.local', tool: 'Blender', status: 'active', relay: '95ms', expires: '65분', risk: 'normal' }
];

const issues = [
  {
    id: 'inc-2401',
    title: 'CAD relay 지연 증가',
    severity: 'critical',
    owner: 'cad24@example.com',
    impact: 'CAD/ZWCAD 세션 3개에서 700ms 이상 지연',
    cause: '사용자별 tunnel broker 재시작 필요 가능성',
    action: 'Relay 재시작 또는 해당 사용자 세션 종료'
  },
  {
    id: 'inc-2402',
    title: '결제 웹훅 재시도 필요',
    severity: 'warning',
    owner: 'billing40@example.com',
    impact: 'Studio 구독 상태가 billing_hold로 남음',
    cause: 'PG webhook 서명 검증 후 DB 갱신 실패',
    action: '웹훅 재처리 큐 이동'
  },
  {
    id: 'inc-2403',
    title: '인증 실패 반복',
    severity: 'warning',
    owner: 'ops@flowstudio.kr',
    impact: '최근 10분간 관리자/사용자 인증 실패 7회',
    cause: '잘못된 토큰 또는 자동화된 재시도',
    action: '계정 임시 제한 또는 MFA 재설정 안내'
  }
];

let logs = [
  { time: '09:42', type: 'relay', target: 'ses-cad-82a', message: 'CAD relay latency above 700ms', status: 'warning' },
  { time: '09:39', type: 'billing', target: 'billing40@example.com', message: 'subscription webhook retry required', status: 'warning' },
  { time: '09:35', type: 'auth', target: 'ops@flowstudio.kr', message: 'repeated login failure detected', status: 'error' },
  { time: '09:31', type: 'session', target: 'ses-hwp-6d9', message: 'idle session close to expiry', status: 'warning' },
  { time: '09:28', type: 'admin', target: 'operator', message: 'operator console opened', status: 'success' }
];

function getCurrentUser() {
  try {
    return JSON.parse(sessionStorage.getItem('mcpworld_demo_user') || '{}');
  } catch {
    return {};
  }
}

function getCurrentUserEmail() {
  return (getCurrentUser().email || '').toLowerCase();
}

function isCurrentAdmin() {
  return ADMIN_EMAILS.has(getCurrentUserEmail());
}

async function getApi(path) {
  const separator = path.includes('?') ? '&' : '?';
  const adminPath = `${path}${separator}email=${encodeURIComponent(getCurrentUserEmail())}`;
  const response = await fetch(`../api${adminPath}`, {
    headers: { 'X-MCPWorld-Admin-Email': getCurrentUserEmail() }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) throw new Error(data.error || 'api_error');
  return data;
}

async function postApi(path, payload) {
  const response = await fetch(`../api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, actorEmail: getCurrentUserEmail() })
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) throw new Error(data.error || 'api_error');
  return data;
}

function getDemoAdminCode() {
  return ['mcpworld', 'admin', '2026'].join('-');
}

function numberWithComma(value) {
  return new Intl.NumberFormat('ko-KR').format(value);
}

function severityLabel(value) {
  return { critical: '긴급', warning: '주의', normal: '정상' }[value] || value;
}

function statusLabel(value) {
  return {
    active: '활성',
    limited: '제한',
    billing_hold: '결제 보류',
    idle: '유휴',
    terminated: '종료',
    success: '정상',
    warning: '주의',
    error: '오류'
  }[value] || value;
}

function showToast(message) {
  if (!adminToast) return;
  adminToast.textContent = message;
  adminToast.classList.remove('hidden');
  setTimeout(() => adminToast.classList.add('hidden'), 1800);
}

function addAction(message, status = 'success') {
  const now = new Date();
  const time = now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
  logs = [{ time, type: 'admin', target: 'operator', message, status }, ...logs];
  renderLogs();
  renderActionFeed();
  showToast(message);
}

function getVisibleIssues() {
  const risk = riskSelect?.value || 'all';
  return risk === 'all' ? issues : issues.filter((issue) => issue.severity === risk);
}

function renderKpis() {
  const visibleIssues = getVisibleIssues();
  const activeSessions = sessions.filter((session) => session.status === 'active').length;
  const warnings = issues.filter((issue) => issue.severity !== 'normal').length;
  if (kpiUsers) kpiUsers.textContent = numberWithComma(users.length);
  if (kpiSessions) kpiSessions.textContent = numberWithComma(activeSessions);
  if (kpiConnectors) kpiConnectors.textContent = numberWithComma(641);
  if (kpiIssues) kpiIssues.textContent = numberWithComma(visibleIssues.length);
  if (kpiErrorRate) kpiErrorRate.textContent = warnings >= 3 ? '2.8%' : '1.1%';
  if (kpiRelay) kpiRelay.textContent = issues.some((issue) => issue.severity === 'critical') ? '주의' : '정상';
}

function renderIssues(selectedId = issues[0]?.id) {
  if (!issueList) return;
  const visibleIssues = getVisibleIssues();
  issueList.innerHTML = '';
  visibleIssues.forEach((issue) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `issue-card ${issue.severity}`;
    button.dataset.issueId = issue.id;
    button.innerHTML = `
      <span class="issue-severity">${severityLabel(issue.severity)}</span>
      <strong>${issue.title}</strong>
      <small>${issue.owner}</small>
      <p>${issue.impact}</p>
    `;
    button.addEventListener('click', () => renderIssueDetail(issue.id));
    issueList.appendChild(button);
  });
  renderIssueDetail(selectedId);
}

function renderIssueDetail(issueId) {
  const issue = issues.find((item) => item.id === issueId) || getVisibleIssues()[0];
  if (!issueDetail || !issue) return;
  issueDetail.innerHTML = `
    <p class="eyebrow">Selected Issue</p>
    <h3>${issue.title}</h3>
    <dl class="ops-definition">
      <dt>위험도</dt><dd>${severityLabel(issue.severity)}</dd>
      <dt>대상</dt><dd>${issue.owner}</dd>
      <dt>영향</dt><dd>${issue.impact}</dd>
      <dt>원인 추정</dt><dd>${issue.cause}</dd>
      <dt>권장 조치</dt><dd>${issue.action}</dd>
    </dl>
    <div class="ops-actions">
      <button class="btn btn-primary" data-action="resolve-issue" data-issue="${issue.id}" type="button">조치 완료</button>
      <button class="btn btn-secondary" data-action="open-user" data-owner="${issue.owner}" type="button">사용자 찾기</button>
    </div>
  `;
}

function renderUsers() {
  if (!userTableBody) return;
  const query = (userSearchInput?.value || '').trim().toLowerCase();
  const plan = planSelect?.value || 'all';
  const rows = users.filter((user) => {
    const planMatch = plan === 'all' || user.plan.toLowerCase() === plan;
    const queryMatch = !query || `${user.name} ${user.email} ${user.plan}`.toLowerCase().includes(query);
    return planMatch && queryMatch;
  });
  userTableBody.innerHTML = '';
  rows.forEach((user) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${user.name}</strong><br><small>${user.email}</small></td>
      <td>${user.plan}</td>
      <td><span class="status-pill ${user.status}">${statusLabel(user.status)}</span></td>
      <td>${user.lastSeen}<br><small>${user.sessions} sessions</small></td>
      <td><span class="risk-pill ${user.risk}">${severityLabel(user.risk)}</span></td>
      <td class="table-actions">
        <button class="btn btn-secondary" data-action="reset-mfa" data-user="${user.email}" type="button">MFA 재설정</button>
        <button class="btn btn-secondary" data-action="lock-user" data-user="${user.email}" type="button">계정 제한</button>
        <button class="btn btn-secondary" data-action="kill-user-sessions" data-user="${user.email}" type="button">세션 종료</button>
      </td>
    `;
    userTableBody.appendChild(tr);
  });
}

function renderSessions() {
  if (!sessionTableBody) return;
  const risk = riskSelect?.value || 'all';
  const rows = risk === 'all' ? sessions : sessions.filter((session) => session.risk === risk);
  sessionTableBody.innerHTML = '';
  rows.forEach((session) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${session.id}</strong></td>
      <td>${session.user}</td>
      <td>${session.tool}</td>
      <td><span class="status-pill ${session.status}">${statusLabel(session.status)}</span></td>
      <td>${session.relay}</td>
      <td>${session.expires}</td>
      <td class="table-actions">
        <button class="btn btn-secondary" data-action="terminate-session" data-session="${session.id}" type="button">종료</button>
        <button class="btn btn-secondary" data-action="extend-session" data-session="${session.id}" type="button">연장</button>
      </td>
    `;
    sessionTableBody.appendChild(tr);
  });
}

function renderLogs(filter = 'all') {
  if (!logTableBody) return;
  const rows = filter === 'all' ? logs : logs.filter((row) => row.type === filter || row.status === filter);
  logTableBody.innerHTML = '';
  rows.forEach((row) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.time}</td>
      <td>${row.type}</td>
      <td>${row.target}</td>
      <td>${row.message}</td>
      <td><span class="event-status ${row.status}">${statusLabel(row.status)}</span></td>
    `;
    logTableBody.appendChild(tr);
  });
}

function renderActionFeed() {
  if (!actionFeed) return;
  actionFeed.innerHTML = '';
  logs.slice(0, 6).forEach((row) => {
    const item = document.createElement('div');
    item.className = `feed-item ${row.status}`;
    item.innerHTML = `<strong>${row.time}</strong><span>${row.message}</span>`;
    actionFeed.appendChild(item);
  });
}

function renderAll() {
  renderKpis();
  renderIssues();
  renderUsers();
  renderSessions();
  renderLogs();
  renderActionFeed();
}

async function hydrateFromApi() {
  try {
    const data = await getApi('/admin/bootstrap');
    if (Array.isArray(data.users) && data.users.length) {
      users.splice(0, users.length, ...data.users.map((user) => ({
        id: user.id,
        name: user.displayName,
        email: user.email,
        plan: user.plan,
        status: user.status,
        lastSeen: user.lastSeenAt ? new Date(user.lastSeenAt * 1000).toLocaleString('ko-KR') : '-',
        risk: user.risk,
        sessions: 0
      })));
    }
    if (Array.isArray(data.sessions)) {
      sessions.splice(0, sessions.length, ...data.sessions.map((session) => ({
        id: session.id,
        user: session.user_id,
        tool: session.tool,
        status: session.status,
        relay: session.relay_status,
        expires: session.expires_at ? new Date(session.expires_at * 1000).toLocaleTimeString('ko-KR') : '-',
        risk: session.status === 'active' ? 'normal' : 'warning'
      })));
    }
    if (Array.isArray(data.logs)) {
      logs = data.logs.map((row) => ({
        time: new Date(row.at * 1000).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
        type: row.event_type,
        target: row.target,
        message: row.message,
        status: row.status
      }));
    }
  } catch {
    addAction('API 연결 실패. 정적 데모 데이터로 표시합니다.', 'warning');
  }
}

function unlockAdmin() {
  sessionStorage.setItem(ADMIN_AUTH_KEY, 'true');
  adminGate?.classList.add('hidden');
  adminContent?.classList.remove('hidden');
  adminLockButton?.classList.remove('hidden');
  renderAll();
}

function lockAdmin() {
  sessionStorage.removeItem(ADMIN_AUTH_KEY);
  adminContent?.classList.add('hidden');
  adminGate?.classList.remove('hidden');
  adminLockButton?.classList.add('hidden');
  if (adminTokenInput) adminTokenInput.value = '';
  if (!isCurrentAdmin()) {
    if (adminTokenInput) adminTokenInput.disabled = true;
    if (adminTokenSubmit) adminTokenSubmit.disabled = true;
    if (adminTokenMessage) {
      adminTokenMessage.textContent = '관리자 권한이 있는 계정으로 로그인해야 운영 콘솔을 열 수 있습니다.';
      adminTokenMessage.classList.add('error');
    }
  } else {
    if (adminTokenInput) adminTokenInput.disabled = false;
    if (adminTokenSubmit) adminTokenSubmit.disabled = false;
  }
}

adminTokenSubmit?.addEventListener('click', () => {
  if (!isCurrentAdmin()) {
    if (adminTokenMessage) {
      adminTokenMessage.textContent = '관리자 권한이 없는 계정입니다.';
      adminTokenMessage.classList.add('error');
    }
    return;
  }
  const typedCode = adminTokenInput?.value.trim() || '';
  if (typedCode === getDemoAdminCode()) {
    if (adminTokenMessage) {
      adminTokenMessage.textContent = '토큰 확인 완료. 운영 콘솔을 엽니다.';
      adminTokenMessage.classList.remove('error');
    }
    unlockAdmin();
    return;
  }
  if (adminTokenMessage) {
    adminTokenMessage.textContent = '운영자 토큰이 올바르지 않습니다.';
    adminTokenMessage.classList.add('error');
  }
});

adminTokenInput?.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') adminTokenSubmit?.click();
});

document.addEventListener('click', (event) => {
  const target = event.target.closest('[data-action], [data-runbook]');
  if (!target) return;
  const action = target.dataset.action || target.dataset.runbook;
  const user = target.dataset.user;
  const session = target.dataset.session;
  const issue = target.dataset.issue;
  const owner = target.dataset.owner;

  const messages = {
    'resolve-issue': `${issue} 조치 완료로 기록했습니다.`,
    'open-user': `${owner} 사용자를 검색 필터에 입력했습니다.`,
    'reset-mfa': `${user} MFA 재설정 링크를 발급했습니다.`,
    'lock-user': `${user} 계정에 임시 제한을 적용했습니다.`,
    'kill-user-sessions': `${user}의 활성 세션 종료 요청을 보냈습니다.`,
    'terminate-session': `${session} 세션 종료 요청을 보냈습니다.`,
    'extend-session': `${session} 세션 만료 시간을 연장했습니다.`,
    'relay-restart': 'Relay 재시작 작업을 큐에 등록했습니다.',
    'billing-retry': '결제 웹훅 실패분을 재처리 큐로 이동했습니다.',
    'rate-limit': '비정상 세션 계정에 임시 rate limit을 적용했습니다.',
    'export-audit': '감사 로그 CSV 생성 작업을 시작했습니다.'
  };

  postApi('/admin/action', { action, target: user || session || issue || owner || 'system' }).catch(() => {});

  if (action === 'open-user' && userSearchInput) {
    userSearchInput.value = owner;
    renderUsers();
  }
  addAction(messages[action] || '운영 조치를 기록했습니다.');
});

adminLockButton?.addEventListener('click', lockAdmin);
refreshAdminData?.addEventListener('click', () => {
  hydrateFromApi().finally(() => {
    renderAll();
    addAction('운영 데이터를 새로고침했습니다.');
  });
});
runTriageButton?.addEventListener('click', () => {
  riskSelect.value = 'critical';
  renderAll();
  addAction('긴급 이슈만 표시하도록 자동 분류했습니다.', 'warning');
});
expireStaleButton?.addEventListener('click', () => {
  addAction('만료 임박 세션 종료 작업을 큐에 등록했습니다.', 'warning');
});
clearLogFilterButton?.addEventListener('click', () => renderLogs());
rangeSelect?.addEventListener('change', renderAll);
planSelect?.addEventListener('change', () => {
  renderKpis();
  renderUsers();
});
riskSelect?.addEventListener('change', renderAll);
userSearchInput?.addEventListener('input', renderUsers);

if (isCurrentAdmin() && sessionStorage.getItem(ADMIN_AUTH_KEY) === 'true') {
  hydrateFromApi().finally(unlockAdmin);
} else {
  lockAdmin();
}
