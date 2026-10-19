# -*- coding: utf-8 -*-
"""全局配置：环境变量 > db_config.json > 默认值。

云端部署（Render）时全部通过环境变量注入，不依赖 db_config.json；
本地运行时可用 start.bat 生成 db_config.json 简化配置。
"""
import os
import json

_CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db_config.json')


def _load_local():
    """读取 start.bat 生成 db_config.json（方便本地非技术用户配置）。"""
    if os.path.exists(_CFG_PATH):
        try:
            with open(_CFG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


_local = _load_local()

# MySQL 连接信息（环境变量优先）
_MYSQL_HOST = os.getenv('MYSQL_HOST', _local.get('mysql_host', '127.0.0.1'))


class Config:
    # 数据库驱动：mysql（本地 MySQL / TiDB Cloud）或 sqlite（PythonAnywhere 等无数据库平台）
    DB_DRIVER = os.getenv('DB_DRIVER', _local.get('db_driver', 'mysql')).strip().lower()
    # SQLite 数据文件路径（仅 DB_DRIVER=sqlite 时生效）
    SQLITE_PATH = os.getenv(
        'SQLITE_PATH',
        _local.get('sqlite_path', os.path.join(os.path.dirname(_CFG_PATH), 'tetris.sqlite3')),
    )

    # MySQL 数据库连接配置
    MYSQL_HOST = _MYSQL_HOST
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', _local.get('mysql_port', 3306)))
    MYSQL_USER = os.getenv('MYSQL_USER', _local.get('mysql_user', 'root'))
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', _local.get('mysql_password', '123456'))
    MYSQL_DB = os.getenv('MYSQL_DB', _local.get('mysql_db', 'tetris_db'))
    MYSQL_CHARSET = 'utf8mb4'

    # 云端数据库（TiDB Cloud 等）强制要求 TLS/SSL。
    # 本机地址默认关闭，非本机地址默认开启，也可用 MYSQL_SSL 显式覆盖。
    MYSQL_SSL = _as_bool(
        os.getenv('MYSQL_SSL'),
        default=_MYSQL_HOST not in ('127.0.0.1', 'localhost', '::1'),
    )
    # 可选：自签/私有 CA 证书路径（TiDB 公共 CA 无需配置）
    MYSQL_SSL_CA = os.getenv('MYSQL_SSL_CA', _local.get('mysql_ssl_ca', ''))

    # JWT 配置
    JWT_SECRET = os.getenv('JWT_SECRET', 'tetris-flask-canvas-secret-key-2026-group6')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRE_HOURS = 2  # Token 有效期 2 小时

    # 初始管理员账号（仅首次初始化时写入，之后需在数据库中修改）
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', _local.get('admin_username', 'admin'))
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', _local.get('admin_password', 'admin123'))

    # 服务器监听地址：0.0.0.0 允许外部访问；云端由平台注入 PORT
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
