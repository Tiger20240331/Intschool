#!/bin/bash
cd "$(dirname "$0")"
python3 tools/collect.py || { echo "采集失败"; read -n 1 -s -r -p ""; exit 1; }
python3 tools/early_warning.py --semester-report
echo
echo "学期报告草稿在 output/semester_reports/ 下（HTML，可打印为 PDF）"
open output/semester_reports 2>/dev/null || true
read -n 1 -s -r -p "按任意键关闭..."
