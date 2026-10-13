/* ======================================================================
   公共脚本：登录态(localStorage)、Fetch 封装、导航栏、Toast、通用工具
   ====================================================================== */

const TOKEN_KEY = 'tetris_token';
const USER_KEY = 'tetris_user';
const SOUND_KEY = 'tetris_sound';

/* ---------------- 登录态管理 ---------------- */
const Auth = {
  get token() { return localStorage.getItem(TOKEN_KEY); },
  get user() {
    try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch (e) { return null; }
  },
  set(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  get isLogin() { return !!this.token; },
  get isAdmin() { return this.user && this.user.role === 'admin'; },
};

/* ---------------- Fetch API 封装（统一 JSON / JWT / 401 处理） ---------------- */
async function api(url, options = {}) {
  const { method = 'GET', body = null, auth = true } = options;
  const headers = { 'Content-Type': 'application/json' };
  if (auth && Auth.token) headers['Authorization'] = 'Bearer ' + Auth.token;

  let res;
  try {
    res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : null });
  } catch (e) {
    throw { code: 0, message: '网络异常，请确认后端服务已启动' };
  }

  let data = null;
  try { data = await res.json(); } catch (e) { /* 非 JSON 响应 */ }

  if (res.status === 401) {
    Auth.clear();
    if (!location.pathname.endsWith('/') && !location.pathname.endsWith('index.html')) {
      location.href = '/?redirect=' + encodeURIComponent(location.pathname);
      throw { code: 401, message: '登录已过期，请重新登录' };
    }
  }
  if (!data) throw { code: res.status, message: `请求失败（HTTP ${res.status}）` };
  if (data.code !== 200) throw data;
  return data;
}

/* ---------------- Toast 轻提示 ---------------- */
function toast(message, type = 'info', duration = 2200) {
  let box = document.getElementById('toast-container');
  if (!box) {
    box = document.createElement('div');
    box.id = 'toast-container';
    document.body.appendChild(box);
  }
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = message;
  box.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity .25s';
    setTimeout(() => el.remove(), 260);
  }, duration);
}

/* ---------------- 导航栏渲染（RBAC：管理员可见“管理后台”） ---------------- */
function renderNavbar(active) {
  const box = document.getElementById('navbar');
  if (!box) return;
  const u = Auth.user;
  if (!u) { location.href = '/'; return; }
  const links = [
    { href: '/game.html', key: 'game', text: '开始游戏' },
    { href: '/leaderboard.html', key: 'leaderboard', text: '排行榜' },
    { href: '/profile.html', key: 'profile', text: '个人中心 / 我的成绩' },
  ];
  if (u.role === 'admin') links.push({ href: '/admin.html', key: 'admin', text: '管理后台' });

  box.innerHTML = `
    <a class="nav-brand" href="/game.html">TETRIS 俄罗斯方块</a>
    <nav class="nav-links">
      ${links.map(l => `<a class="nav-link ${active === l.key ? 'active' : ''}" href="${l.href}">${l.text}</a>`).join('')}
    </nav>
    <div class="nav-user">
      <span>${u.nickname || u.username}</span>
      <span class="nav-role ${u.role === 'admin' ? 'admin' : ''}">${u.role === 'admin' ? '管理员' : '玩家'}</span>
      <button id="logoutBtn" class="btn btn-ghost btn-sm">登出</button>
    </div>`;
  document.getElementById('logoutBtn').addEventListener('click', logout);
}

async function logout() {
  try { await api('/api/logout', { method: 'POST', auth: true }); } catch (e) { /* 无状态登出，忽略失效 */ }
  Auth.clear();
  toast('已安全登出', 'success');
  setTimeout(() => { location.href = '/'; }, 500);
}

/* ---------------- 页面访问控制 ---------------- */
function requireAuth() {
  if (!Auth.isLogin) {
    location.href = '/?redirect=' + encodeURIComponent(location.pathname);
    return false;
  }
  return true;
}

/* ---------------- 时间 / 数值工具 ---------------- */
function pad2(n) { return String(n).padStart(2, '0'); }

// 本地时间 -> 'YYYY-MM-DD HH:mm:ss'（与后端 DATETIME 对应）
function formatDateTime(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ` +
         `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

function formatDuration(sec) {
  sec = Math.max(0, parseInt(sec, 10) || 0);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return h > 0 ? `${h}:${pad2(m)}:${pad2(s)}` : `${pad2(m)}:${pad2(s)}`;
}

function escapeHtml(str) {
  return String(str == null ? '' : str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
