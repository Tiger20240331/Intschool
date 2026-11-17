#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub device-flow login - no browser automation, no password ever typed here.

    python3 tools/github_login.py          # prints a code, waits for approval

On success the token is written to token.txt (chmod 600) next to this kit.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
TOKEN_FILE = os.path.join(KIT, "token.txt")

CLIENT_ID = "178c6fc778ccc68e1d6a"  # GitHub CLI's public client id
SCOPE = "public_repo"


def post(url, data):
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Accept": "application/json", "User-Agent": "radar-on-intschool"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    try:
        start = post("https://github.com/login/device/code", {"client_id": CLIENT_ID, "scope": SCOPE})
    except urllib.error.HTTPError as e:
        sys.exit("GitHub rejected the device-code request: %s %s" % (e.code, e.read().decode()[:200]))

    print("verification_uri: %s" % start["verification_uri"])
    print("user_code: %s" % start["user_code"])
    sys.stdout.flush()

    interval = int(start.get("interval", 5))
    deadline = time.time() + int(start.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(interval)
        try:
            res = post("https://github.com/login/oauth/access_token", {
                "client_id": CLIENT_ID,
                "device_code": start["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            })
        except urllib.error.HTTPError as e:
            print("poll error", e.code); continue
        err = res.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        if err in ("expired_token", "access_denied", "bad_verification_code"):
            sys.exit("login %s - run this script again" % err)
        token = res.get("access_token")
        if token:
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(token)
            os.chmod(TOKEN_FILE, 0o600)
            scopes = res.get("scope", "")
            print("token saved (scopes: %s)" % scopes)
            return
        sys.exit("unexpected response: %s" % res)
    sys.exit("code expired - run this script again")


if __name__ == "__main__":
    main()
