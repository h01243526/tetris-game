/* 排行榜：总榜/日榜/周榜切换、分页、当前登录用户排名高亮（F-12；游客可浏览） */
(function () {
  // 排行榜游客可浏览：登录用户渲染完整导航，游客显示精简导航
  if (Auth.isLogin) {
    renderNavbar('leaderboard');
  } else {
    document.getElementById('navbar').innerHTML = `
      <a class="nav-brand" href="/">TETRIS 俄罗斯方块</a>
      <nav class="nav-links">
        <a class="nav-link active" href="/leaderboard.html">排行榜</a>
      </nav>
      <div class="nav-user">
        <span style="color:var(--text-dim);font-size:13px;">游客模式</span>
        <a class="btn btn-primary btn-sm" href="/">登录 / 注册</a>
      </div>`;
  }

  const PAGE_SIZE = 10;
  let type = 'total';
  let page = 1;
  let totalPages = 1;
  const me = Auth.user ? Auth.user.username : null;

  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(t => t.addEventListener('click', () => {
    tabs.forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    type = t.dataset.type;
    page = 1;
    loadRank();
  }));

  async function loadRank() {
    const tbody = document.getElementById('rankBody');
    const empty = document.getElementById('rankEmpty');
    const myBox = document.getElementById('myRankBox');
    tbody.innerHTML = '<tr><td colspan="5" class="empty">加载中…</td></tr>';

    let res;
    try {
      res = await api(`/api/leaderboard?type=${type}&page=${page}&page_size=${PAGE_SIZE}`, { auth: Auth.isLogin });
    } catch (err) {
      tbody.innerHTML = '';
      empty.classList.remove('hidden');
      empty.textContent = err.message || '加载失败';
      return;
    }

    const { total, list, my_rank } = res.data;
    totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    if (me && my_rank) {
      myBox.innerHTML = `<span class="rank-mybadge">我在「${typeName(type)}」当前排名：第 <b>${my_rank}</b> 名</span>`;
    } else if (me) {
      myBox.innerHTML = `<span class="rank-mybadge">你在「${typeName(type)}」中暂无排名，快去对局吧</span>`;
    } else {
      myBox.innerHTML = '';
    }

    if (!list.length) {
      tbody.innerHTML = '';
      empty.textContent = '该榜单暂无对局记录';
      empty.classList.remove('hidden');
    } else {
      empty.classList.add('hidden');
      tbody.innerHTML = list.map(r => `
        <tr class="${r.username === me ? 'me' : ''}">
          <td><span class="rank-no ${r.rank <= 3 ? 'r' + r.rank : ''}">${r.rank}</span></td>
          <td>${r.username === me ? escapeHtml(r.username) + ' （我）' : escapeHtml(r.username)}</td>
          <td><b style="color:var(--yellow)">${r.score}</b></td>
          <td>${r.lines_cleared}</td>
          <td>${r.played_at}</td>
        </tr>`).join('');
    }
    document.getElementById('pageInfo').textContent = `${page} / ${totalPages}（共 ${total} 条记录）`;
    document.getElementById('prevPage').disabled = page <= 1;
    document.getElementById('nextPage').disabled = page >= totalPages;
  }

  function typeName(t) {
    return { total: '总榜', day: '日榜', week: '周榜' }[t];
  }

  document.getElementById('prevPage').addEventListener('click', () => {
    if (page > 1) { page--; loadRank(); }
  });
  document.getElementById('nextPage').addEventListener('click', () => {
    if (page < totalPages) { page++; loadRank(); }
  });

  loadRank();
})();
