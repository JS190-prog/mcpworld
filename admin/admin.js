const ADMIN_AUTH_KEY = 'mcpworld_operator_unlocked';

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
const toolHealthTableBody = document.querySelector('#toolHealthTable tbody');
const adminTokenTableBody = document.querySelector('#adminTokenTable tbody');
const adminTokenNameInput = document.querySelector('#adminTokenName');
const adminTokenRoleSelect = document.querySelector('#adminTokenRole');
const createAdminTokenButton = document.querySelector('#createAdminTokenButton');
const newAdminTokenBox = document.querySelector('#newAdminTokenBox');
const actionFeed = document.querySelector('#actionFeed');
const adminToast = document.querySelector('#adminToast');

const kpiUsers = document.querySelector('#kpiUsers');
const kpiSessions = document.querySelector('#kpiSessions');
const kpiConnectors = document.querySelector('#kpiConnectors');
const kpiIssues = document.querySelector('#kpiIssues');
const kpiErrorRate = document.querySelector('#kpiErrorRate');
const kpiRelay = document.querySelector('#kpiRelay');

const users = [];
const sessions = [];
const issues = [];
const toolHealth = [];
const adminTokens = [];
let logs = [];
let actionRows = [];
const planOptions = ['Free', 'Pro', 'Expert', 'Admin'];
let summary = {
  users: 0,
  activeSessions: 0,
  issuedToday: 0,
  issues: 0,
  errorRate: 0,
  relay: 'normal'
};
let adminCapabilities = {
  role: null,
  canMutate: false
};

async function getApi(path) {
  const response = await fetch(`../api${path}`, { credentials: 'same-origin' });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) throw new Error(data.error || 'api_error');
  return data;
}

