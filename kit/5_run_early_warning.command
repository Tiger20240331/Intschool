#!/bin/bash
cd "$(dirname "$0")"
python3 tools/collect.py || { echo "采集失败"; read -n 1 -s -r -p ""; exit 1; }
python3 tools/early_warning.py
echo
echo "输出在 output/early_warning_*.md / .json 与 *.eml"
open output 2>/dev/null || true
read -n 1 -s -r -p "按任意键关闭..."
