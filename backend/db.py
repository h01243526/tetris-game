# -*- coding: utf-8 -*-
"""数据访问层：PyMySQL 连接管理、数据库初始化、常用查询封装。"""
import os
import ssl

import pymysql
from pymysql.cursors import DictCursor
from flask import g, current_app
from werkzeug.security import generate_password_hash

from config import Config


# ----------------------------------------------------------------------
# 连接参数（本地 MySQL 无需 SSL；TiDB Cloud 等云数据库强制 TLS）
# ----------------------------------------------------------------------
def _ssl_context():
    """按需构造 SSLContext；返回 None 表示不启用 TLS。"""
    if not Config.MYSQL_SSL:
        return None
    ctx = ssl.create_default_context()
    if Config.MYSQL_SSL_CA:
        # 配置了 CA 证书：做完整校验
        ctx.load_verify_locations(cafile=Config.MYSQL_SSL_CA)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    else:
        # 云数据库公共 CA：加密传输但不校验证书链，避免证书路径依赖
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _conn_kwargs(with_db=True):
    kwargs = dict(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        charset=Config.MYSQL_CHARSET,
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=10,
    )
    if with_db:
        kwargs['database'] = Config.MYSQL_DB
    ctx = _ssl_context()
    if ctx is not None:
        kwargs['ssl'] = ctx
    return kwargs


# ----------------------------------------------------------------------
# 请求级连接（每个请求一条连接，请求结束自动关闭）
# ----------------------------------------------------------------------
def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(**_conn_kwargs(with_db=True))
    return g.db


def close_db(_exc=None):
    conn = g.pop('db', None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def query_one(sql, args=None):
    with get_db().cursor() as cur:
        cur.execute(sql, args or ())
        return cur.fetchone()


def query_all(sql, args=None):
    with get_db().cursor() as cur:
        cur.execute(sql, args or ())
        return cur.fetchall()


def execute(sql, args=None):
    """执行单条写操作，返回 lastrowid。"""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, args or ())
        return cur.lastrowid


# ----------------------------------------------------------------------
# 数据库初始化：建库 -> 执行 schema.sql -> 预置管理员与难度配置
# 说明：云端数据库（如 TiDB Cloud）可能不允许自建库或存在少量语法差异，
#       因此这里对每个语句做容错处理，尽可能完成初始化而不阻断启动。
# ----------------------------------------------------------------------
def _connect_server():
    return pymysql.connect(**_conn_kwargs(with_db=False))


def _connect_db():
    return pymysql.connect(**_conn_kwargs(with_db=True))


def _split_sql(script):
    """按分号切分脚本（本项目 schema 不含存储过程/触发器，简单切分即可）。"""
    statements = []
    buf = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith('--'):
            continue
        buf.append(line)
        if stripped.endswith(';'):
            stmt = '\n'.join(buf).strip().rstrip(';').strip()
            if stmt:
                statements.append(stmt)
            buf = []
    tail = '\n'.join(buf).strip().rstrip(';').strip()
    if tail:
        statements.append(tail)
    return statements


def _seed(conn):
    """预置管理员账号与 1~15 级难度配置（幂等）。"""
    with conn.cursor() as cur:
        cur.execute('SELECT id FROM `user` WHERE username = %s', (Config.ADMIN_USERNAME,))
        if cur.fetchone() is None:
            cur.execute(
                'INSERT INTO `user` (username, password_hash, nickname, role, status) '
                'VALUES (%s, %s, %s, %s, 1)',
                (Config.ADMIN_USERNAME,
                 generate_password_hash(Config.ADMIN_PASSWORD),
                 '系统管理员', 'admin'),
            )
            print(f'[init] 已创建管理员账号：{Config.ADMIN_USERNAME} / {Config.ADMIN_PASSWORD}')

        # 等级 1~3 简单，4~7 普通，8~12 困难，13~15 专家
        # 下落间隔：800ms 起，每升一级减少 55ms，最低 80ms；每 10 行升一级
        def level_name(level):
            if level <= 3:
                return '简单'
            if level <= 7:
                return '普通'
            if level <= 12:
                return '困难'
            return '专家'

        for level in range(1, 16):
            interval = max(800 - (level - 1) * 55, 80)
            cur.execute('SELECT id FROM difficulty_level WHERE level = %s', (level,))
            if cur.fetchone() is None:
                cur.execute(
                    'INSERT INTO difficulty_level (level, level_name, drop_interval_ms, '
                    'upgrade_lines, score_multiplier) VALUES (%s, %s, %s, 10, 1.00)',
                    (level, level_name(level), interval),
                )


def init_db():
    """启动时调用：建库、建表、初始化数据。

    对建库与建表语句做容错：云端数据库可能不允许 CREATE DATABASE（已由控制台
    预先创建），此时给出提示并继续；个别 DDL 不兼容时记录警告但不中断启动。
    """
    # 1. 尝试建库（本地 MySQL 需要；TiDB Cloud 等通常已在控制台建好）
    try:
        conn = _connect_server()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` "
                    f"DEFAULT CHARACTER SET {Config.MYSQL_CHARSET}"
                )
        finally:
            conn.close()
    except Exception as e:
        print(f'[init] 跳过建库（{e}）；若数据库不存在，请在云控制台创建 "{Config.MYSQL_DB}"')

    # 2. 建表 / 建视图（逐条容错）
    conn = _connect_db()
    try:
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
        with open(schema_path, 'r', encoding='utf-8') as f:
            statements = _split_sql(f.read())
        with conn.cursor() as cur:
            for stmt in statements:
                try:
                    cur.execute(stmt)
                except Exception as e:
                    first_line = stmt.strip().splitlines()[0][:80]
                    print(f'[init][warn] 语句执行失败（已跳过）：{first_line}\n           {e}')
    finally:
        conn.close()

    # 3. 预置管理员与难度数据
    conn = _connect_db()
    try:
        _seed(conn)
    finally:
        conn.close()
    print(f'[init] 数据库 `{Config.MYSQL_DB}` 初始化完成')
