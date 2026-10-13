# -*- coding: utf-8 -*-
"""用户模块（二）：个人资料、修改昵称、修改密码（F-04）。"""
from flask import Blueprint, request, g
from werkzeug.security import generate_password_hash, check_password_hash

from db import query_one, execute
from utils import success, fail, fmt_dt
from auth import token_required

bp = Blueprint('user', __name__)


@bp.get('/api/user')
@token_required
def get_profile():
    u = g.user
    return success({
        'id': u['id'],
        'username': u['username'],
        'nickname': u['nickname'],
        'role': u['role'],
        'status': u['status'],
        'created_at': fmt_dt(u['created_at']),
        'last_login_at': fmt_dt(u['last_login_at']),
    })


@bp.put('/api/user')
@token_required
def update_nickname():
    body = request.get_json(silent=True) or {}
    nickname = (body.get('nickname') or '').strip()
    if not nickname:
        return fail('昵称不能为空', 400)
    if len(nickname) > 20:
        return fail('昵称长度不能超过 20 个字符', 400)

    execute('UPDATE `user` SET nickname = %s WHERE id = %s', (nickname, g.user['id']))
    g.user['nickname'] = nickname
    return success({'nickname': nickname}, '昵称修改成功')


@bp.put('/api/user/password')
@token_required
def change_password():
    body = request.get_json(silent=True) or {}
    old_password = body.get('old_password') or ''
    new_password = body.get('new_password') or ''
    confirm = body.get('confirm_password') or ''

    if not old_password or not new_password:
        return fail('原密码与新密码不能为空', 400)

    row = query_one('SELECT password_hash FROM `user` WHERE id = %s', (g.user['id'],))
    if not check_password_hash(row['password_hash'], old_password):
        return fail('原密码错误', 400)
    if not (6 <= len(new_password) <= 20):
        return fail('新密码长度需为 6~20 位', 400)
    if new_password != confirm:
        return fail('两次输入的新密码不一致', 400)
    if check_password_hash(row['password_hash'], new_password):
        return fail('新密码不能与原密码相同', 400)

    execute(
        'UPDATE `user` SET password_hash = %s WHERE id = %s',
        (generate_password_hash(new_password), g.user['id']),
    )
    return success({}, '密码修改成功')
