const ADMIN_AUTH_KEY = 'mcpworld_admin_unlocked';

const adminGate = document.querySelector('#adminGate');
const adminContent = document.querySelector('#adminContent');
const adminTokenInput = document.querySelector('#adminTokenInput');
const adminTokenSubmit = document.querySelector('#adminTokenSubmit');
const adminTokenMessage = document.querySelector('#adminTokenMessage');
const adminLockButton = document.querySelector('#adminLockButton');
const rangeSelect = document.querySelector('#rangeSelect');
const planSelect = document.querySelector('#planSelect');
const refreshAdminData = document.querySelector('#refreshAdminData');
const exportEvents = document.querySelector('#exportEvents');
const programTableBody = document.querySelector('#programTable tbody');
const eventTableBody = document.querySelector('#eventTable tbody');
const planBars = document.querySelector('#planBars');

const kpiUsers = document.querySelector('#kpiUsers');
const kpiDevices = document.querySelector('#kpiDevices');
const kpiSessions = document.querySelector('#kpiSessions');
const kpiConnectors = document.querySelector('#kpiConnectors');
const kpiErrorRate = document.querySelector('#kpiErrorRate');
const kpiRelay = document.querySelector('#kpiRelay');

const programStats = [
  { program: 'Word', version: 'Microsoft Word / Microsoft 365', registered: 42, active: 8, connectors: 136, errors: 2 },
  { program: 'PowerPoint', version: 'Microsoft PowerPoint / Microsoft 365', registered: 51, active: 11, connectors: 188, errors: 3 },
  { program: 'Excel', version: 'Microsoft Excel / Microsoft 365', registered: 39, active: 7, connectors: 121, errors: 1 },
  { program: 'CAD / ZWCAD', version: 'ZWCAD 2025', registered: 24, active: 6, connectors: 78, errors: 4 },
  { program: 'HWP', version: 'Hancom Office HWP', registered: 27, active: 4, connectors: 84, errors: 2 },
  { program: 'Photoshop', version: 'Adobe Photoshop', registered: 13, active: 2, connectors: 34, errors: 1 },
  { program: 'Blender', version: 'Blender', registered: 9, active: 1, connectors: 22, errors: 0 }
];

const planStats = [
  { plan: 'Free', users: 118, note: '1 PC / 1개 프로그램 / 테스트 세션' },
  { plan: 'Starter', users: 64, note: 'Word + PowerPoint + Excel' },
  { plan: 'Pro', users: 43, note: 'Office + CAD/ZWCAD + HWP' },
  { plan: 'Studio', users: 17, note: 'Pro + Photoshop + Blender + 긴 세션' }
];

const eventRows = [
  { time: '14:58', user: 'demo@mcpworld.local', program: 'CAD / ZWCAD', event: 'pair', status: 'success' },
  { time: '14:55', user: 'user17@example.com', program: 'PowerPoint', event: 'connector issued', status: 'success' },
  { time: '14:51', user: 'user08@example.com', program: 'HWP', event: 'session start', status: 'success' },
  { time: '14:49', user: 'user24@example.com', program: 'CAD / ZWCAD', event: 'program path check', status: 'warning' },
  { time: '14:45', user: 'user03@example.com', program: 'Photoshop', event: 'relay retry', status: 'warning' },
  { time: '14:42', user: 'user11@example.com', program: 'Excel', event: 'disconnect', status: 'success' },
  { time: '14:40', user: 'user05@example.com', program: 'Word', event: 'auth failed', status: 'error' }
];

function getDemoAdminCode() {
  return ['mcpworld', 'admin', '2026'].join('-');
}

function numberWithComma(value) {
  return new Intl.NumberFormat('ko-KR').format(value);
}

function getMultiplier() {
  const range = rangeSelect?.value || '7d';
  if (range === 'today') return 0.38;
  if (range === '30d') return 2.6;
  return 1;
}

function applyPlanFilter(rows) {
  const plan = planSelect?.value || 'all';
  if (plan === 'all') return rows;
  const factorMap = { free: 0.52, starter: 0.76, pro: 0.62, studio: 0.33 };
  const factor = factorMap[plan] || 1;
  return rows.map((row) => ({
    ...row,
    registered: Math.max(1, Math.round(row.registered * factor)),
    active: Math.max(0, Math.round(row.active * factor)),
    connectors: Math.max(1, Math.round(row.connectors * factor)),
    errors: Math.max(0, Math.round(row.errors * factor))
  }));
}

