#!/bin/bash
cd "$(dirname "$0")"
echo "== 第 1 步：获取 IntSchool 登录 token =="
echo "请先在 Chrome 登录 https://teacher.intschool.cn（保持该标签页打开）。"
echo
TOKEN="$(osascript <<'APPLESCRIPT' 2>/dev/null
tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if URL of t contains "teacher.intschool.cn" then
        return execute t javascript "JSON.parse(localStorage.getItem('token')).token"
      end if
    end repeat
  end repeat
end tell
return ""
APPLESCRIPT
)"
if [ -z "$TOKEN" ]; then
  echo "自动读取失败：可能没有打开 IntSchool 标签页，或 Chrome 未允许 JavaScript from Apple Events。"
  echo "可一键开启：Chrome 菜单 View → Developer → 勾选 Allow JavaScript from Apple Events，然后重试。"
  echo
  echo "或手动：在 IntSchool 页面按 F12 → Console，粘贴下面一行回车："
  echo '  copy(JSON.parse(localStorage.getItem("token")).token)'
  echo "然后把复制到的 token 粘贴到这里："
  read -r TOKEN
fi
if [ -z "$TOKEN" ]; then echo "未获得 token，退出。"; exit 1; fi
printf '%s' "$TOKEN" > token.txt
chmod 600 token.txt
echo
EXP="$(python3 - "$TOKEN" <<'PY' 2>/dev/null
import sys,base64,json,datetime
t=sys.argv[1]
try:
    p=t.split('.')[1]; p+='='*(-len(p)%4)
    d=json.loads(base64.urlsafe_b64decode(p))
    print(datetime.datetime.fromtimestamp(d['exp']).strftime('%Y-%m-%d'))
except Exception:
    print('')
PY
)"
if [ -n "$EXP" ]; then
  echo "已保存 token。有效期至：$EXP（默认约 1 年；过期后重跑本步骤）。"
else
  echo "已保存 token（有效期约 1 年；过期后重跑本步骤）。"
fi
read -n 1 -s -r -p "按任意键关闭..."
