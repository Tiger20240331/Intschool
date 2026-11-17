#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mint one access code per invited parent, for the invitation-only web page.

    python3 tools/make_invites.py --base-url https://tiger20240331.github.io/Intschool
    python3 tools/make_invites.py --reset          # retire every old code and start again

Writes:
    invites.json   token + sha256 + who it was issued to (kept local, never published)
    invites.csv    one row per parent: email, learner, class, personal link
    invites_email.txt  bilingual invitation email with the link placeholder filled per row

Existing codes are kept when you re-run, so links already sent keep working.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import secrets
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
INVITES = os.path.join(KIT, "invites.json")
OUTDIR = os.path.join(KIT, "output")

EMAIL_TEMPLATE = """Subject: 学生雷达报告卡（演示版）· Radar report card preview

Dear Parent / Guardian of {student},

I am sharing a preview of the class radar report card I now use for {class}. The page is a
demonstration copy: learner names have been replaced with "Student 01", "Student 02" and so on,
and no family contact details appear on it.

Open your personal link (please do not forward it):

{link}

The page needs about a minute to load the first time. If the link asks for an access code, paste
this one: {token}

--
家长您好：

我把自己在用的班级雷达报告卡做成预览版分享给您。这一版是演示版：学生姓名已替换为
"Student 01""Student 02"，页面上也不含任何家庭联系方式。

请打开您的个人链接（请勿转发）：

{link}

首次打开大约需要一分钟加载。如果页面要求输入访问码，请粘贴：{token}

祝好，
{signature_name}, {signature_title}
{signature_phone}
"""


def sha(token):
    return hashlib.sha256(token.strip().encode()).hexdigest()


def load_rows():
    """Learner names and parent addresses, read from the newest rendered report."""
    if not os.path.isdir(OUTDIR):
        sys.exit("no output/ folder - run the collect and render steps first")
    cands = [os.path.join(OUTDIR, f) for f in os.listdir(OUTDIR)
             if f.startswith("Radar_") and f.endswith(".html")]
    if not cands:
        sys.exit("no Radar_*.html in output/ - run the collect and render steps first")
    doc = open(max(cands, key=os.path.getmtime), encoding="utf-8").read()
    i = doc.find("const D = ")
    j = doc.find("\nconst COLORS = ")
    if i < 0 or j < 0:
        sys.exit("cannot find the data payload in the report")
    payload = json.loads(doc[i + len("const D = "):j].rstrip().rstrip(";"))
    return payload.get("rows") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://tiger20240331.github.io/Intschool")
    ap.add_argument("--reset", action="store_true", help="discard existing codes")
    ap.add_argument("--no-teacher", action="store_true", help="skip the teacher's own code")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    students = load_rows()

    old = {}
    if os.path.exists(INVITES) and not args.reset:
        try:
            for inv in json.load(open(INVITES, encoding="utf-8")).get("invites", []):
                old[(inv.get("email") or "").lower()] = inv
        except Exception:
            old = {}

    invites, seen = [], set()
    for st in students:
        emails = [e for e in (st.get("parents") or []) if e]
        for email in emails:
            key = email.lower()
            if key in seen:
                continue
            seen.add(key)
            prev = old.get(key)
            token = prev["token"] if prev else secrets.token_hex(6)
            invites.append({
                "token": token,
                "hash": sha(token),
                "email": email,
                "student": st.get("name", ""),
                "class": st.get("class", ""),
                "issued": (prev or {}).get("issued") or datetime.date.today().isoformat(),
            })

    if not args.no_teacher:
        cfg = {}
        cfgpath = os.path.join(KIT, "config.json")
        if os.path.exists(cfgpath):
            cfg = json.load(open(cfgpath, encoding="utf-8"))
        teacher_email = cfg.get("publish_owner_email") or "teacher"
        prev = old.get(teacher_email.lower())
        token = prev["token"] if prev else secrets.token_hex(6)
        invites.append({"token": token, "hash": sha(token), "email": teacher_email,
                        "student": "（老师本人 / teacher）", "class": "",
                        "issued": (prev or {}).get("issued") or datetime.date.today().isoformat()})

    payload = {"created": datetime.datetime.now().isoformat(timespec="seconds"),
               "base_url": base, "invites": invites}
    json.dump(payload, open(INVITES, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.chmod(INVITES, 0o600)

    with open(os.path.join(KIT, "invites.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["email", "student", "class", "link", "code"])
        for inv in invites:
            w.writerow([inv["email"], inv["student"], inv["class"],
                        "%s/?k=%s" % (base, inv["token"]), inv["token"]])

    cfgpath = os.path.join(KIT, "config.json")
    cfg = json.load(open(cfgpath, encoding="utf-8")) if os.path.exists(cfgpath) else {}
    open(os.path.join(KIT, "invites_email.txt"), "w", encoding="utf-8").write(
        EMAIL_TEMPLATE.format(student="{student}", **{"class": "{class}"},
                              link="%s/?k={token}" % base, token="{token}",
                              signature_name=cfg.get("signature_name", ""),
                              signature_title=cfg.get("signature_title", ""),
                              signature_phone=cfg.get("signature_phone", "")))

    print("invites  :", len(invites), "(%d codes)" % len({i['hash'] for i in invites}))
    print("file     :", INVITES)
    print("csv      :", os.path.join(KIT, "invites.csv"))
    print("sample   :", "%s/?k=%s" % (base, invites[0]["token"]))
    if args.reset:
        print("note     : --reset retired every previously issued code")


if __name__ == "__main__":
    main()
