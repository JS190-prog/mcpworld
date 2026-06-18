const navToggle = document.querySelector('.nav-toggle');
const navLinks = document.querySelector('.nav-links');
const loginDialog = document.querySelector('#loginDialog');
const signupDialog = document.querySelector('#signupDialog');
const checkoutDialog = document.querySelector('#checkoutDialog');
const loginUser = document.querySelector('#loginUser');
const loginPass = document.querySelector('#loginPass');
const loginMessage = document.querySelector('#loginMessage');
const signupMessage = document.querySelector('#signupMessage');

const demoAccount = {
  id: 'demo',
  email: 'demo@mcpworld.local',
  pass: 'demo1234',
  nickname: '데모 사용자',
  plan: 'Pro Trial'
};

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
  button.addEventListener('click', () => openDialog(checkoutDialog));
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

  if (isDemoUser && pass === demoAccount.pass) {
    loginMessage.textContent = '로그인되었습니다. 대시보드로 이동합니다.';
    loginMessage.classList.remove('error');
    goToDashboard(demoAccount);
    return;
  }

  loginMessage.textContent = '데모 계정은 아이디 demo, 비밀번호 demo1234 입니다.';
  loginMessage.classList.add('error');
});

document.querySelector('#signupSubmit')?.addEventListener('click', () => {
  const email = document.querySelector('#signupEmail')?.value.trim() || '';
  const nickname = document.querySelector('#signupName')?.value.trim() || '';
  const pass = document.querySelector('#signupPass')?.value || '';
  const terms = document.querySelector('#agreeTerms')?.checked;
  const privacy = document.querySelector('#agreePrivacy')?.checked;

  if (!email || !nickname || pass.length < 8) {
    signupMessage.textContent = '이메일, 표시 이름, 8자 이상 비밀번호를 입력하세요.';
    signupMessage.classList.add('error');
    return;
  }

  if (!terms || !privacy) {
    signupMessage.textContent = '필수 약관에 동의해야 가입할 수 있습니다.';
    signupMessage.classList.add('error');
    return;
  }

  signupMessage.textContent = '가입되었습니다. 대시보드로 이동합니다.';
  signupMessage.classList.remove('error');
  goToDashboard({ nickname, email, plan: 'Free Trial' });
});
