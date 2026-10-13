/* 个人中心：资料展示、修改昵称/密码(F-04)、历史对局与最高分(F-11) */
(function () {
  if (!requireAuth()) return;
  renderNavbar('profile');

  /* ---------- 加载个人资料与最高分 ---------- */
  async function loadProfile() {
    const res = await api('/api/user');
    const d = res.data;
    document.getElementById('pUsername').textContent = d.username;
    document.getElementById('pNickname').textContent = d.nickname || '未设置';
    document.getElementById('pRole').textContent = d.role === 'admin' ? '管理员' : '玩家';
    document.getElementById('pCreated').textContent = d.created_at;
    document.getElementById('pLastLogin').textContent = d.last_login_at || '暂无记录';
    document.getElementById('newNickname').placeholder = d.nickname || d.username;

    // 同步本地缓存的用户信息（导航栏昵称）
    const u = Auth.user || {};
    u.username = d.username; u.nickname = d.nickname; u.role = d.role;
    localStorage.setItem(USER_KEY, JSON.stringify(u));
    renderNavbar('profile');
  }

  async function loadHighScore() {
    const res = await api('/api/games/highscore');
    document.getElementById('highScore').textContent = res.data.highscore;
  }

  /* ---------- 修改昵称 ---------- */
  document.getElementById('nickForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const nickname = document.getElementById('newNickname').value.trim();
    if (!nickname) { toast('昵称不能为空', 'error'); return; }
    try {
      await api('/api/user', { method: 'PUT', body: { nickname } });
      toast('昵称修改成功', 'success');
      document.getElementById('newNickname').value = '';
      loadProfile();
    } catch (err) { toast(err.message, 'error'); }
  });

  /* ---------- 修改密码 ---------- */
  document.getElementById('pwdForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const old_password = document.getElementById('oldPwd').value;
    const new_password = document.getElementById('newPwd').value;
    const confirm_password = document.getElementById('confirmPwd').value;
    if (!old_password || !new_password) { toast('请填写完整密码信息', 'error'); return; }
    if (new_password !== confirm_password) { toast('两次输入的新密码不一致', 'error'); return; }
    try {
      await api('/api/user/password', {
        method: 'PUT',
        body: { old_password, new_password, confirm_password },
      });
      toast('密码修改成功，下次登录请使用新密码', 'success');
      e.target.reset();
    } catch (err) { toast(err.message, 'error'); }
  });

  /* ---------- 历史对局分页 ---------- */
  const PAGE_SIZE = 10;
  let page = 1;
  let totalPages = 1;

  async function loadGames() {
    const tbody = document.getElementById('gamesBody');
    const empty = document.getElementById('gamesEmpty');
    const res = await api(`/api/games?page=${page}&page_size=${PAGE_SIZE}`);
    const { total, list } = res.data;
    totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    if (!list.length) {
      tbody.innerHTML = '';
      empty.classList.remove('hidden');
    } else {
      empty.classList.add('hidden');
      tbody.innerHTML = list.map((g, i) => `
        <tr>
          <td>${(page - 1) * PAGE_SIZE + i + 1}</td>
          <td>${g.start_time}</td>
          <td>${g.end_time}</td>
          <td><b style="color:var(--yellow)">${g.score}</b></td>
          <td>${g.lines_cleared}</td>
          <td>Lv.${g.level}</td>
          <td>${formatDuration(g.duration)}</td>
        </tr>`).join('');
    }
    document.getElementById('pageInfo').textContent = `${page} / ${totalPages}（共 ${total} 条）`;
    document.getElementById('prevPage').disabled = page <= 1;
    document.getElementById('nextPage').disabled = page >= totalPages;
  }

  document.getElementById('prevPage').addEventListener('click', () => {
    if (page > 1) { page--; loadGames(); }
  });
  document.getElementById('nextPage').addEventListener('click', () => {
    if (page < totalPages) { page++; loadGames(); }
  });

  loadProfile().catch(err => toast(err.message, 'error'));
  loadHighScore().catch(() => {});
  loadGames().catch(err => toast(err.message, 'error'));
})();
