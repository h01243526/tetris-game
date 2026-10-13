/* 登录 / 注册页脚本（F-01、F-02） */
(function () {
  // 已登录则直接进入游戏主页
  if (Auth.isLogin) {
    location.href = '/game.html';
    return;
  }

  const tabs = document.querySelectorAll('.auth-tab');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const loginMsg = document.getElementById('loginMsg');
  const regMsg = document.getElementById('regMsg');

  tabs.forEach(tab => tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const isLogin = tab.dataset.tab === 'login';
    loginForm.style.display = isLogin ? 'block' : 'none';
    registerForm.style.display = isLogin ? 'none' : 'block';
    loginMsg.textContent = regMsg.textContent = '';
    loginMsg.className = regMsg.className = 'auth-msg';
  }));

  function showMsg(el, text, type) {
    el.textContent = text;
    el.className = 'auth-msg ' + (type || 'error');
  }

  // ---------------- 登录 ----------------
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    if (!username || !password) { showMsg(loginMsg, '请输入用户名和密码'); return; }

    const btn = loginForm.querySelector('button');
    btn.disabled = true;
    try {
      const res = await api('/api/login', { method: 'POST', auth: false, body: { username, password } });
      Auth.set(res.data.token, res.data.user);
      showMsg(loginMsg, '登录成功，正在进入游戏…', 'success');
      const redirect = new URLSearchParams(location.search).get('redirect');
      setTimeout(() => { location.href = redirect && redirect.startsWith('/') ? redirect : '/game.html'; }, 400);
    } catch (err) {
      showMsg(loginMsg, err.message || '登录失败');
    } finally {
      btn.disabled = false;
    }
  });

  // ---------------- 注册 ----------------
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('regUsername').value.trim();
    const password = document.getElementById('regPassword').value;
    const confirmPassword = document.getElementById('regConfirm').value;

    if (!/^[A-Za-z0-9_一-龥]{3,20}$/.test(username)) {
      showMsg(regMsg, '用户名需为 3~20 位字母、数字、下划线或汉字'); return;
    }
    if (password.length < 6 || password.length > 20) {
      showMsg(regMsg, '密码长度需为 6~20 位'); return;
    }
    if (password !== confirmPassword) {
      showMsg(regMsg, '两次输入的密码不一致'); return;
    }

    const btn = registerForm.querySelector('button');
    btn.disabled = true;
    try {
      await api('/api/register', {
        method: 'POST', auth: false,
        body: { username, password, confirm_password: confirmPassword },
      });
      showMsg(regMsg, '注册成功，请使用新账号登录', 'success');
      document.getElementById('loginUsername').value = username;
      document.getElementById('loginPassword').value = '';
      setTimeout(() => tabs[0].click(), 800);
    } catch (err) {
      showMsg(regMsg, err.message || '注册失败');
    } finally {
      btn.disabled = false;
    }
  });
})();
