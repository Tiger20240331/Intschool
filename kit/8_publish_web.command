#!/bin/bash
# Publish the radar report as a public webpage on GitHub Pages.
#
#   double-click                     -> publishes the anonymised demo (names removed)
#   ./8_publish_web.command full     -> publishes the real report, after a typed confirmation
#
# Needs a GitHub token the first time; the script walks you through a one-time
# device login (code + github.com/login/device) and then remembers it in token.txt.

set -u
cd "$(dirname "$0")" || exit 1

MODE="${1:-redacted}"
PY="$(command -v python3)"

if [ -z "$PY" ]; then
  echo "python3 not found - install the Xcode command line tools first."
  read -r -p "Press Enter to close…" _
  exit 1
fi

if [ "$MODE" = "full" ]; then
  cat <<'WARN'
⚠  full mode publishes REAL learner data
   87 names, grades and parent email addresses, indexable by any search engine.
   GitHub Pages keeps no access control: anyone with the link - or a search result -
   can download the page. Only continue if your school has approved this.
WARN
  read -r -p "Type PUBLISH to continue: " ok
  [ "$ok" = "PUBLISH" ] || { echo "cancelled."; exit 1; }
fi

echo
echo "== 1/3 checking the GitHub login =="
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
echo "== 2/3 building and pushing =="
"$PY" tools/publish_web.py --mode "$MODE" || { echo "publish failed."; read -r -p "Press Enter to close…" _; exit 1; }

echo
echo "== 3/3 telling the search engines =="
"$PY" tools/indexnow.py || true

cat <<'DONE'

Done. The page is live at:
  https://tiger20240331.github.io/Intschool/

Indexing is not instant: Bing/Yandex usually pick it up within hours, Google within
days-to-weeks. To speed Google up, open Google Search Console once, add the property
and submit https://tiger20240331.github.io/Intschool/sitemap.xml

Press Enter to close…
DONE
read -r _
