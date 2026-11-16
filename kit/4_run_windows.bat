@echo off
cd /d %~dp0
if not exist token.txt (
  echo 请先创建 token.txt（把 IntSchool 的 token 粘贴进去，一行）。
  pause & exit /b
)
python tools\collect.py || (pause & exit /b)
python tools\render_radar.py || (pause & exit /b)
echo.
echo 完成。报告在 output 目录。
start "" output
pause
