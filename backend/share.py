# -*- coding: utf-8 -*-
"""
一键公网分享脚本：启动 Flask 服务 + SSH 内网穿透隧道
其他人通过公网链接即可直接访问游戏，无需安装任何环境。

使用方式：  python backend/share.py
停止：      Ctrl+C
"""
import os
import sys
import time
import re
import subprocess
import signal
import webbrowser

# 确保能导入同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from db import init_db


def start_flask():
    """以子进程方式启动 Flask 服务。"""
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    proc = subprocess.Popen(
        [sys.executable, __file__.replace('share.py', 'app.py')],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
    )
    # 等待 Flask 启动
    time.sleep(3)
    print('[flask] 服务已启动，监听 0.0.0.0:5000', flush=True)
    return proc


def start_tunnel():
    """通过 SSH 反向隧道将本地 5000 端口暴露到公网（serveo.net，免费免注册）。"""
    proc = subprocess.Popen(
        ['ssh', '-o', 'StrictHostKeyChecking=no',
         '-o', 'ServerAliveInterval=30',
         # 关键：用 127.0.0.1 而非 localhost，避免 IPv6 解析导致 502
         '-R', '80:127.0.0.1:5000',
         'serveo.net'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    url = None
    deadline = time.time() + 20
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.3)
            continue
        print(f'[tunnel] {line.strip()}', flush=True)
        m = re.search(r'https://([\w.-]+)', line)
        if m and 'serveo' in m.group(0):
            url = m.group(0)
            break

    return proc, url


def write_entry_html(url):
    """将当前公网链接写入「开始游戏.html」，用户双击即可进入游戏。

    每次启动 share.py 都会刷新此文件，所以即使公网链接变化，
    只要重新运行过 share.bat，双击 HTML 就能跳转到最新地址。
    """
    html_path = os.path.join(os.path.dirname(__file__), '..', '开始游戏.html')
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>俄罗斯方块 · 开始游戏</title>
<meta http-equiv="refresh" content="0;url={url}/">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh;
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: #fff; font-family: 'Segoe UI', system-ui, sans-serif;
  }}
  .card {{
    text-align: center; padding: 50px 60px;
    border-radius: 20px;
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.1);
  }}
  .icon {{
    font-size: 64px; margin-bottom: 20px;
    display: inline-block; animation: bounce 1s infinite;
  }}
  h1 {{ font-size: 28px; margin-bottom: 10px; }}
  p  {{ color: #aaa; font-size: 15px; }}
  @keyframes bounce {{
    0%,100% {{ transform: translateY(0); }}
    50%    {{ transform: translateY(-10px); }}
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="icon">🎮</div>
    <h1>正在进入游戏...</h1>
    <p>若页面未自动跳转，请<a href="{url}/" style="color:#4fc3f7;text-decoration:none">点此进入</a></p>
  </div>
</body>
</html>
'''
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f'[entry] 已更新入口文件：{os.path.abspath(html_path)}', flush=True)


def main():
    print('=' * 56, flush=True)
    print('     俄罗斯方块游戏 — 公网分享模式', flush=True)
    print('     其他人无需安装任何环境，浏览器打开链接即可游玩', flush=True)
    print('=' * 56, flush=True)

    # 1. 初始化数据库（首次运行自动建库建表）
    print('[1/3] 初始化数据库...', flush=True)
    init_db()

    # 2. 启动 Flask
    print('[2/3] 启动游戏服务...', flush=True)
    flask_proc = start_flask()

    # 3. 启动公网隧道
    print('[3/3] 建立公网隧道...', flush=True)
    tunnel_proc, url = start_tunnel()

    if not url:
        print('\n*** 隧道建立失败 ***', flush=True)
        print('可能原因：网络问题或 serveo.net 暂时不可用', flush=True)
        print('你仍可通过局域网分享：http://你的本机IP:5000', flush=True)
        flask_proc.terminate()
        sys.exit(1)

    # 写入「开始游戏.html」入口文件（双击即可进入游戏）
    write_entry_html(url)

    # 自动打开浏览器
    print('[browser] 正在打开浏览器...', flush=True)
    webbrowser.open(url + '/')

    print(flush=True)
    print('=' * 56, flush=True)
    print(f'  ✓ 游戏已上线！将以下链接分享给好友：\n', flush=True)
    print(f'    {url}\n', flush=True)
    print(f'  管理员账号：admin / admin123（仅你可登录管理后台）\n', flush=True)
    print(f'  其他人打开链接即可注册/登录/游玩\n', flush=True)
    print(f'  💡 浏览器已自动打开游戏页面\n', flush=True)
    print(f'  按 Ctrl+C 停止服务（服务停止后链接失效）', flush=True)
    print('=' * 56, flush=True)

    # 保持运行
    try:
        while True:
            time.sleep(1)
            if flask_proc.poll() is not None:
                print('[flask] 服务已停止', flush=True)
                break
            if tunnel_proc.poll() is not None:
                print('[tunnel] 隧道已断开，尝试重连...', flush=True)
                tunnel_proc, new_url = start_tunnel()
                if new_url:
                    write_entry_html(new_url)
                    print(f'[tunnel] 重连成功：{new_url}', flush=True)
                else:
                    print('[tunnel] 重连失败，服务仍在本地运行', flush=True)
                    break
    except KeyboardInterrupt:
        print('\n正在停止服务...', flush=True)
    finally:
        flask_proc.terminate()
        tunnel_proc.terminate()
        try:
            flask_proc.wait(timeout=5)
        except Exception:
            flask_proc.kill()
        try:
            tunnel_proc.wait(timeout=5)
        except Exception:
            tunnel_proc.kill()
        print('已停止。', flush=True)


if __name__ == '__main__':
    main()