async function postApi(path, payload) {
  const response = await fetch(`../api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) throw new Error(data.error || 'api_error');
  return data;
}

function numberWithComma(value) {
  return new Intl.NumberFormat('ko-KR').format(Number(value || 0));
}

function severityLabel(value) {
  return { critical: 'Critical', warning: 'Warning', normal: 'Normal' }[value] || value || '-';
}

function statusLabel(value) {
  return {
    active: 'Active',
    limited: 'Limited',
    billing_hold: 'Billing hold',
    idle: 'Idle',
    terminated: 'Terminated',
    success: 'Success',
    warning: 'Warning',
    error: 'Error',
    queued: 'Queued',
    running: 'Running',
    revoked: 'Revoked',
    ready: 'Ready',
    no_calls: 'No calls',
    stale: 'Stale',
    busy: 'Busy',
    needs_setup: 'Needs setup'
  }[value] || value || '-';
}

function mutationAttrs() {
  return adminCapabilities.canMutate ? '' : ' disabled title="Read-only operator account"';
}

function escapeSelector(value) {
  if (window.CSS?.escape) return CSS.escape(value);
  return String(value).replace(/["\\]/g, '\\$&');
}

function renderPlanSelect(user) {
  const options = planOptions.map((plan) => {
    const selected = plan.toLowerCase() === (user.plan || '').toLowerCase() ? ' selected' : '';
    return `<option value="${plan}"${selected}>${plan}</option>`;
  }).join('');
  return `
    <div class="inline-control">
      <select data-plan-for="${user.email}"${mutationAttrs()}>${options}</select>
      <button class="btn btn-secondary" data-action="set-plan" data-user="${user.email}" type="button"${mutationAttrs()}>Apply</button>
    </div>
  `;
}

function showToast(message) {
  if (!adminToast) return;
  adminToast.textContent = message;
  adminToast.classList.remove('hidden');
  setTimeout(() => adminToast.classList.add('hidden'), 1800);
}

function addAction(message, status = 'success') {
  if (status === 'error') {
    console.error(message);
  }
  showToast(message);
}

function formatDateTime(seconds) {
  return seconds ? new Date(seconds * 1000).toLocaleString('ko-KR') : '-';
}

function formatTime(seconds) {
  return seconds ? new Date(seconds * 1000).toLocaleTimeString('ko-KR') : '-';
}

function getVisibleIssues() {
  const risk = riskSelect?.value || 'all';
  return risk === 'all' ? issues : issues.filter((issue) => issue.severity === risk);
}

function renderKpis() {
  const visibleIssues = getVisibleIssues();
  if (kpiUsers) kpiUsers.textContent = numberWithComma(summary.users ?? users.length);
  if (kpiSessions) kpiSessions.textContent = numberWithComma(summary.activeSessions ?? 0);
  if (kpiConnectors) kpiConnectors.textContent = numberWithComma(summary.issuedToday ?? 0);
  if (kpiIssues) kpiIssues.textContent = numberWithComma(summary.issues ?? visibleIssues.length);
  if (kpiErrorRate) kpiErrorRate.textContent = `${summary.errorRate ?? 0}%`;
  if (kpiRelay) kpiRelay.textContent = summary.relay || 'normal';
}

function renderIssues(selectedId = issues[0]?.id) {
  if (!issueList) return;
  const visibleIssues = getVisibleIssues();
  issueList.innerHTML = '';
  if (!visibleIssues.length) {
    issueList.innerHTML = '<p class="muted">현재 운영자가 처리할 문제가 없습니다.</p>';
    if (issueDetail) issueDetail.innerHTML = '<p class="muted">실시간 점검 결과가 정상입니다.</p>';
    return;
  }
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

function issuePlaybook(issue) {
  const defaults = {
    decision: '영향 대상과 최근 로그를 확인한 뒤 정상 사용이면 유지하고, 의심스러운 사용이면 계정 제한 또는 세션 종료를 실행하세요.',
    steps: [
      '오른쪽 상세의 영향 범위와 원인 추정을 확인합니다.',
      '아래 로그/세션/사용자 표에서 같은 대상이 반복되는지 확인합니다.',
      '필요한 행의 조치 버튼을 눌러 처리한 뒤 Action Feed와 로그에 성공 기록이 남았는지 확인합니다.'
    ],
    buttons: [
      { label: '로그 표로 이동', section: 'logs' },
      { label: '세션 표로 이동', section: 'sessions' }
    ],
    supportedActions: ['사용자 표: Limit, End sessions', '세션 표: End, Extend', '도구 상태 표: End sessions, Review']
  };
  const playbooks = {
    'ops-expiring-sessions': {
      decision: '정상 사용자가 아직 작업 중이면 세션을 연장하고, 사용자가 작업을 끝냈거나 의심스러우면 세션을 종료합니다.',
      steps: [
        '활성 세션 표로 이동해 만료 시간이 임박한 행을 확인합니다.',
        '사용자가 정상 작업 중이면 해당 세션 행의 Extend를 누릅니다.',
        '알 수 없는 사용자거나 작업 종료 상태면 End를 눌러 연결을 닫습니다.',
        '사용자에게 새 연결이 필요하면 대시보드에서 링크를 다시 생성하도록 안내합니다.'
      ],
      buttons: [{ label: '활성 세션 표로 이동', section: 'sessions' }],
      supportedActions: ['세션 표: Extend', '세션 표: End']
    },
    'ops-stale-tool-calls': {
      decision: '도구 호출이 오래 대기 중이면 Agent 연결 상태를 확인하고, 멈춘 세션은 종료해서 새 링크로 다시 연결하게 합니다.',
      steps: [
        '도구 상태 표에서 대기/실행 수가 높은 도구를 확인합니다.',
        '같은 도구의 최근 오류가 반복되면 해당 도구 행의 End sessions를 눌러 멈춘 연결을 정리합니다.',
        '사용자에게 MCPWorld Agent를 다시 열고 도구 연결 링크를 재생성하도록 안내합니다.',
        '정리 후 새 호출이 queued/running에 계속 쌓이는지 새로고침으로 확인합니다.'
      ],
      buttons: [
        { label: '도구 상태 표로 이동', section: 'tool-health' },
        { label: '활성 세션 표로 이동', section: 'sessions' }
      ],
      supportedActions: ['도구 상태 표: End sessions', '세션 표: End']
    },
    'ops-offline-agents': {
      decision: 'Agent가 오프라인이면 서버에서 강제로 복구하기보다 사용자 PC의 Agent 실행 상태를 먼저 확인시켜야 합니다.',
      steps: [
        '도구 상태 표와 활성 세션 표에서 영향 받는 사용자와 도구를 확인합니다.',
        '사용자에게 MCPWorld Agent가 실행 중인지, 방화벽/백신이 막지 않는지 확인하도록 안내합니다.',
        '오래된 세션은 세션 표에서 End를 눌러 정리합니다.',
        '사용자가 Agent를 다시 실행한 뒤 대시보드에서 새 연결 링크를 생성하도록 안내합니다.'
      ],
      buttons: [
        { label: '도구 상태 표로 이동', section: 'tool-health' },
        { label: '활성 세션 표로 이동', section: 'sessions' }
      ],
      supportedActions: ['세션 표: End', '도구 상태 표: Review']
    },
    'ops-recent-failures': {
      decision: '최근 실패 이벤트는 먼저 로그에서 대상을 확인하고, 같은 사용자/세션에서 반복되면 제한 또는 세션 종료를 실행합니다.',
      steps: [
        '로그와 조치 이력 표로 이동해 Error/Warning 행의 대상과 내용을 확인합니다.',
        '인증 실패가 반복되는 계정은 사용자 표에서 Limit를 누릅니다.',
        '특정 사용자 세션에서 호출 실패가 반복되면 사용자 표의 End sessions 또는 세션 표의 End를 누릅니다.',
        '조치 후 같은 오류가 계속 남는지 새로고침으로 확인합니다.'
      ],
      buttons: [
        { label: '로그 표로 이동', section: 'logs' },
        { label: '사용자 표로 이동', section: 'users' }
      ],
      supportedActions: ['사용자 표: Limit', '사용자 표: End sessions', '세션 표: End']
    }
  };
  return { ...defaults, ...(playbooks[issue.id] || {}) };
}

function renderIssueDetail(issueId) {
  const issue = issues.find((item) => item.id === issueId) || getVisibleIssues()[0];
  if (!issueDetail || !issue) return;
  const playbook = issuePlaybook(issue);
  issueDetail.innerHTML = `
    <p class="eyebrow">Operator Playbook</p>
    <h3>${issue.title}</h3>
    <dl class="ops-definition">
      <dt>위험도</dt><dd>${severityLabel(issue.severity)}</dd>
      <dt>담당 영역</dt><dd>${issue.owner}</dd>
      <dt>영향 범위</dt><dd>${issue.impact}</dd>
      <dt>원인 추정</dt><dd>${issue.cause}</dd>
      <dt>판단 기준</dt><dd>${playbook.decision}</dd>
    </dl>
    <div class="operator-steps">
      <strong>관리자가 할 일</strong>
      <ol>${playbook.steps.map((step) => `<li>${step}</li>`).join('')}</ol>
    </div>
    <div class="operator-steps">
      <strong>실제로 누를 수 있는 조치</strong>
      <ul>${playbook.supportedActions.map((action) => `<li>${action}</li>`).join('')}</ul>
    </div>
    <div class="ops-actions">
      ${playbook.buttons.map((button) => `<button class="btn btn-secondary" data-ui-action="focus-section" data-section="${button.section}" type="button">${button.label}</button>`).join('')}
    </div>
  `;
}

function renderUsers() {
  if (!userTableBody) return;
  const query = (userSearchInput?.value || '').trim().toLowerCase();
  const plan = planSelect?.value || 'all';
  const rows = users.filter((user) => {
    const planMatch = plan === 'all' || (user.plan || '').toLowerCase() === plan;
    const queryMatch = !query || `${user.name} ${user.email} ${user.plan}`.toLowerCase().includes(query);
    return planMatch && queryMatch;
  });
  userTableBody.innerHTML = '';
  rows.forEach((user) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${user.name}</strong><br><small>${user.email}</small></td>
      <td>${renderPlanSelect(user)}</td>
      <td><span class="status-pill ${user.status}">${statusLabel(user.status)}</span></td>
      <td>${user.lastSeen}<br><small>${numberWithComma(user.sessions)} sessions</small></td>
      <td><span class="risk-pill ${user.risk}">${severityLabel(user.risk)}</span></td>
      <td class="table-actions">
        <button class="btn btn-secondary" data-action="lock-user" data-user="${user.email}" type="button"${mutationAttrs()}>Limit</button>
        <button class="btn btn-secondary" data-action="kill-user-sessions" data-user="${user.email}" type="button"${mutationAttrs()}>End sessions</button>
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
        <button class="btn btn-secondary" data-action="terminate-session" data-session="${session.id}" type="button"${mutationAttrs()}>End</button>
        <button class="btn btn-secondary" data-action="extend-session" data-session="${session.id}" type="button"${mutationAttrs()}>Extend</button>
      </td>
    `;
    sessionTableBody.appendChild(tr);
  });
}

