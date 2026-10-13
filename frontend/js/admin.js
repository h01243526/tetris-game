/* 管理后台：用户列表分页/搜索、禁用启用、删除（RBAC，仅 admin 角色） */
(function () {
  if (!requireAuth()) return;
  renderNavbar('admin');

  const PAGE_SIZE = 10;
  let page = 1;
  let totalPages = 1;
  let keyword = '';
  let accessChecked = false;

  const panel = document.getElementById('adminPanel');
  const denied = document.getElementById('denied');

  async function loadUsers() {
    const tbody = document.getElementById('usersBody');
    tbody.innerHTML = '<tr><td colspan="8" class="empty">加载中…</td></tr>';
    try {
      const qs = new URLSearchParams({ page, page_size: PAGE_SIZE, keyword });
      const res = await api(`/api/admin/users?${qs.toString()}`);
      if (!accessChecked) { accessChecked = true; denied.classList.add('hidden'); panel.classList.remove('hidden'); }

      const { total, list } = res.data;
      totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
      const me = Auth.user;
      const isMe = u => me && u.id === me.id;

      if (!list.length) {
        tbody.innerHTML = '';
        document.getElementById('usersEmpty').classList.remove('hidden');
      } else {
        document.getElementById('usersEmpty').classList.add('hidden');
        tbody.innerHTML = list.map(u => `
          <tr>
            <td>${u.id}</td>
            <td>${escapeHtml(u.username)}</td>
            <td>${escapeHtml(u.nickname || '-')}</td>
            <td><span class="tag ${u.role === 'admin' ? 'role-admin' : 'role-player'}">${u.role === 'admin' ? '管理员' : '玩家'}</span></td>
            <td><span class="tag ${u.status === 1 ? 'ok' : 'off'}">${u.status === 1 ? '正常' : '禁用'}</span></td>
            <td>${u.created_at}</td>
            <td>${u.last_login_at || '-'}</td>
            <td style="white-space:nowrap;">
              <button class="btn btn-ghost btn-sm js-toggle" data-id="${u.id}" data-status="${u.status}" ${isMe(u) ? 'disabled' : ''}>
                ${u.status === 1 ? '禁用' : '启用'}
              </button>
              <button class="btn btn-danger btn-sm js-delete" data-id="${u.id}" data-name="${escapeHtml(u.username)}"
                      ${isMe(u) || u.role === 'admin' ? 'disabled' : ''}>删除</button>
            </td>
          </tr>`).join('');
      }
      document.getElementById('pageInfo').textContent = `${page} / ${totalPages}（共 ${total} 人）`;
      document.getElementById('prevPage').disabled = page <= 1;
      document.getElementById('nextPage').disabled = page >= totalPages;
    } catch (err) {
      if (err.code === 403) {
        panel.classList.add('hidden');
        denied.classList.remove('hidden');
      } else {
        toast(err.message || '加载失败', 'error');
      }
    }
  }

  // 禁用 / 启用
  document.getElementById('usersBody').addEventListener('click', async (e) => {
    const btn = e.target.closest('.js-toggle');
    if (!btn) return;
    const id = btn.dataset.id;
    const nextStatus = parseInt(btn.dataset.status, 10) === 1 ? 0 : 1;
    if (!confirm(`确定要${nextStatus === 0 ? '禁用' : '启用'}该账号吗？`)) return;
    try {
      await api(`/api/admin/users/${id}/status`, { method: 'PUT', body: { status: nextStatus } });
      toast('账号状态已更新', 'success');
      loadUsers();
    } catch (err) { toast(err.message, 'error'); }
  });

  // 删除
  document.getElementById('usersBody').addEventListener('click', async (e) => {
    const btn = e.target.closest('.js-delete');
    if (!btn) return;
    const id = btn.dataset.id;
    const name = btn.dataset.name;
    if (!confirm(`确定删除账号「${name}」吗？\n该账号下全部对局记录将一并删除，且不可恢复！`)) return;
    try {
      await api(`/api/admin/users/${id}`, { method: 'DELETE' });
      toast('删除成功', 'success');
      loadUsers();
    } catch (err) { toast(err.message, 'error'); }
  });

  document.getElementById('searchBtn').addEventListener('click', () => {
    keyword = document.getElementById('keyword').value.trim();
    page = 1;
    loadUsers();
  });
  document.getElementById('resetBtn').addEventListener('click', () => {
    document.getElementById('keyword').value = '';
    keyword = ''; page = 1; loadUsers();
  });
  document.getElementById('prevPage').addEventListener('click', () => { if (page > 1) { page--; loadUsers(); } });
  document.getElementById('nextPage').addEventListener('click', () => { if (page < totalPages) { page++; loadUsers(); } });

  loadUsers();
})();
