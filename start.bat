@echo off
chcp 65001 >nul 2>&1
title 俄罗斯方块游戏 - 启动器
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ════════════════════════════════════════════════
echo     基于 Flask + HTML5 Canvas 的俄罗斯方块游戏
echo     第 6 组 课程设计项目
echo ════════════════════════════════════════════════
echo.

REM ---------- 1. 检查 Python ----------
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo    ✗ 未检测到 Python，请先安装 Python 3.9+
    echo    下载地址：https://www.python.org/downloads/
    echo    安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo    ✓ Python %PYVER%
echo.

REM ---------- 2. 创建虚拟环境 ----------
echo [2/5] 创建虚拟环境...
if not exist "backend\venv" (
    python -m venv backend\venv
    echo    虚拟环境已创建
) else (
    echo    虚拟环境已存在，跳过
)
call "backend\venv\Scripts\activate.bat"
echo.

REM ---------- 3. 安装依赖 ----------
echo [3/5] 安装 Python 依赖...
pip install -r backend\requirements.txt -q 2>nul
echo    ✓ 依赖安装完成
echo.

REM ---------- 4. 配置数据库 ----------
echo [4/5] 配置 MySQL 数据库连接...
if exist "backend\db_config.json" (
    echo    已检测到 db_config.json，将使用已有配置
) else (
    echo    请输入 MySQL 数据库连接信息（直接回车使用默认值）：
    set /p mysql_user="    MySQL 用户名 (默认 root): "
    if "!mysql_user!"=="" set mysql_user=root
    set /p mysql_pwd="    MySQL 密码 (默认 123456): "
    if "!mysql_pwd!"=="" set mysql_pwd=123456
    set /p mysql_host="    MySQL 主机地址 (默认 127.0.0.1): "
    if "!mysql_host!"=="" set mysql_host=127.0.0.1
    set /p mysql_port="    MySQL 端口 (默认 3306): "
    if "!mysql_port!"=="" set mysql_port=3306

    echo {"mysql_host":"!mysql_host!","mysql_port":!mysql_port!,"mysql_user":"!mysql_user!","mysql_password":"!mysql_pwd!","mysql_db":"tetris_db","admin_username":"admin","admin_password":"admin123"} > "backend\db_config.json"
    echo    ✓ 配置已保存到 backend\db_config.json
)
echo.

REM ---------- 5. 启动服务 ----------
echo [5/5] 启动游戏服务...
echo.
echo ════════════════════════════════════════════════
echo   游戏即将启动！
echo.
echo   本机访问地址：  http://127.0.0.1:5000
echo   局域网访问地址：http://你的IP:5000
echo.
echo   默认管理员账号：admin / admin123
echo   其他用户可自行注册账号后游玩
echo.
echo   按 Ctrl+C 可停止服务
echo ════════════════════════════════════════════════
echo.

python backend\app.py

pause
