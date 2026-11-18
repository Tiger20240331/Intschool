#!/bin/bash
# Radar on Intschool — one command that keeps a colleague's copy current.
#
#   double-click / bash share/radar_colleague.command          first run: clone, then update
#   bash share/radar_colleague.command --auto                  also install a daily 07:30 update job
#   bash share/radar_colleague.command --check                 only report local vs remote version
#
# The clone lives at $RADAR_HOME (default ~/RadarSkill) and is symlinked into DSH, so
# "updating" is just `git pull` — no tarballs, no re-downloading the whole package.

set -u
REPO_URL="${RADAR_REPO:-https://github.com/Tiger20240331/Intschool.git}"
TARGET="${RADAR_HOME:-$HOME/RadarSkill}"
MODE="${1:-}"
PLIST="$HOME/Library/LaunchAgents/com.radar.intschool.update.plist"

version_of() { /usr/bin/python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" "$1/package.json" 2>/dev/null || echo "?"; }
say() { [ "${2:-}" = "quiet" ] || printf '%s\n' "$1"; }

if ! command -v git >/dev/null 2>&1; then
  echo "git not found. Run: xcode-select --install   (then try again)"
  exit 1
fi

if [ ! -d "$TARGET/.git" ]; then
  echo "== first install =="
  mkdir -p "$(dirname "$TARGET")"
  git clone --quiet --depth 1 "$REPO_URL" "$TARGET" || { echo "clone failed - check the network / repo URL"; exit 1; }
  echo "cloned $(version_of "$TARGET") into $TARGET"
  cat <<NEXT

One manual step, once per machine:
  DSH -> Plugins -> install from path -> $TARGET
  (or: Plugins -> Add plugin -> pick the folder)

After that, just run this file again (or let the daily job do it) to update.
NEXT
  [ "$MODE" = "--auto" ] || exit 0
else
  before="$(version_of "$TARGET")"
  if [ "$MODE" = "--check" ]; then
    remote="$(git -C "$TARGET" ls-remote --tags --refs origin 'v*' | awk -F/ '{print $NF}' | sort -V | tail -1)"
    echo "installed: $before"
    echo "latest   : ${remote:-unknown}"
    exit 0
  fi
  if ! git -C "$TARGET" pull --ff-only --quiet 2>/dev/null; then
    echo "update failed - the folder has local edits or the network is down:"
    echo "  git -C \"$TARGET\" status"
    exit 1
  fi
  after="$(version_of "$TARGET")"
  if [ "$before" = "$after" ]; then
    [ "$MODE" = "--quiet" ] || echo "already current ($before)"
  else
    echo "updated $before -> $after"
    [ "$MODE" = "--quiet" ] || echo "Reload the plugin in DSH (disable then enable it) or restart DSH to pick it up."
  fi
fi

# --- optional daily auto-update ------------------------------------------------
if [ "$MODE" = "--auto" ]; then
  mkdir -p "$(dirname "$PLIST")"
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.radar.intschool.update</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$TARGET/share/radar_colleague.command</string>
    <string>--quiet</string>
  </array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>
  <key>StandardOutPath</key><string>$TARGET/update.log</string>
  <key>StandardErrorPath</key><string>$TARGET/update.log</string>
  <key>RunAtLoad</key><false/>
</dict></plist>
PLISTEOF
  launchctl unload "$PLIST" 2>/dev/null
  launchctl load -w "$PLIST" 2>/dev/null && echo "daily 07:30 update installed -> $PLIST" \
    || echo "could not load the daily job; the file is at $PLIST"
fi
