#!/bin/bash
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then echo "需要 Python 3"; read -n 1 -s -r -p "按任意键关闭..."; exit 1; fi
if curl -s -o /dev/null "http://127.0.0.1:8765/"; then
  open "http://127.0.0.1:8765/"; echo "已在运行，直接打开。"; sleep 1; exit 0
fi
echo "启动本地服务（保持此窗口打开；关闭即停止）…"
python3 tools/serve.py &
SERVER_PID=$!
sleep 1.5
open "http://127.0.0.1:8765/"
wait $SERVER_PID