function renderToolHealth() {
  if (!toolHealthTableBody) return;
  toolHealthTableBody.innerHTML = '';
  if (!toolHealth.length) {
    toolHealthTableBody.innerHTML = '<tr><td colspan="8">No tool health data yet.</td></tr>';
    return;
  }
  toolHealth.forEach((tool) => {
    const tr = document.createElement('tr');
    const queueText = `${numberWithComma(tool.queued || 0)} / ${numberWithComma(tool.running || 0)}`;
    tr.innerHTML = `
      <td><strong>${tool.label}</strong><br><small>${tool.slug}</small></td>
      <td><span class="risk-pill ${tool.severity}">${statusLabel(tool.status)}</span><br><small>${numberWithComma(tool.activeSessions || 0)} active sessions</small></td>
      <td>${numberWithComma(tool.callsToday || 0)}<br><small>${numberWithComma(tool.recentCalls || 0)} recent</small></td>
      <td>${queueText}<br><small>${numberWithComma(tool.stale || 0)} stale</small></td>
      <td>${numberWithComma(tool.failed || 0)}</td>
      <td>${tool.lastError || '-'}<br><small>${formatDateTime(tool.lastUpdatedAt)}</small></td>
      <td>${tool.recommendation || '-'}</td>
      <td class="table-actions">
        <button class="btn btn-secondary" data-action="mark-tool-reviewed" data-tool="${tool.slug}" type="button"${mutationAttrs()}>Review</button>
        <button class="btn btn-secondary" data-action="terminate-tool-sessions" data-tool="${tool.slug}" type="button"${mutationAttrs()}>End sessions</button>
      </td>
    `;
    toolHealthTableBody.appendChild(tr);
  });
}

