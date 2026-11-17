#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish the radar report as a static website on GitHub Pages.

    python3 tools/publish_web.py --mode redacted     # public, anonymised demo
    python3 tools/publish_web.py --mode full         # real learner data - public

Needs token.txt (run tools/github_login.py once). The site is force-pushed to the
gh-pages branch, so the branch always mirrors the latest build and carries no history
of earlier uploads.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
TOKEN_FILE = os.path.join(KIT, "token.txt")
DEFAULT_REPO = "Tiger20240331/Intschool"


def token():
    if not os.path.exists(TOKEN_FILE):
        sys.exit("no token.txt - run: python3 tools/github_login.py")
    return open(TOKEN_FILE, encoding="utf-8").read().strip()


def api(method, path, tok, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "token " + tok, "Accept": "application/vnd.github+json",
                 "User-Agent": "radar-on-intschool", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"message": raw[:300]}


def run(cmd, cwd, quiet=True):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        out = (p.stdout + p.stderr).replace("x-access-token:", "x-access-token:***")
        sys.exit("command failed: %s\n%s" % (" ".join(cmd[:2]), out[-1200:]))
    return p.stdout


def config_repo():
    path = os.path.join(KIT, "config.json")
    try:
        cfg = json.load(open(path, encoding="utf-8"))
        if cfg.get("publish_repo"):
            return cfg["publish_repo"]
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "redacted"], default="redacted")
    ap.add_argument("--repo", default=config_repo() or DEFAULT_REPO)
    ap.add_argument("--branch", default="gh-pages")
    args = ap.parse_args()

    owner = args.repo.split("/")[0]
    base = "https://%s.github.io/%s" % (owner.lower(), args.repo.split("/")[1])
    tok = token()

    build = [sys.executable, os.path.join(HERE, "build_site.py"), "--base-url", base]
    if args.mode == "redacted":
        build.append("--redact")

    tmp = tempfile.mkdtemp(prefix="radar-site-")
    site = os.path.join(tmp, "site")
    build += ["--out", site]
    subprocess.run(build, check=True)

    run(["git", "init", "-q"], site)
    run(["git", "checkout", "-q", "-b", args.branch], site)
    run(["git", "add", "-A"], site)
    run(["git", "-c", "user.name=%s" % owner,
         "-c", "user.email=%s@users.noreply.github.com" % owner,
         "commit", "-qm", "Radar report site (%s) %s" % (args.mode, time.strftime("%Y-%m-%d %H:%M"))], site)
    url = "https://x-access-token:%s@github.com/%s.git" % (tok, args.repo)
    run(["git", "push", "-q", "-f", url, "%s:%s" % (args.branch, args.branch)], site)
    print("pushed %s branch to %s" % (args.branch, args.repo))

    st, body = api("GET", "/repos/%s/pages" % args.repo, tok)
    if st == 404:
        st, body = api("POST", "/repos/%s/pages" % args.repo, tok,
                       {"source": {"branch": args.branch, "path": "/"}})
        print("Pages enabled:", st)
    else:
        st, body = api("PUT", "/repos/%s/pages" % args.repo, tok,
                       {"source": {"branch": args.branch, "path": "/"}})
        print("Pages updated:", st)
    if st >= 300:
        sys.exit("cannot configure Pages: %s" % body.get("message"))

    shutil.rmtree(tmp, ignore_errors=True)

    for _ in range(30):
        time.sleep(4)
        st, b = api("GET", "/repos/%s/pages/builds/latest" % args.repo, tok)
        if st == 200 and b.get("status") in ("built", "errored"):
            print("pages build:", b.get("status"), b.get("error") or "")
            break
    print("live url :", base + "/")
    print("mode     :", args.mode)


if __name__ == "__main__":
    main()
