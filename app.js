const navToggle = document.querySelector('.nav-toggle');
const navLinks = document.querySelector('.nav-links');
const loginDialog = document.querySelector('#loginDialog');
const signupDialog = document.querySelector('#signupDialog');
const checkoutDialog = document.querySelector('#checkoutDialog');
const loginUser = document.querySelector('#loginUser');
const loginPass = document.querySelector('#loginPass');
const loginMessage = document.querySelector('#loginMessage');
const signupMessage = document.querySelector('#signupMessage');


function applyExternalLinks() {
  const links = window.MCPWORLD_LINKS || {};
  const mappings = [
    ['.github-repo-link', links.githubRepo],
    ['.github-release-link', links.githubReleases],
    ['.github-issues-link', links.githubIssues],
    ['.github-discussions-link', links.githubDiscussions]
  ];
  mappings.forEach(([selector, href]) => {
    if (!href) return;
    document.querySelectorAll(selector).forEach((anchor) => {
      anchor.href = href;
      anchor.target = '_blank';
      anchor.rel = 'noopener';
    });
  });
}

applyExternalLinks();

const demoAccount = {
  id: 'demo',
  email: 'demo@mcpworld.local',
  pass: 'demo1234',
  nickname: '데모 사용자',
  plan: 'Pro Trial'
};

async function postApi(path, payload) {
  const response = await fetch(`api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    const error = new Error(data.error || 'api_error');
    error.data = data;
    throw error;
  }
  return data;
}

async function getApi(path) {
  const response = await fetch(`api${path}`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    const error = new Error(data.error || 'api_error');
    error.data = data;
    throw error;
  }
  return data;
}

if (navToggle && navLinks) {
  navToggle.addEventListener('click', () => {
    const isOpen = navLinks.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
  });

  navLinks.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      navLinks.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

function openDialog(dialog) {
  if (!dialog) return;
  if (typeof dialog.showModal === 'function') dialog.showModal();
  else dialog.setAttribute('open', '');
}

function closeDialog(dialog) {
  if (!dialog) return;
  if (typeof dialog.close === 'function') dialog.close();
  else dialog.removeAttribute('open');
}

function goToDashboard(user) {
  sessionStorage.setItem('mcpworld_demo_user', JSON.stringify(user));
  window.location.href = 'dashboard.html';
}

document.querySelectorAll('.open-login').forEach((button) => {
  button.addEventListener('click', () => openDialog(loginDialog));
});

document.querySelectorAll('.open-signup').forEach((button) => {
  button.addEventListener('click', () => {
    closeDialog(loginDialog);
    openDialog(signupDialog);
  });
});

document.querySelectorAll('.open-checkout').forEach((button) => {
  button.addEventListener('click', async () => {
    try {
      const plan = button.closest('.price-card')?.querySelector('h3')?.textContent || 'Pro';
      const data = await postApi('/billing/checkout', { plan });
      if (data.checkoutUrl) window.location.href = data.checkoutUrl;
    } catch {
      openDialog(checkoutDialog);
    }
  });
});

document.querySelectorAll('.modal-close').forEach((button) => {
  button.addEventListener('click', () => closeDialog(button.closest('dialog')));
});

document.querySelectorAll('.modal').forEach((dialog) => {
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) closeDialog(dialog);
  });
});

document.querySelector('#loginSubmit')?.addEventListener('click', () => {
  const user = loginUser?.value.trim() || '';
  const pass = loginPass?.value || '';
  const isDemoUser = user === demoAccount.id || user === demoAccount.email;

  postApi('/auth/login', { identifier: user, password: pass })
    .then((data) => {
      loginMessage.textContent = '로그인되었습니다. 대시보드로 이동합니다.';
      loginMessage.classList.remove('error');
      goToDashboard({
        nickname: data.user.displayName,
        email: data.user.email,
        plan: data.user.plan
      });
    })
    .catch(() => {
      if (isDemoUser && pass === demoAccount.pass) {
        loginMessage.textContent = '로컬 데모 로그인으로 이동합니다.';
        loginMessage.classList.remove('error');
        goToDashboard(demoAccount);
        return;
      }
      loginMessage.textContent = '로그인에 실패했습니다. 데모 계정은 demo / demo1234 입니다.';
      loginMessage.classList.add('error');
    });
});

document.querySelector('#signupSubmit')?.addEventListener('click', () => {
  const email = document.querySelector('#signupEmail')?.value.trim() || '';
  const nickname = document.querySelector('#signupName')?.value.trim() || '';
  const pass = document.querySelector('#signupPass')?.value || '';
  const terms = document.querySelector('#agreeTerms')?.checked;
  const privacy = document.querySelector('#agreePrivacy')?.checked;
  const agentNotice = document.querySelector('#agreeAgentNotice')?.checked;

  if (!email || !nickname || pass.length < 8) {
    signupMessage.textContent = '이메일, 표시 이름, 8자 이상 비밀번호를 입력하세요.';
    signupMessage.classList.add('error');
    return;
  }

  if (!terms || !privacy || !agentNotice) {
    signupMessage.textContent = '필수 약관과 로컬 에이전트 고지를 확인해야 가입할 수 있습니다.';
    signupMessage.classList.add('error');
    return;
  }

  postApi('/auth/signup', { email, displayName: nickname, password: pass })
    .then((data) => {
      signupMessage.textContent = '가입되었습니다. 대시보드로 이동합니다.';
      signupMessage.classList.remove('error');
      goToDashboard({ nickname: data.user.displayName, email: data.user.email, plan: data.user.plan });
    })
    .catch((error) => {
      signupMessage.textContent = error.data?.error === 'email_exists' ? '이미 가입된 이메일입니다.' : '가입 API 연결에 실패했습니다.';
      signupMessage.classList.add('error');
    });
});

document.querySelector('#googleSignupButton')?.addEventListener('click', async () => {
  try {
    const data = await getApi('/auth/google/url');
    if (data.url) window.location.href = data.url;
  } catch (error) {
    signupMessage.textContent = 'Google OAuth 설정이 필요합니다. 서버에 GOOGLE_CLIENT_ID를 설정하세요.';
    signupMessage.classList.add('error');
  }
});
