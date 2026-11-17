#!/bin/bash
# 在同一 Wi-Fi 分享报告：给同事一个网址，而不是本地文件。
cd "$(dirname "$0")" || exit 1
CODE="${RADAR_CODE:-$(python3 -c 'import secrets;print(secrets.token_hex(3))')}"
export RADAR_HOST=0.0.0.0 RADAR_CODE="$CODE"
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo "=============================================="
echo " 同一 Wi-Fi 的同事/家长打开："
echo "   http://${IP:-<本机IP>}:8765/?code=$CODE"
echo " 访问码：$CODE  （关闭此窗口即停止分享）"
echo "=============================================="
python3 tools/serve.py