function renderLogs(filter = 'all') {
  if (!logTableBody) return;
  const rows = filter === 'all' ? logs : logs.filter((row) => row.type === filter || row.status === filter);
  logTableBody.innerHTML = '';
  if (!rows.length) {
    logTableBody.innerHTML = '<tr><td colspan="5">No operator actions, auth failures, relay errors, or billing webhook events yet.</td></tr>';
    return;
  }
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

function renderAdminTokens() {
  if (!adminTokenTableBody) return;
  adminTokenTableBody.innerHTML = '';
  if (!adminTokens.length) {
    adminTokenTableBody.innerHTML = '<tr><td colspan="6">No admin tokens yet.</td></tr>';
    return;
  }
  adminTokens.forEach((token) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${token.name}</strong><br><small>${token.id}</small></td>
      <td>${token.role}</td>
      <td><span class="status-pill ${token.status}">${statusLabel(token.status)}</span></td>
      <td>${token.createdBy || '-'}</td>
      <td>${formatDateTime(token.lastUsedAt)}</td>
      <td class="table-actions">
        <button class="btn btn-secondary" data-action="revoke-admin-token" data-token="${token.id}" type="button"${token.status === 'active' ? mutationAttrs() : ' disabled'}>Revoke</button>
      </td>
    `;
    adminTokenTableBody.appendChild(tr);
  });
}

function renderActionFeed() {
  if (!actionFeed) return;
  actionFeed.innerHTML = '';
  if (!actionRows.length) {
    actionFeed.innerHTML = '<div class="feed-item success"><strong>Ready</strong><span>No operator actions have been recorded yet.</span></div>';
    return;
  }
  actionRows.slice(0, 6).forEach((row) => {
    const item = document.createElement('div');
    item.className = `feed-item ${row.status}`;
    item.innerHTML = `<strong>${row.time}</strong><span>${row.message}</span>`;
    actionFeed.appendChild(item);
  });
}

function renderAll() {
  renderKpis();
  renderIssues();
  renderToolHealth();
  renderUsers();
  renderSessions();
  renderAdminTokens();
  renderLogs();
  renderActionFeed();
}

async function hydrateFromApi() {
  const data = await getApi('/admin/bootstrap');
  summary = { ...summary, ...(data.summary || {}) };
  adminCapabilities = {
    role: data.admin?.role || null,
    canMutate: data.capabilities?.canMutate === true
  };
  users.splice(0, users.length, ...(data.users || []).map((user) => ({
    id: user.id,
    name: user.displayName || user.name || user.email,
    email: user.email,
    plan: user.plan || '-',
    status: user.status || '-',
    lastSeen: formatDateTime(user.lastSeenAt || user.last_seen_at),
    risk: user.risk || 'normal',
    sessions: user.sessionCount || user.sessions || 0
  })));
  sessions.splice(0, sessions.length, ...(data.sessions || []).map((session) => ({
    id: session.id,
    user: session.user_email || session.userEmail || session.user_id,
    tool: session.tool,
    status: session.status,
    relay: session.relay_status || session.relay || '-',
    expires: formatTime(session.expires_at || session.expiresAt),
    risk: session.status === 'active' ? 'normal' : 'warning'
  })));
  issues.splice(0, issues.length, ...(data.issues || []));
  toolHealth.splice(0, toolHealth.length, ...(data.toolHealth || data.usage?.toolHealth || []));
  adminTokens.splice(0, adminTokens.length, ...(data.tokens || []));
  logs = (data.logs || []).map((row) => ({
    time: row.at ? formatTime(row.at) : row.time || '-',
    type: row.event_type || row.type || 'event',
    target: row.target || '-',
    message: row.message || '',
    status: row.status || 'success'
  }));
  actionRows = logs.filter((row) => row.type.startsWith('admin.'));
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
  if (adminTokenSubmit) adminTokenSubmit.disabled = false;
}

async function verifyAdminSession() {
  if (adminTokenSubmit) adminTokenSubmit.disabled = true;
  try {
    await hydrateFromApi();
    if (adminTokenMessage) {
      const mode = adminCapabilities.canMutate ? 'operator' : 'read-only viewer';
      adminTokenMessage.textContent = `Admin session verified. Live operations console is open in ${mode} mode.`;
      adminTokenMessage.classList.remove('error');
    }
    unlockAdmin();
  } catch {
    if (adminTokenMessage) {
      adminTokenMessage.textContent = 'Log in with an admin account to open the operations console.';
      adminTokenMessage.classList.add('error');
    }
    lockAdmin();
  } finally {
    if (adminTokenSubmit) adminTokenSubmit.disabled = false;
  }
}

adminTokenSubmit?.addEventListener('click', () => {
  verifyAdminSession();
});

adminTokenInput?.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') adminTokenSubmit?.click();
});

document.addEventListener('click', async (event) => {
  const target = event.target.closest('[data-action], [data-runbook], [data-ui-action]');
  if (!target) return;
  const uiAction = target.dataset.uiAction;
  if (uiAction === 'focus-section') {
    const sectionId = target.dataset.section;
    const section = sectionId ? document.querySelector(`#${escapeSelector(sectionId)}`) : null;
    if (section) {
      section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      addAction(`Moved to ${sectionId} for the selected issue.`);
    }
    return;
  }
  const action = target.dataset.action || target.dataset.runbook;
  const user = target.dataset.user;
  const session = target.dataset.session;
  const issue = target.dataset.issue;
  const owner = target.dataset.owner;
  const token = target.dataset.token;
  const tool = target.dataset.tool;
  const apiTarget = user || session || issue || owner || token || tool || 'system';

  if (action === 'open-user' && userSearchInput) {
    userSearchInput.value = owner;
    renderUsers();
    addAction(`Filtered owner: ${owner}`);
    return;
  }
  if (!adminCapabilities.canMutate) {
    addAction('This operator account is read-only.', 'error');
    return;
  }

  try {
    const payload = { action, target: apiTarget };
    if (action === 'set-plan') {
      const planInput = document.querySelector(`[data-plan-for="${escapeSelector(apiTarget)}"]`);
      payload.plan = planInput?.value || '';
    }
    const result = await postApi('/admin/action', payload);
    await hydrateFromApi();
    renderAll();
    const suffix = result.plan ? ` plan=${result.plan}` : '';
    addAction(`${action} completed for ${apiTarget}.${suffix} affected=${result.affected ?? 0}`);
  } catch (error) {
    addAction(`${action} failed for ${apiTarget}: ${error.message}`, 'error');
  }
});

