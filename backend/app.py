# -*- coding: utf-8 -*-
"""
基于 Flask + HTML5 Canvas 的俄罗斯方块游戏 —— 后端应用入口

启动方式：
    cd backend
    python app.py
启动后访问：http://127.0.0.1:5000
默认管理员：admin / admin123
"""
import os
from flask import Flask, request, send_from_directory
from flask_cors import CORS

from config import Config
from db import init_db, close_db
from utils import fail
from blueprints import auth_bp, user_bp, game_bp, leaderboard_bp, admin_bp

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))


def create_app():
    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
    app.config.from_object(Config)

    # 前后端分离部署下的跨域支持
    CORS(app, resources={r'/api/*': {'origins': '*'}})

    # 请求结束释放数据库连接
    app.teardown_appcontext(close_db)

    # 注册业务蓝图：用户模块 / 游戏成绩模块 / 排行榜 / 管理模块
    app.register_blueprint(auth_bp.bp)
    app.register_blueprint(user_bp.bp)
    app.register_blueprint(game_bp.bp)
    app.register_blueprint(leaderboard_bp.bp)
    app.register_blueprint(admin_bp.bp)

    # ---------- 前端页面路由 ----------
    @app.get('/')
    def index():
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.get('/<path:page>.html')
    def html_page(page):
        return send_from_directory(FRONTEND_DIR, f'{page}.html')

    # ---------- 统一错误处理（API 返回 JSON） ----------
    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith('/api/'):
            return fail('接口不存在', 404)
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return fail('请求方法不被允许', 405)

    @app.errorhandler(500)
    def server_error(_e):
        return fail('服务器内部错误', 500)

    return app


app = create_app()

if __name__ == '__main__':
    # 首次启动自动建库、建表并写入预置数据
    init_db()
    # 绑定 0.0.0.0 使局域网内其他人可通过本机 IP 访问
    app.run(host=Config.HOST, port=Config.PORT, debug=False)
