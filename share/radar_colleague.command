#!/bin/bash
# Radar on Intschool — installer / updater for a colleague's Mac.
#
# Double-click this file. First run: downloads the skill into ~/RadarSkill and sets up a
# daily automatic update. Run it again any time to update immediately.
#
#   --no-auto   skip the daily update job
#   --check     only report the installed version
#   --quiet     log-only mode (used by the daily job)

set -u
REPO_URL="${RADAR_REPO:-https://github.com/Tiger20240331/Intschool.git}"
TARGET="${RADAR_HOME:-$HOME/RadarSkill}"
MODE="${1:-}"
PLIST="$HOME/Library/LaunchAgents/com.radar.intschool.update.plist"

version_of() { /usr/bin/python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" "$1/package.json" 2>/dev/null || echo "?"; }
line() { [ "$MODE" = "--quiet" ] || printf '%s\n' "$1"; }

if ! command -v git >/dev/null 2>&1; then
  cat <<'EOF'
This Mac needs the Apple command line tools once (it installs git).

  1. In Terminal, run:  xcode-select --install
  2. Click "Install" in the window that pops up, wait until it finishes.
  3. Double-click this file again.
EOF
  read -r -p "Press Enter to close…" _
  exit 1
fi

# ---------- first install -------------------------------------------------------
if [ ! -d "$TARGET/.git" ]; then
  line "Downloading the Radar skill, please wait…"
  mkdir -p "$(dirname "$TARGET")"
  if ! git clone --quiet --depth 1 "$REPO_URL" "$TARGET" 2>/dev/null; then
    echo "The download failed. Check the internet connection, then double-click this file again."
    read -r -p "Press Enter to close…" _
    exit 1
  fi
  ver="$(version_of "$TARGET")"
  printf '%s\n' "$TARGET" | pbcopy 2>/dev/null || true
  cat <<DONE

✅ Installed version $ver
   The folder is copied to your clipboard.

Two clicks left, once only:

  1. Open DeepSeek Harness
  2. Plugins  →  install from path  →  paste (⌘V)  →  choose "Radar on Intschool"

From now on this file updates itself — nothing else to download or send.
DONE
else
  # ---------- update ----------------------------------------------------------
  before="$(version_of "$TARGET")"
  if [ "$MODE" = "--check" ]; then
    remote="$(git -C "$TARGET" ls-remote --tags --refs origin 'v*' 2>/dev/null | awk -F/ '{print $NF}' | sort -V | tail -1)"
    echo "installed: $before"
    echo "latest   : ${remote:-unknown}"
    exit 0
  fi
  if ! git -C "$TARGET" pull --ff-only --quiet 2>/dev/null; then
    line "Could not update just now (offline, or the folder was edited)."
    line "Open Terminal and run:  git -C \"$TARGET\" status"
    [ "$MODE" = "--quiet" ] || read -r -p "Press Enter to close…" _
    exit 1
  fi
  after="$(version_of "$TARGET")"
  if [ "$before" = "$after" ]; then
    line "Already up to date (version $after)."
  else
    echo "Updated $before → $after"
    line "In DeepSeek Harness: Plugins → switch Radar off and on again (or restart the app)."
  fi
  [ "$MODE" = "--quiet" ] || read -r -p "Press Enter to close…" _
fi

# ---------- daily automatic update ----------------------------------------------
if [ "$MODE" != "--no-auto" ] && [ "$MODE" != "--check" ] && [ "$MODE" != "--quiet" ]; then
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
  if launchctl load -w "$PLIST" 2>/dev/null; then
    echo
    echo "Automatic updates: ON — checked daily at 07:30, silent unless the version changes."
  else
    echo
    echo "Automatic updates could not be scheduled. The file is at: $PLIST"
  fi
fi

if [ "$MODE" != "--quiet" ] && [ "$MODE" != "--check" ]; then
  read -r -p "Press Enter to close…" _
fi