function renderKpis(rows) {
  const multiplier = getMultiplier();
  const registered = rows.reduce((sum, row) => sum + row.registered, 0);
  const active = rows.reduce((sum, row) => sum + row.active, 0);
  const connectors = rows.reduce((sum, row) => sum + row.connectors, 0);
  const errors = rows.reduce((sum, row) => sum + row.errors, 0);
  const users = Math.round(242 * multiplier);
  const devices = Math.round(registered * multiplier);
  const sessions = Math.round(active * multiplier);
  const issued = Math.round(connectors * multiplier);
  const errorRate = issued > 0 ? ((errors / issued) * 100).toFixed(1) : '0.0';

  if (kpiUsers) kpiUsers.textContent = numberWithComma(users);
  if (kpiDevices) kpiDevices.textContent = numberWithComma(devices);
  if (kpiSessions) kpiSessions.textContent = numberWithComma(sessions);
  if (kpiConnectors) kpiConnectors.textContent = numberWithComma(issued);
  if (kpiErrorRate) kpiErrorRate.textContent = `${errorRate}%`;
  if (kpiRelay) kpiRelay.textContent = errors >= 6 ? '주의' : '정상';
}

function renderProgramTable(rows) {
  if (!programTableBody) return;
  const multiplier = getMultiplier();
  programTableBody.innerHTML = '';
  rows.forEach((row) => {
    const tr = document.createElement('tr');
    [row.program, row.version, row.registered, row.active, row.connectors, row.errors].forEach((value, index) => {
      const td = document.createElement('td');
      const scaled = typeof value === 'number' ? Math.round(value * multiplier) : value;
      td.textContent = typeof scaled === 'number' ? numberWithComma(scaled) : scaled;
      if (index === 5 && Number(scaled) > 0) td.className = 'status-warning';
      tr.appendChild(td);
    });
    programTableBody.appendChild(tr);
  });
}

function renderPlanBars() {
  if (!planBars) return;
  const total = planStats.reduce((sum, row) => sum + row.users, 0);
  planBars.innerHTML = '';
  planStats.forEach((row) => {
    const percent = Math.round((row.users / total) * 100);
    const item = document.createElement('article');
    item.className = 'plan-bar-card';
    item.innerHTML = `
      <div class="plan-bar-head">
        <strong>${row.plan}</strong>
        <span>${numberWithComma(row.users)}명 · ${percent}%</span>
      </div>
      <div class="plan-bar-track"><div class="plan-bar-fill" style="width:${percent}%"></div></div>
      <p>${row.note}</p>
    `;
    planBars.appendChild(item);
  });
}

function renderEvents() {
  if (!eventTableBody) return;
  eventTableBody.innerHTML = '';
  eventRows.forEach((row) => {
    const tr = document.createElement('tr');
    [row.time, row.user, row.program, row.event, row.status].forEach((value, index) => {
      const td = document.createElement('td');
      td.textContent = value;
      if (index === 4) td.className = `event-status ${value}`;
      tr.appendChild(td);
    });
    eventTableBody.appendChild(tr);
  });
}

function renderAll() {
  const filteredRows = applyPlanFilter(programStats);
  renderKpis(filteredRows);
  renderProgramTable(filteredRows);
  renderPlanBars();
  renderEvents();
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
  if (adminTokenMessage) {
    adminTokenMessage.textContent = '';
    adminTokenMessage.classList.remove('error');
  }
}

adminTokenSubmit?.addEventListener('click', () => {
  const typedCode = adminTokenInput?.value.trim() || '';
  if (typedCode === getDemoAdminCode()) {
    if (adminTokenMessage) {
      adminTokenMessage.textContent = '토큰 확인 완료. 관리자 대시보드를 엽니다.';
      adminTokenMessage.classList.remove('error');
    }
    unlockAdmin();
    return;
  }
  if (adminTokenMessage) {
    adminTokenMessage.textContent = '관리자 토큰이 올바르지 않습니다.';
    adminTokenMessage.classList.add('error');
  }
});

adminTokenInput?.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') adminTokenSubmit?.click();
});
adminLockButton?.addEventListener('click', lockAdmin);
refreshAdminData?.addEventListener('click', () => {
  renderAll();
  refreshAdminData.textContent = '새로고침 완료';
  setTimeout(() => {
    refreshAdminData.textContent = '통계 새로고침';
  }, 1200);
});
rangeSelect?.addEventListener('change', renderAll);
planSelect?.addEventListener('change', renderAll);
exportEvents?.addEventListener('click', () => {
  exportEvents.textContent = 'CSV 생성 데모 완료';
  setTimeout(() => {
    exportEvents.textContent = 'CSV 내보내기 데모';
  }, 1400);
});

if (sessionStorage.getItem(ADMIN_AUTH_KEY) === 'true') unlockAdmin();
else lockAdmin();
