@echo off
chcp 65001 >nul
cd /d D:\cctv-ai
title 工地 AI 監控控制台
echo ============================================
echo    工地 AI 監控控制台 啟動中...
echo    伺服器就緒後會自動開啟瀏覽器(約 20 秒)
echo    要關閉:直接關掉這個視窗,或按 Ctrl+C
echo ============================================
echo.
rem 背景等 20 秒後自動開瀏覽器
start "" cmd /c "timeout /t 20 >nul & start http://localhost:8080"
python webpanel.py
echo.
echo 伺服器已停止。按任意鍵關閉視窗。
pause >nul
