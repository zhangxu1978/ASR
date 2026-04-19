@echo off
chcp 65001 >nul
echo ========================================
echo    Qwen3-ASR 歌词识别服务
echo ========================================
echo.
echo 正在启动服务...
echo 请访问: http://localhost:8000
echo 按 Ctrl+C 停止服务
echo.

cd /d "%~dp0"

python main.py

pause
