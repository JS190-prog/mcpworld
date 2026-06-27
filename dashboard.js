const connectorList = document.querySelector('#connectorList');
const refreshConnectors = document.querySelector('#refreshConnectors');
const signOutButton = document.querySelector('#signOutButton');
const welcomeTitle = document.querySelector('#welcomeTitle');
const accountName = document.querySelector('#accountName');
const accountEmail = document.querySelector('#accountEmail');
const planName = document.querySelector('#planName');
const autoBindButton = document.querySelector('#autoBindButton');
const installMcpworldButton = document.querySelector('#installMcpworldButton');
const agentStatusTitle = document.querySelector('#agentStatusTitle');
const agentStatusText = document.querySelector('#agentStatusText');

function getAgentDownloadUrl() {
  return window.MCPWORLD_LINKS?.githubReleases || 'release/latest.json';
}

function configureAgentDownloadLink() {
  if (!installMcpworldButton) return;
  installMcpworldButton.href = getAgentDownloadUrl();
  installMcpworldButton.target = '_blank';
  installMcpworldButton.rel = 'noopener';
}

configureAgentDownloadLink();


const connectorTools = [
  { label: 'Word', versionName: 'Microsoft Word / Microsoft 365', slug: 'word', executablePath: 'C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE' },
  { label: 'PowerPoint', versionName: 'Microsoft PowerPoint / Microsoft 365', slug: 'powerpoint', executablePath: 'C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE' },
  { label: 'Excel', versionName: 'Microsoft Excel / Microsoft 365', slug: 'excel', executablePath: 'C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE' },
  { label: 'CAD / ZWCAD', versionName: 'ZWCAD 2025', slug: 'cad', executablePath: 'C:\\Program Files\\ZWSOFT\\ZWCAD 2025\\ZWCAD.exe' },
  { label: 'HWP', versionName: 'Hancom Office HWP', slug: 'hwp', executablePath: 'C:\\Program Files (x86)\\Hnc\\Office\\Hwp.exe' },
  { label: 'Photoshop', versionName: 'Adobe Photoshop', slug: 'photoshop', executablePath: 'C:\\Program Files\\Adobe\\Adobe Photoshop\\Photoshop.exe' },
  { label: 'Blender', versionName: 'Blender', slug: 'blender', executablePath: 'C:\\Program Files\\Blender Foundation\\Blender\\blender.exe' },
  { label: 'Local Code', versionName: 'Local Code MCP · 파일 편집 (데스크톱 앱 불필요)', slug: 'localcode', executablePath: '로컬 코드 MCP 서버 (허용 폴더 내 파일 편집)' },
  { label: 'OpenCrab Ingest', versionName: 'OpenCrab MCP · 온톨로지/문서 인제스트', slug: 'opencrab', executablePath: 'OpenCrab MCP 서버 (예: 127.0.0.1:18006/mcp)' }
];

const fallbackUser = {
  nickname: '사용자',
  email: '',
  plan: 'Free Trial'
};

const registeredTools = new Set();
let currentSessionId = '';
const connectorRoutes = new Map();

