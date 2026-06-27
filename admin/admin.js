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
    issueList.innerHTML = '<p class="muted">No active operational issues.</p>';
    if (issueDetail) issueDetail.innerHTML = '<p class="muted">Live checks are clear.</p>';
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

function renderIssueDetail(issueId) {
  const issue = issues.find((item) => item.id === issueId) || getVisibleIssues()[0];
  if (!issueDetail || !issue) return;
  issueDetail.innerHTML = `
    <p class="eyebrow">Selected Issue</p>
    <h3>${issue.title}</h3>
    <dl class="ops-definition">
      <dt>Severity</dt><dd>${severityLabel(issue.severity)}</dd>
      <dt>Owner</dt><dd>${issue.owner}</dd>
      <dt>Impact</dt><dd>${issue.impact}</dd>
      <dt>Likely Cause</dt><dd>${issue.cause}</dd>
      <dt>Suggested Action</dt><dd>${issue.action}</dd>
    </dl>
    <div class="ops-actions">
      <button class="btn btn-primary" data-action="resolve-issue" data-issue="${issue.id}" type="button">Mark reviewed</button>
      <button class="btn btn-secondary" data-action="open-user" data-owner="${issue.owner}" type="button">Find owner</button>
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
  const target = event.target.closest('[data-action], [data-runbook]');
  if (!target) return;
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
