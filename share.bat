@echo off
chcp 65001 >nul 2>&1
title 俄罗斯方块游戏 - 公网分享模式
cd /d "%~dp0"

echo ════════════════════════════════════════════════
echo     俄罗斯方块 - 公网分享模式
echo     启动后将生成公网链接，分享给好友即可游玩
echo ════════════════════════════════════════════════
echo.

REM ---------- 检查 Python ----------
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ 未检测到 Python，请先安装 Python 3.9+
    echo   下载：https://www.python.org/downloads/
    pause
    exit /b 1
)

REM ---------- 安装依赖 ----------
echo 正在检查依赖...
pip install -r backend\requirements.txt -q 2>nul
echo ✓ 依赖就绪
echo.

REM ---------- 配置数据库 ----------
if not exist "backend\db_config.json" (
    echo 首次运行，请配置 MySQL 数据库连接：
    set /p mysql_user="  MySQL 用户名 (默认 root): "
    if "!mysql_user!"=="" set mysql_user=root
    set /p mysql_pwd="  MySQL 密码 (默认 123456): "
    if "!mysql_pwd!"=="" set mysql_pwd=123456
    echo {"mysql_host":"127.0.0.1","mysql_port":3306,"mysql_user":"!mysql_user!","mysql_password":"!mysql_pwd!","mysql_db":"tetris_db","admin_username":"admin","admin_password":"admin123"} > "backend\db_config.json"
    echo ✓ 配置已保存
    echo.
)

REM ---------- 启动分享模式 ----------
echo 正在启动公网分享模式...
echo.
python backend\share.py

pause
