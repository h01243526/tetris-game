# -*- coding: utf-8 -*-
"""管理模块：用户账号管理（查询 / 禁用启用 / 删除）与操作日志（RBAC，仅管理员）。"""
from flask import Blueprint, request, g

from db import get_db, query_one, query_all
from utils import success, fail, fmt_dt, parse_pagination, to_int
from auth import admin_required

bp = Blueprint('admin', __name__)


def _user_dict(row):
    return {
        'id': row['id'],
        'username': row['username'],
        'nickname': row['nickname'],
        'role': row['role'],
        'status': row['status'],
        'created_at': fmt_dt(row['created_at']),
        'last_login_at': fmt_dt(row['last_login_at']),
    }


def _write_log(cur, action, target, detail):
    cur.execute(
        'INSERT INTO operation_log (admin_id, action, target, detail) VALUES (%s, %s, %s, %s)',
        (g.user['id'], action, target, detail),
    )


@bp.get('/api/admin/users')
@admin_required
def list_users():
    page, page_size = parse_pagination(request.args, default_size=20)
    keyword = (request.args.get('keyword') or '').strip()
    offset = (page - 1) * page_size

    where_sql = ''
    args = []
    if keyword:
        where_sql = 'WHERE username LIKE %s OR nickname LIKE %s'
        args = [f'%{keyword}%', f'%{keyword}%']

    total_row = query_one(f'SELECT COUNT(*) AS cnt FROM `user` {where_sql}', args)
    rows = query_all(
        f'SELECT id, username, nickname, role, status, created_at, last_login_at '
        f'FROM `user` {where_sql} ORDER BY id ASC LIMIT %s OFFSET %s',
        args + [page_size, offset],
    )
    return success({
        'total': total_row['cnt'],
        'page': page,
        'page_size': page_size,
        'list': [_user_dict(r) for r in rows],
    })


@bp.put('/api/admin/users/<int:user_id>/status')
@admin_required
def update_user_status(user_id):
    """禁用 / 启用账号。"""
    body = request.get_json(silent=True) or {}
    status, err = to_int(body.get('status'), 'status', minimum=0, maximum=1)
    if err:
        return fail(err, 400)

    target = query_one('SELECT id, username, role FROM `user` WHERE id = %s', (user_id,))
    if not target:
        return fail('用户不存在', 404)
    if target['id'] == g.user['id']:
        return fail('不能禁用当前登录的管理员账号', 400)

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute('UPDATE `user` SET status = %s WHERE id = %s', (status, user_id))
        _write_log(cur, 'update_status', f'user:{user_id}',
                   f'{"启用" if status == 1 else "禁用"}账号 {target["username"]}')
    return success({}, '账号状态更新成功')


@bp.delete('/api/admin/users/<int:user_id>')
@admin_required
def delete_user(user_id):
    """删除异常账号，对局记录随外键级联删除。"""
    target = query_one('SELECT id, username, role FROM `user` WHERE id = %s', (user_id,))
    if not target:
        return fail('用户不存在', 404)
    if target['id'] == g.user['id']:
        return fail('不能删除当前登录的管理员账号', 400)

    conn = get_db()
    conn.begin()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM `user` WHERE id = %s', (user_id,))
            _write_log(cur, 'delete_user', f'user:{user_id}',
                       f'删除异常账号 {target["username"]}')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return success({}, '删除成功')
