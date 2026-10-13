# -*- coding: utf-8 -*-
"""JWT 签发/校验与认证鉴权装饰器。"""
import functools
from datetime import datetime, timedelta, timezone

import jwt
from flask import request, g

from config import Config
from db import query_one
from utils import fail


def make_token(user):
    """登录成功后签发 JWT，有效期 2 小时。"""
    payload = {
        'sub': str(user['id']),  # PyJWT 2.10+ 规范要求 sub 为字符串
        'username': user['username'],
        'role': user['role'],
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def _decode_token(token):
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def _bearer_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()
    return None


def load_current_user(required=True):
    """解析请求中的 Token 并加载用户；成功时写入 g.user。"""
    token = _bearer_token()
    if not token:
        if required:
            return None, fail('未登录或登录已失效，请重新登录', 401)
        return None, None
    payload = _decode_token(token)
    if not payload:
        if required:
            return None, fail('登录已过期，请重新登录', 401)
        return None, None
    user = query_one(
        'SELECT id, username, nickname, role, status, created_at, last_login_at '
        'FROM `user` WHERE id = %s',
        (int(payload.get('sub')),),
    )
    if not user or user['status'] != 1:
        if required:
            return None, fail('账号不存在或已被禁用', 401)
        return None, None
    g.user = user
    return user, None


def token_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        _user, error = load_current_user(required=True)
        if error is not None:
            return error
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        _user, error = load_current_user(required=True)
        if error is not None:
            return error
        if g.user['role'] != 'admin':
            return fail('无权限访问，仅管理员可操作', 403)
        return view(*args, **kwargs)
    return wrapper
