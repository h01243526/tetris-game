# -*- coding: utf-8 -*-
"""数据访问层：双驱动（MySQL / SQLite）连接管理、数据库初始化、常用查询封装。

DB_DRIVER=mysql  本地 MySQL / TiDB Cloud（默认，原行为不变）
DB_DRIVER=sqlite 无独立数据库平台（如 PythonAnywhere 免费版），数据存本地文件
"""
import os
import sqlite3
import ssl
from datetime import datetime, date

from flask import g
from werkzeug.security import generate_password_hash

from config import Config

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:  # sqlite 模式下允许不安装 PyMySQL
    pymysql = None
    DictCursor = None


_IS_SQLITE = Config.DB_DRIVER == 'sqlite'


# ----------------------------------------------------------------------
# SQLite 适配层：把 sqlite3 包装成与 PyMySQL 一致的用法
# （%s 占位符 -> ?、datetime 参数转字符串、cursor 支持 with、提供 begin/commit）
# ----------------------------------------------------------------------
class _SQLiteCursor:
    def __init__(self, cur):
        self._cur = cur

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self._cur.close()

    @staticmethod
    def _convert(value):
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        return value

    def execute(self, sql, args=()):
        sql = sql.replace('%s', '?')
        return self._cur.execute(sql, tuple(self._convert(a) for a in args))

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(r) for r in self._cur.fetchall()]

    @property
    def lastrowid(self):
        return self._cur.lastrowid


class _SQLiteConn:
    """autocommit 模式（isolation_level=None）；begin() 开启显式事务。"""

    def __init__(self, path):
        db_dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute('PRAGMA foreign_keys = ON')
        self._conn.execute('PRAGMA busy_timeout = 5000')

    def cursor(self):
        return _SQLiteCursor(self._conn.cursor())

    def begin(self):
        self._conn.execute('BEGIN')

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _connect_sqlite():
    return _SQLiteConn(Config.SQLITE_PATH)


# ----------------------------------------------------------------------
# MySQL 连接参数（本地 MySQL 无需 SSL；TiDB Cloud 等云数据库强制 TLS）
# ----------------------------------------------------------------------
def _ssl_context():
    """按需构造 SSLContext；返回 None 表示不启用 TLS。"""
    if not Config.MYSQL_SSL:
        return None
    ctx = ssl.create_default_context()
    if Config.MYSQL_SSL_CA:
        ctx.load_verify_locations(cafile=Config.MYSQL_SSL_CA)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    else:
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
        if _IS_SQLITE:
            g.db = _connect_sqlite()
        else:
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
# 数据库初始化：执行 schema 脚本 -> 预置管理员与难度配置
# 说明：MySQL 模式先尝试建库（云端可能不允许，容错跳过）；
#       所有 DDL 逐条容错，个别不兼容时记录警告但不中断启动。
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


def _apply_schema(conn, script_name):
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
    with open(schema_path, 'r', encoding='utf-8') as f:
        statements = _split_sql(f.read())
    with conn.cursor() as cur:
        for stmt in statements:
            try:
                cur.execute(stmt)
            except Exception as e:
                first_line = stmt.strip().splitlines()[0][:80]
                print(f'[init][warn] 语句执行失败（已跳过）：{first_line}\n           {e}')


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
            print(f'[init] 已创建管理员账号：{Config.ADMIN_USERNAME}')

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
    """启动时调用：建表、初始化数据（幂等）。"""
    if _IS_SQLITE:
        conn = _connect_sqlite()
        try:
            _apply_schema(conn, 'schema_sqlite.sql')
            _seed(conn)
        finally:
            conn.close()
        print(f'[init] SQLite 数据库初始化完成：{Config.SQLITE_PATH}')
        return

    # MySQL：先尝试建库（TiDB Cloud 等已预建时会失败，容错继续）
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

    conn = _connect_db()
    try:
        _apply_schema(conn, 'schema.sql')
        _seed(conn)
    finally:
        conn.close()
    print(f'[init] 数据库 `{Config.MYSQL_DB}` 初始化完成')
