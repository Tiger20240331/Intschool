#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Submit the published site to IndexNow (Bing, Yandex, Naver, Seznam).

    python3 tools/indexnow.py --site https://tiger20240331.github.io/Intschool

Google has no open ping endpoint any more - use Search Console once and it will
re-crawl from the sitemap on its own.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="https://tiger20240331.github.io/Intschool")
    ap.add_argument("--endpoint", default="https://api.indexnow.org/indexnow")
    args = ap.parse_args()

    keyfile = os.path.join(KIT, "indexnow.key")
    if not os.path.exists(keyfile):
        sys.exit("no indexnow.key - run build_site.py once to generate it")
    key = open(keyfile, encoding="utf-8").read().strip()

    base = args.site.rstrip("/")
    host = base.split("//", 1)[1].split("/")[0]
    body = {
        "host": host,
        "key": key,
        "keyLocation": "%s/%s.txt" % (base, key),
        "urlList": [base + "/", base + "/robots.txt"],
    }
    req = urllib.request.Request(
        args.endpoint, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "radar-on-intschool"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("indexnow:", r.status, r.read().decode()[:200] or "(accepted)")
    except urllib.error.HTTPError as e:
        print("indexnow:", e.code, e.read().decode()[:300])


if __name__ == "__main__":
    main()
