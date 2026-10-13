# -*- coding: utf-8 -*-
"""用户模块（一）：注册 / 登录 / 登出（F-01 ~ F-03）。"""
import re
from datetime import datetime

from flask import Blueprint, request
from werkzeug.security import generate_password_hash, check_password_hash

from db import query_one, execute
from utils import success, fail
from auth import make_token

bp = Blueprint('auth', __name__)

USERNAME_RE = re.compile(r'^[A-Za-z0-9_一-龥]{3,20}$')


@bp.post('/api/register')
def register():
    body = request.get_json(silent=True) or {}
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    confirm = body.get('confirm_password') or ''

    # 表单参数校验
    if not username or not password:
        return fail('用户名和密码不能为空', 400)
    if not USERNAME_RE.match(username):
        return fail('用户名需为 3~20 位字母、数字、下划线或汉字', 400)
    if not (6 <= len(password) <= 20):
        return fail('密码长度需为 6~20 位', 400)
    if password != confirm:
        return fail('两次输入的密码不一致', 400)

    # 用户名唯一性校验（参数化查询防 SQL 注入）
    exists = query_one('SELECT id FROM `user` WHERE username = %s', (username,))
    if exists:
        return fail('用户名已被占用，请更换用户名', 400)

    user_id = execute(
        'INSERT INTO `user` (username, password_hash, nickname, role, status) '
        'VALUES (%s, %s, %s, %s, 1)',
        (username, generate_password_hash(password), username, 'player'),
    )
    return success({'user_id': user_id}, '注册成功')


@bp.post('/api/login')
def login():
    body = request.get_json(silent=True) or {}
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    client_ip = request.remote_addr or 'unknown'

    if not username or not password:
        return fail('用户名和密码不能为空', 400)

    user = query_one('SELECT * FROM `user` WHERE username = %s', (username,))

    # 账号不存在 / 密码错误：写失败登录日志
    if not user or not check_password_hash(user['password_hash'], password):
        execute(
            'INSERT INTO login_log (user_id, login_time, login_ip, login_status, fail_reason) '
            'VALUES (%s, %s, %s, 0, %s)',
            (user['id'] if user else None, datetime.now(), client_ip,
             '用户名不存在' if not user else '密码错误'),
        )
        return fail('用户名或密码错误', 401)

    if user['status'] != 1:
        execute(
            'INSERT INTO login_log (user_id, login_time, login_ip, login_status, fail_reason) '
            'VALUES (%s, %s, %s, 0, %s)',
            (user['id'], datetime.now(), client_ip, '账号已被禁用'),
        )
        return fail('账号已被禁用，请联系管理员', 403)

    # 登录成功：更新最后登录时间并写登录日志
    execute('UPDATE `user` SET last_login_at = %s WHERE id = %s', (datetime.now(), user['id']))
    execute(
        'INSERT INTO login_log (user_id, login_time, login_ip, login_status) '
        'VALUES (%s, %s, %s, 1)',
        (user['id'], datetime.now(), client_ip),
    )

    token = make_token(user)
    return success({
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'nickname': user['nickname'],
            'role': user['role'],
        },
    }, '登录成功')


@bp.post('/api/logout')
def logout():
    # JWT 为无状态认证，后端无需维护会话；前端清除本地 Token 即可
    return success({}, '已登出')
