@echo off
chcp 65001 >nul 2>&1
title 俄罗斯方块 - 正在启动
cd /d "%~dp0"

echo ════════════════════════════════════════════════
echo   俄罗斯方块 · 一键启动
echo   浏览器将自动打开，请稍候...
echo ════════════════════════════════════════════════
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ 未检测到 Python，请先安装 Python 3.9+
    echo   下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 安装依赖
pip install -r backend\requirements.txt -q >nul 2>&1

REM 配置数据库（首次运行自动创建默认配置）
if not exist "backend\db_config.json" (
    echo {"mysql_host":"127.0.0.1","mysql_port":3306,"mysql_user":"root","mysql_password":"123456","mysql_db":"tetris_db","admin_username":"admin","admin_password":"admin123"} > "backend\db_config.json"
)

REM 启动服务（share.py 会自动初始化数据库、启动 Flask、建立隧道、打开浏览器）
python backend\share.py

pause
