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
  { label: 'Blender', versionName: 'Blender', slug: 'blender', executablePath: 'C:\\Program Files\\Blender Foundation\\Blender\\blender.exe' }
];

const fallbackUser = {
  nickname: '데모 사용자',
  email: 'demo@mcpworld.local',
  plan: 'Pro Trial'
};

const registeredTools = new Set();
let currentSessionId = '';

async function postApi(path, payload) {
  const response = await fetch(`api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
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
    const raw = sessionStorage.getItem('mcpworld_demo_user');
    return raw ? JSON.parse(raw) : fallbackUser;
  } catch {
    return fallbackUser;
  }
}

function makeSessionId() {
  const randomPart = Math.random().toString(36).slice(2, 10);
  const timePart = Date.now().toString(36).slice(-6);
  return `${randomPart}${timePart}`;
}

function buildConnectorUrl(user, toolSlug, sessionId) {
  const userKey = encodeURIComponent((user.email || 'demo').split('@')[0].toLowerCase());
  return `${getAppBaseUrl()}/relay/u/${userKey}/mcp/${toolSlug}?session=${sessionId}`;
}

async function issueConnector(user, toolSlug) {
  try {
    const data = await postApi('/sessions/issue', { email: user.email, tool: toolSlug });
    return data.session.route;
  } catch {
    return buildConnectorUrl(user, toolSlug, currentSessionId);
  }
}

function buildPairUrl(user, tool, sessionId) {
  const params = new URLSearchParams({
    server: getAppBaseUrl(),
    user: user.email || fallbackUser.email,
    tool: tool.slug,
    token: sessionId,
    program_path: tool.executablePath
  });
  return `mcpworld://pair?${params.toString()}`;
}

function renderUser(user) {
  if (welcomeTitle) welcomeTitle.textContent = `${user.nickname}님, MCP 연결을 시작하세요.`;
  if (accountName) accountName.textContent = user.nickname;
  if (accountEmail) accountEmail.textContent = user.email;
  if (planName) planName.textContent = user.plan || 'Free Trial';
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

function renderConnectors(user, options = {}) {
  if (!connectorList) return;
  if (options.refreshSession || !currentSessionId) {
    currentSessionId = makeSessionId();
    registeredTools.clear();
  }
  connectorList.innerHTML = '';

  connectorTools.forEach((tool) => {
    const isRegistered = registeredTools.has(tool.slug);
    let connectorUrl = buildConnectorUrl(user, tool.slug, currentSessionId);
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
    registerButton.textContent = isRegistered ? '등록 완료' : '에이전트 등록';
    registerButton.addEventListener('click', () => {
      window.location.href = pairUrl;
      registeredTools.add(tool.slug);
      setAgentState();
      renderConnectors(user, { refreshSession: false });
    });

    const copyButton = document.createElement('button');
    copyButton.className = 'btn btn-secondary connector-copy';
    copyButton.type = 'button';
    copyButton.textContent = '주소 복사';
    copyButton.disabled = !isRegistered;
    copyButton.addEventListener('click', async () => {
      try {
        connectorUrl = await issueConnector(user, tool.slug);
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

const currentUser = getUser();
renderUser(currentUser);
setAgentState();
renderConnectors(currentUser, { refreshSession: true });

installMcpworldButton?.addEventListener('click', (event) => {
  installMcpworldButton.textContent = '다운로드 시작';
  setTimeout(() => {
    installMcpworldButton.textContent = '에이전트 설치';
  }, 1400);
});

autoBindButton?.addEventListener('click', () => {
  connectorTools.forEach((tool) => registeredTools.add(tool.slug));
  setAgentState();
  renderConnectors(currentUser, { refreshSession: false });
});

refreshConnectors?.addEventListener('click', () => {
  renderConnectors(currentUser, { refreshSession: true });
  setAgentState();
  refreshConnectors.textContent = '새 주소 발급 완료';
  setTimeout(() => {
    refreshConnectors.textContent = '주소 다시 발급';
  }, 1400);
});

signOutButton?.addEventListener('click', () => {
  sessionStorage.removeItem('mcpworld_demo_user');
  window.location.href = 'index.html';
});

document.querySelectorAll('.dashboard-action').forEach((button) => {
  button.addEventListener('click', () => {
    button.textContent = '운영 API 연결 예정';
    const title = button.closest('.card')?.querySelector('h3')?.textContent;
    if (title === '세션 전체 종료') {
      postApi('/admin/action', { action: 'terminate-user-sessions', target: currentUser.email }).catch(() => {});
    }
    setTimeout(() => {
      if (button.closest('.card')?.querySelector('h3')?.textContent === '세션 전체 종료') button.textContent = '세션 종료';
      if (button.closest('.card')?.querySelector('h3')?.textContent === '결제 포털') button.textContent = '결제 관리';
      if (button.closest('.card')?.querySelector('h3')?.textContent === '개인정보 요청') button.textContent = '요청 접수';
    }, 1400);
  });
});
