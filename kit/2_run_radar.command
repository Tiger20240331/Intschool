#!/bin/bash
cd "$(dirname "$0")"
echo "== 第 2 步：生成并打开你的 Radar Report Card =="
if [ ! -f token.txt ]; then
  echo "还没有 token.txt，请先双击 1_get_token.command。"
  read -n 1 -s -r -p "按任意键关闭..."; exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 python3。请先安装 Python 3。"
  read -n 1 -s -r -p "按任意键关闭..."; exit 1
fi
python3 tools/collect.py || { echo "采集失败，请查看上方错误。"; read -n 1 -s -r -p "按任意键关闭..."; exit 1; }
python3 tools/render_radar.py || { echo "生成失败。"; read -n 1 -s -r -p "按任意键关闭..."; exit 1; }
HTML="$(ls -t output/Radar_*.html 2>/dev/null | head -1)"
echo
echo "完成：$HTML"
if ! curl -s -o /dev/null "http://127.0.0.1:8765/"; then
  echo "启动本地服务（保持此窗口打开，关闭即停止）…"
  python3 tools/serve.py &
  SERVER_PID=$!
  sleep 1.5
fi
open "http://127.0.0.1:8765/"
echo "页面每次打开会自动刷新数据（约 1–2 分钟）。"
[ -n "$SERVER_PID" ] && wait $SERVER_PID
read -n 1 -s -r -p "按任意键关闭..."
