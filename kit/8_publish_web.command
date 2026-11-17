#!/bin/bash
# Publish the radar report as a web page.
#
#   double-click                    -> invitation-only page (anonymised, one code per parent)
#   ./8_publish_web.command public  -> public, indexed, anonymised demo
#   ./8_publish_web.command full    -> public with REAL learner data (typed confirmation required)
#
# The first run walks you through a one-time GitHub device login.

set -u
cd "$(dirname "$0")" || exit 1

MODE="${1:-private}"
PY="$(command -v python3)"

if [ -z "$PY" ]; then
  echo "python3 not found - install the Xcode command line tools first."
  read -r -p "Press Enter to close…" _
  exit 1
fi

case "$MODE" in
  private) MODE_FLAG="--mode private" ;;
  public)  MODE_FLAG="--mode redacted" ;;
  full)
    cat <<'WARN'
⚠  full mode publishes REAL learner data
   87 names, grades and parent email addresses, indexable by any search engine.
   GitHub Pages has no access control: anyone with the link - or a search result -
   can download the page. Only continue if your school has approved this.
WARN
    read -r -p "Type PUBLISH to continue: " ok
    [ "$ok" = "PUBLISH" ] || { echo "cancelled."; exit 1; }
    MODE_FLAG="--mode full" ;;
  *) echo "unknown mode: $MODE (use private | public | full)"; exit 1 ;;
esac

echo
echo "== 1/4 checking the GitHub login =="
LOGIN_OK=0
if [ -s token.txt ]; then
  if curl -s -o /dev/null -w "%{http_code}" -H "Authorization: token $(cat token.txt)" \
      https://api.github.com/user | grep -q 200; then
    LOGIN_OK=1
    echo "token OK"
  else
    echo "token expired - a fresh login is needed"
  fi
fi
if [ "$LOGIN_OK" = "0" ]; then
  echo
  echo "Open https://github.com/login/device in a browser and enter the code below."
  echo
  "$PY" tools/github_login.py || { echo "login failed."; read -r -p "Press Enter to close…" _; exit 1; }
fi

echo
echo "== 2/4 issuing access codes =="
if [ "$MODE" = "private" ]; then
  "$PY" tools/make_invites.py || { echo "could not issue codes."; read -r -p "Press Enter to close…" _; exit 1; }
elif [ -f invites.json ]; then
  echo "public mode - existing invites.json is not used"
fi

echo
echo "== 3/4 building and pushing =="
"$PY" tools/publish_web.py $MODE_FLAG || { echo "publish failed."; read -r -p "Press Enter to close…" _; exit 1; }

if [ "$MODE" = "private" ]; then
  echo
  echo "== 4/4 invitations =="
  echo "One personal link per parent is in invites.csv; the bilingual email template is invites_email.txt."
  "$PY" - <<'PY'
import csv, os
rows = list(csv.DictReader(open("invites.csv", encoding="utf-8-sig")))
print("   %d invitations ready, e.g. %s -> %s" % (len(rows), rows[0]["student"], rows[0]["link"]))
PY
else
  echo
  echo "== 4/4 telling the search engines =="
  "$PY" tools/indexnow.py || true
fi

cat <<'DONE'

Done. The page is live at:
  https://tiger20240331.github.io/Intschool/

Press Enter to close…
DONE
read -r _
