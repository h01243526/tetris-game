# -*- coding: utf-8 -*-
"""WSGI 入口（供 gunicorn 等生产级服务器使用）。

云端部署（Render）时启动命令为：
    gunicorn wsgi:application --bind 0.0.0.0:$PORT

导入时完成一次数据库初始化（幂等），保证首次部署自动建表与预置数据。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from db import init_db

try:
    init_db()
except Exception as exc:  # 数据库暂时不可用时不阻断进程启动，便于平台重试
    print(f'[wsgi] 数据库初始化失败：{exc}', flush=True)

application = app
