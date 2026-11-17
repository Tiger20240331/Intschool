#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create an Outlook draft (compose window) from JSON on stdin: {to:[...], subject, body}.

macOS only. Uses AppleScript against Microsoft Outlook; if that fails, writes an .eml
next to the kit and opens it with Outlook instead.
"""
import json, os, subprocess, sys, tempfile, uuid

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def apple_quote(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def make_draft(to, subject, body):
    to = [t.strip() for t in (to or []) if t and "@" in t]
    tmp = os.path.join(tempfile.gettempdir(), f"radar-draft-{uuid.uuid4().hex}.txt")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body or "")
    lines = [
        f'set bodyText to (read POSIX file "{apple_quote(tmp)}" as «class utf8»)',
        'tell application "Microsoft Outlook"',
        f'  set m to make new outgoing message with properties {{subject:"{apple_quote(subject)}", content:bodyText}}',
    ]
    for addr in to:
        lines.append(f'  make new recipient at m with properties {{email address:{{address:"{apple_quote(addr)}"}}}}')
    lines += ['  open m', 'end tell']
    script = "\n".join(lines)
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=25)
        if r.returncode == 0:
            return {"ok": True, "mode": "applescript", "recipients": to}
        err = (r.stderr or r.stdout).strip()[:300]
    except Exception as e:
        err = str(e)[:300]
    # fallback: write an .eml and let Outlook open it
    try:
        eml = os.path.join(KIT, "output", "Radar_draft.eml")
        headers = [
            "From: ", "To: " + "; ".join(to), f"Subject: {subject}",
            "MIME-Version: 1.0", "Content-Type: text/plain; charset=utf-8",
            "Content-Transfer-Encoding: 8bit", "",
        ]
        with open(eml, "w", encoding="utf-8") as f:
            f.write("\r\n".join(headers) + "\r\n" + (body or ""))
        subprocess.run(["open", "-a", "Microsoft Outlook", eml], timeout=15)
        return {"ok": True, "mode": "eml", "file": eml, "recipients": to, "note": err}
    except Exception as e2:
        return {"ok": False, "error": err or str(e2)[:300]}


if __name__ == "__main__":
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"bad json: {e}"}))
        sys.exit(1)
    print(json.dumps(make_draft(payload.get("to"), payload.get("subject", "Student update"), payload.get("body", "")),
                     ensure_ascii=False))