createAdminTokenButton?.addEventListener('click', async () => {
  if (!adminCapabilities.canMutate) {
    addAction('This operator account is read-only.', 'error');
    return;
  }
  const name = (adminTokenNameInput?.value || '').trim();
  const role = adminTokenRoleSelect?.value || 'viewer';
  if (!name) {
    addAction('Token name is required.', 'error');
    return;
  }
  try {
    const result = await postApi('/admin/action', { action: 'create-admin-token', target: name, name, role });
    if (newAdminTokenBox) {
      newAdminTokenBox.classList.remove('hidden');
      newAdminTokenBox.innerHTML = `<strong>New ${result.role} token</strong><code>${result.token}</code><small>Copy it now. It will not be shown again.</small>`;
    }
    if (adminTokenNameInput) adminTokenNameInput.value = '';
    await hydrateFromApi();
    renderAll();
    addAction(`create-admin-token completed. role=${result.role}`);
  } catch (error) {
    addAction(`create-admin-token failed: ${error.message}`, 'error');
  }
});

adminLockButton?.addEventListener('click', lockAdmin);
refreshAdminData?.addEventListener('click', () => {
  hydrateFromApi()
    .then(() => {
      renderAll();
      addAction('Live operations data refreshed.');
    })
    .catch((error) => addAction(`Refresh failed: ${error.message}`, 'error'));
});
runTriageButton?.addEventListener('click', () => {
  if (riskSelect) riskSelect.value = 'critical';
  renderAll();
  addAction('Showing critical issues only.', 'warning');
});
expireStaleButton?.addEventListener('click', () => {
  addAction('Stale-session cleanup should be handled from active session rows.', 'warning');
});
clearLogFilterButton?.addEventListener('click', () => renderLogs());
rangeSelect?.addEventListener('change', renderAll);
planSelect?.addEventListener('change', () => {
  renderKpis();
  renderUsers();
});
riskSelect?.addEventListener('change', renderAll);
userSearchInput?.addEventListener('input', renderUsers);

verifyAdminSession();