async function postApi(path, payload) {
  const response = await fetch(`api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) throw new Error(data.error || 'api_error');
  return data;
}

async function getApi(path) {
  const response = await fetch(`api${path}`, { credentials: 'same-origin' });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) throw new Error(data.error || 'api_error');
  return data;
}

function getAppBaseUrl() {
  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const appRoot = pathParts[0] === 'mcpworld' ? '/mcpworld' : '';
  return `${window.location.origin}${appRoot}`;
}

function getUser() {
  try {
    const raw = sessionStorage.getItem('mcpworld_user');
    return raw ? JSON.parse(raw) : fallbackUser;
  } catch {
    return fallbackUser;
  }
}

async function loadAuthenticatedUser() {
  try {
    const data = await getApi('/auth/me');
    const user = {
      nickname: data.user.displayName,
      email: data.user.email,
      plan: data.user.plan
    };
    sessionStorage.setItem('mcpworld_user', JSON.stringify(user));
    return user;
  } catch {
    sessionStorage.removeItem('mcpworld_user');
    return fallbackUser;
  }
}

function makeSessionId() {
  const randomPart = Math.random().toString(36).slice(2, 10);
  const timePart = Date.now().toString(36).slice(-6);
  return `${randomPart}${timePart}`;
}

function getMcpProxyBase() {
  return (window.MCPWORLD_LINKS?.mcpProxyBase || '').replace(/\/$/, '');
}

function buildConnectorUrl(user, toolSlug, sessionId) {
  const proxyBase = getMcpProxyBase();
  if (proxyBase) return `${proxyBase}/${encodeURIComponent(sessionId)}/mcp`;
  return `${getAppBaseUrl()}/mcp?key=${encodeURIComponent(sessionId)}`;
}

async function loadConnectorLinks(user, options = {}) {
  if (!user.email) return false;
  const endpoint = options.regenerate ? '/sessions/regenerate' : '/sessions/links';
  try {
    const data = await postApi(endpoint, { email: user.email });
    connectorRoutes.clear();
    data.sessions.forEach((session) => {
      connectorRoutes.set(session.tool, session.route);
    });
    currentSessionId = data.sessions[0]?.id || currentSessionId || makeSessionId();
    if (options.regenerate) registeredTools.clear();
    return true;
  } catch {
    if (!currentSessionId) currentSessionId = makeSessionId();
    return false;
  }
}

function buildPairUrl(user, tool, sessionId) {
  const params = new URLSearchParams({
    server: getAppBaseUrl(),
    user: user.email || '',
    tool: tool.slug,
    token: sessionId,
    program_path: tool.executablePath
  });
  return `mcpworld://pair?${params.toString()}`;
}

function renderUser(user) {
  if (welcomeTitle) welcomeTitle.textContent = `${user.nickname}님, MCP 연결을 시작하세요.`;
  if (accountName) accountName.textContent = user.nickname;
  if (accountEmail) accountEmail.textContent = user.email || '로그인이 필요합니다.';
  if (planName) planName.textContent = user.plan || 'Free Trial';
}

async function applyAdminAccess(user) {
  if (!user.email) {
    document.querySelectorAll('[data-admin-link]').forEach((link) => link.remove());
    return;
  }
  let isAdmin = false;
  try {
    const response = await fetch('api/auth/me', { credentials: 'same-origin' });
    const data = await response.json().catch(() => ({}));
    isAdmin = response.ok && data.ok === true && data.isAdmin === true;
  } catch {
    isAdmin = false;
  }
  document.querySelectorAll('[data-admin-link]').forEach((link) => {
    if (isAdmin) link.hidden = false;
    else link.remove();
  });
}

function setAgentState() {
  const count = registeredTools.size;
  const total = connectorTools.length;
  if (agentStatusTitle) agentStatusTitle.textContent = count === total ? '모든 프로그램 등록 완료' : `등록된 프로그램 ${count}/${total}`;
  if (agentStatusText) {
    agentStatusText.textContent = count === total
      ? '모든 프로그램이 로컬 에이전트에 등록되어 ChatGPT 커넥터 주소를 복사할 수 있습니다.'
      : '필요한 프로그램을 등록하면 해당 MCP 주소 복사 버튼이 활성화됩니다.';
  }
  if (autoBindButton) autoBindButton.textContent = count === total ? '전체 다시 등록' : '전체 등록';
}

function renderConnectors(user) {
  if (!connectorList) return;
  if (!user.email) {
    connectorList.innerHTML = '';
    const row = document.createElement('div');
    row.className = 'connector-row is-waiting';
    const title = document.createElement('div');
    title.className = 'connector-title';
    const titleName = document.createElement('strong');
    titleName.textContent = '로그인이 필요합니다';
    const description = document.createElement('small');
    description.textContent = '계정으로 로그인하면 프로그램별 MCP 주소를 발급할 수 있습니다.';
    title.append(titleName, description);
    row.append(title);
    connectorList.appendChild(row);
    return;
  }
  if (!currentSessionId) currentSessionId = makeSessionId();
  connectorList.innerHTML = '';

  connectorTools.forEach((tool) => {
    const isRegistered = registeredTools.has(tool.slug);
    const connectorUrl = connectorRoutes.get(tool.slug) || buildConnectorUrl(user, tool.slug, currentSessionId);
    const pairUrl = buildPairUrl(user, tool, currentSessionId);
    const row = document.createElement('div');
    row.className = isRegistered ? 'connector-row is-bound' : 'connector-row is-waiting';

    const title = document.createElement('div');
    title.className = 'connector-title';
    const titleName = document.createElement('strong');
    titleName.textContent = tool.label;
    const versionName = document.createElement('small');
    versionName.textContent = tool.versionName;
    title.append(titleName, versionName);

    const routeWrap = document.createElement('div');
    routeWrap.className = 'connector-route';
    const connectorCode = document.createElement('code');
    connectorCode.textContent = connectorUrl;
    const programPath = document.createElement('small');
    programPath.textContent = isRegistered ? `등록됨: ${tool.executablePath}` : `대기 중: ${tool.executablePath}`;
    routeWrap.append(connectorCode, programPath);

    const actions = document.createElement('div');
    actions.className = 'connector-actions';

    const registerButton = document.createElement('button');
    registerButton.className = isRegistered ? 'btn btn-secondary connector-register' : 'btn btn-primary connector-register';
    registerButton.type = 'button';
    registerButton.textContent = isRegistered ? '연동 완료' : '연동 링크 열기';
    registerButton.addEventListener('click', () => {
      window.location.href = pairUrl;
      registeredTools.add(tool.slug);
      setAgentState();
      renderConnectors(user);
    });

    const copyButton = document.createElement('button');
    copyButton.className = 'btn btn-secondary connector-copy';
    copyButton.type = 'button';
    copyButton.textContent = '주소 복사';
    copyButton.disabled = !isRegistered;
    copyButton.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(connectorUrl);
        copyButton.textContent = '복사 완료';
      } catch {
        copyButton.textContent = '직접 선택 필요';
      }
      setTimeout(() => {
        copyButton.textContent = '주소 복사';
      }, 1400);
    });

    actions.append(registerButton, copyButton);
    row.append(title, routeWrap, actions);
    connectorList.appendChild(row);
  });
}

let currentUser = getUser();

async function initDashboard() {
  currentUser = await loadAuthenticatedUser();
  renderUser(currentUser);
  applyAdminAccess(currentUser);
  setAgentState();
  await loadConnectorLinks(currentUser);
  renderConnectors(currentUser);
}

initDashboard();

installMcpworldButton?.addEventListener('click', (event) => {
  installMcpworldButton.textContent = '다운로드 시작';
  setTimeout(() => {
    installMcpworldButton.textContent = '에이전트 다운로드';
  }, 1400);
});

autoBindButton?.addEventListener('click', () => {
  connectorTools.forEach((tool) => registeredTools.add(tool.slug));
  setAgentState();
  renderConnectors(currentUser);
});

refreshConnectors?.addEventListener('click', async () => {
  refreshConnectors.disabled = true;
  refreshConnectors.textContent = '재생성 중';
  await loadConnectorLinks(currentUser, { regenerate: true });
  renderConnectors(currentUser);
  setAgentState();
  refreshConnectors.textContent = '기존 토큰 만료 완료';
  setTimeout(() => {
    refreshConnectors.disabled = false;
    refreshConnectors.textContent = '토큰 다시 생성';
  }, 1400);
});

signOutButton?.addEventListener('click', async () => {
  try {
    await postApi('/auth/logout', {});
  } catch {
    // Local sign-out still clears the dashboard session marker.
  }
  sessionStorage.removeItem('mcpworld_user');
  window.location.href = 'index.html';
});

document.querySelectorAll('.dashboard-action').forEach((button) => {
  button.addEventListener('click', () => {
    button.textContent = '운영 API 연결 예정';
    const title = button.closest('.card')?.querySelector('h3')?.textContent;
    setTimeout(() => {
      if (button.closest('.card')?.querySelector('h3')?.textContent === '세션 전체 종료') button.textContent = '세션 종료';
      if (button.closest('.card')?.querySelector('h3')?.textContent === '결제 포털') button.textContent = '결제 관리';
      if (button.closest('.card')?.querySelector('h3')?.textContent === '개인정보 요청') button.textContent = '요청 접수';
    }, 1400);
  });
});
