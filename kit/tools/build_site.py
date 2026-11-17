#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn the single-file radar report into a static website that search engines can index.

    python3 tools/build_site.py                          # real data, ready to publish
    python3 tools/build_site.py --redact --out site-demo # anonymised public demo
    python3 tools/build_site.py --redact --private       # invitation-only: gate page + hidden report

Output (default ./site):
    index.html   the report + SEO metadata + a crawlable intro/noscript block
    robots.txt   allow indexing, point at the sitemap
    sitemap.xml
    404.html     redirect back to index
    .nojekyll    keep GitHub Pages from running Jekyll
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import re
import secrets
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)


def die(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def split_payload(doc):
    """Return (start, end) offsets of the JSON payload inside `const D = ...;`."""
    marker = "const D = "
    i = doc.find(marker)
    if i < 0:
        die("payload marker 'const D = ' not found - is this a radar report?")
    i += len(marker)
    j = doc.find("\nconst COLORS = ", i)
    if j < 0:
        die("payload end marker not found")
    return i, j


def parse_payload(doc):
    i, j = split_payload(doc)
    raw = doc[i:j].rstrip().rstrip(";")
    return json.loads(raw), i, j


def pseudonym(n):
    return "Student %02d" % n


def split_parts(name):
    """"Dong, Mingyi 董明翊 (Jason)" -> ['Dong','Mingyi','董明翊','Jason']"""
    return [p.strip() for p in re.split(r"[,\s()]+", name or "") if p.strip()]


def transform_strings(obj, fn):
    """Apply fn to every string inside a JSON-like structure."""
    if isinstance(obj, dict):
        return {k: transform_strings(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [transform_strings(v, fn) for v in obj]
    if isinstance(obj, str):
        return fn(obj)
    return obj


def redact(doc, payload, i, j):
    rows = payload.get("rows") or []
    originals = [r.get("name") or "" for r in rows]

    for n, row in enumerate(rows, 1):
        row["_alias"] = "Student %02d" % n

    alias_of = {name: rows[k]["_alias"] for k, name in enumerate(originals)}

    # parts that are distinctive enough to replace anywhere in the document
    strong = sorted({p for name in originals for p in split_parts(name)
                     if (p.isascii() and len(p) >= 4) or (not p.isascii() and len(p) >= 2)},
                    key=len, reverse=True)
    # three-letter given names / nicknames: only rewritten inside free text
    weak = {p for name in originals for p in split_parts(name)
            if p.isascii() and len(p) == 3}
    weak_map = {p: alias_of[name] for name in originals for p in split_parts(name) if p in weak}
    weak_re = re.compile(r"\b(%s)\b" % "|".join(sorted(map(re.escape, weak), key=len, reverse=True))) if weak else None

    def free_text(s):
        if weak_re:
            s = weak_re.sub(lambda m: weak_map.get(m.group(1), m.group(1)), s)
        for p in strong:
            if p in s:
                s = s.replace(p, alias_of.get(next((n for n in originals if p in split_parts(n)), ""), p))
        return s

    for row in rows:
        row["name"] = row.pop("_alias")
        row["parents"] = []
        info = row.get("info") or {}
        for key in ("gender", "birthday", "dormitory", "boarding", "bus", "house", "advisory", "enterDate"):
            info.pop(key, None)
        row["info"] = info
        for key in ("_diary", "lifeBlock", "profileData", "summary", "entries"):
            if key in row:
                row[key] = transform_strings(row[key], free_text)

    sig = payload.get("signature")
    if isinstance(sig, dict):
        sig["phone"] = ""

    body = json.dumps(payload, ensure_ascii=False)
    for name in sorted(alias_of, key=len, reverse=True):
        body = body.replace(name, alias_of[name])
    for part in strong:
        owner = next((n for n in originals if part in split_parts(n)), None)
        if owner:
            body = body.replace(part, alias_of[owner])
    body = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "parent@example.com", body)
    doc = doc[:i] + body + doc[j:]
    # the search hint names two real students
    doc = doc.replace('例如 Jason / 董明翊 / G7-C', '例如 Student 07 / G7-C')
    return doc


FAVICON = ("<link rel=\"icon\" href=\"data:image/svg+xml,"
           "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Ccircle cx='16' cy='16' r='13' fill='none' stroke='%231f4e79' stroke-width='2'/%3E"
           "%3Ccircle cx='16' cy='16' r='7' fill='none' stroke='%231f4e79' stroke-width='1.5'/%3E"
           "%3Cpath d='M16 16 L27 9' stroke='%23c00000' stroke-width='2'/%3E%3C/svg%3E\">")


def seo_head(payload, base_url, demo, private=False):
    teacher = payload.get("teacher") or "Teacher"
    n = len(payload.get("rows") or [])
    courses = payload.get("courses") or []
    desc = ("One-page IntSchool radar report card: per-course achievement radar, task-level drill-down, "
            "weekly insights, missing-work triage, class heat map and parent communication coverage for "
            "%d learners across %d courses." % (n, len(courses)))
    if demo:
        desc += " Anonymised demonstration copy: learner names, parent contacts and personal details are removed."
    title = "Radar Report Card | %s | IntSchool" % teacher
    if demo:
        title += " (demo)"
    canonical = base_url.rstrip("/") + "/"
    ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": desc,
        "url": canonical,
        "inLanguage": ["zh-CN", "en"],
        "author": {"@type": "Person", "name": teacher},
        "about": ["Student assessment", "Gradebook analytics", "IntSchool"],
    }
    tags = [
        '<meta name="description" content="%s">' % html.escape(desc),
        '<meta name="robots" content="%s">' % ("noindex,nofollow,noarchive" if private
                                                 else "index,follow,max-image-preview:large"),
        '<meta name="author" content="%s">' % html.escape(teacher),
        '<meta name="keywords" content="radar report card, IntSchool, gradebook, student progress, '
        'missing work, parent communication, %s">' % html.escape(teacher),
        '<link rel="canonical" href="%s">' % html.escape(canonical),
        FAVICON,
        '<meta property="og:type" content="website">',
        '<meta property="og:title" content="%s">' % html.escape(title),
        '<meta property="og:description" content="%s">' % html.escape(desc),
        '<meta property="og:url" content="%s">' % html.escape(canonical),
        '<meta property="og:site_name" content="Radar on IntSchool">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:title" content="%s">' % html.escape(title),
        '<meta name="twitter:description" content="%s">' % html.escape(desc),
        '<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False),
    ]
    return title, desc, "\n".join(tags)


def intro_block(payload, base_url, demo):
    teacher = html.escape(payload.get("teacher") or "")
    n = len(payload.get("rows") or [])
    courses = payload.get("courses") or []
    rows = payload.get("rows") or []
    classes = sorted({r.get("class", "") for r in rows if r.get("class")})
    gen = payload.get("generated") or ""

    def cls_rows():
        out = []
        for c in classes:
            members = [r for r in rows if r.get("class") == c]
            for r in members:
                out.append(r)
        return out

    listing = "\n".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            html.escape(str(r.get("name", ""))), html.escape(str(r.get("class", ""))),
            html.escape(str(r.get("course", ""))))
        for r in cls_rows()
    )
    banner = ""
    if demo:
        banner = ('<p class="seoWarn"><b>Demo copy.</b> Learner names, parent email addresses, dormitory and '
                  'date-of-birth fields have been removed. Grades are shown only to demonstrate the layout.</p>')
    return """
<section class="seoIntro" id="about">
  <h1>Radar Report Card · %s</h1>
  <p>One page, %d learners, %d courses: a per-course achievement radar, task-by-task drill-down,
  weekly insight, missing-work triage queue, class heat map and parent communication coverage —
  built from the IntSchool gradebook, task detail, student log and attendance data.</p>
  <p>Use the search box on the left to find a learner by name or class, click a radar axis to open that
  course, hover a bar to see the task behind it. Data generated %s.</p>
  %s
  <details><summary>Index of learners on this page</summary>
    <table><thead><tr><th>Learner</th><th>Class</th><th>Course</th></tr></thead><tbody>%s</tbody></table>
  </details>
</section>
<noscript><p class="seoWarn">This report is interactive and needs JavaScript. The learner index above
lists everyone included in it.</p></noscript>
""" % (teacher, n, len(courses), html.escape(str(gen)), banner, listing)


STYLE = """
.seoIntro{background:#f6f8fa;border:1px solid #d0d7de;border-radius:10px;padding:12px 14px;margin:10px 0 14px;line-height:1.6}
.seoIntro h1{font-size:16px;margin:0 0 6px;color:#1f4e79}
.seoIntro p{margin:4px 0;font-size:12px;color:#3d444d}
.seoIntro details{margin-top:8px;font-size:12px}
.seoIntro summary{cursor:pointer;color:#1f4e79;font-weight:600}
.seoIntro table{border-collapse:collapse;width:100%;margin-top:6px;font-size:11.5px}
.seoIntro th,.seoIntro td{border-bottom:1px solid #e3e8ee;padding:3px 6px;text-align:left}
.seoWarn{background:#fff4e5;border:1px solid #ffd591;border-radius:8px;padding:8px 10px;font-size:12px;color:#7a4d00}
"""



GATE_CSS = """
:root{--blue:#1f4e79;--line:#d0d7de}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
 font-family:-apple-system,"PingFang SC","Segoe UI",Arial,sans-serif;background:#f6f8fa;color:#1f2328}
.gate{background:#fff;border:1px solid var(--line);border-top:4px solid var(--blue);border-radius:12px;
 padding:26px 30px;max-width:520px;width:calc(100% - 40px);box-shadow:0 10px 30px rgba(0,0,0,.06)}
h1{font-size:18px;margin:0 0 10px;color:var(--blue)}
p{font-size:13px;line-height:1.6;margin:8px 0}
.en{color:#57606a;font-size:12px}
form{display:flex;gap:8px;margin:16px 0 6px}
input{flex:1;padding:9px 11px;border:1px solid var(--line);border-radius:7px;font-size:14px}
button{padding:9px 16px;border:0;border-radius:7px;background:var(--blue);color:#fff;font-size:14px;cursor:pointer}
.msg{color:#c00000;font-size:12.5px;min-height:18px;margin:4px 0}
.fine{color:#8b949e;font-size:11px;line-height:1.6;margin-top:14px;border-top:1px solid #eaeef2;padding-top:10px}
"""


def gate_page(report_path, hashes):
    return """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>雷达报告卡 · 受邀访问 | Radar Report Card (invitation only)</title>
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="referrer" content="no-referrer">
<style>%s</style></head>
<body>
<main class="gate">
  <h1>雷达报告卡 · 受邀访问</h1>
  <p>这个页面只向收到邀请邮件的家长和同事开放。请直接点击邮件里的个人链接；也可以把邮件中的访问码粘贴到下面。</p>
  <p class="en">This page is invitation-only. Open the personal link in your invitation email,
  or paste the access code from that email below.</p>
  <form id="f" autocomplete="off">
    <input id="k" placeholder="访问码 / access code" spellcheck="false" autocomplete="off">
    <button type="submit">进入 Enter</button>
  </form>
  <p class="msg" id="m"></p>
  <p class="fine">访问码由任课老师单独发放；重新发布后旧访问码可能失效。<br>
  Codes are issued by the teacher individually and may be retired when the page is republished.</p>
</main>
<script>
const H=%s, P=%s;
async function digest(s){
  const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s.trim()));
  return [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');
}
async function unlock(code){
  if(!code) return false;
  try{ if(H.indexOf(await digest(code))>=0){ localStorage.setItem('radar_ok','1'); return true; } }catch(e){}
  return false;
}
(async()=>{
  const q=new URLSearchParams(location.search);
  const k=q.get('k')||q.get('code')||'';
  if(k && await unlock(k)){ location.replace(P); return; }
  try{ if(localStorage.getItem('radar_ok')) location.replace(P); }catch(e){}
})();
document.getElementById('f').addEventListener('submit',async e=>{
  e.preventDefault();
  const m=document.getElementById('m');
  if(await unlock(document.getElementById('k').value)) location.replace(P);
  else m.textContent='访问码无效 / that code is not valid';
});
</script></body></html>""" % (GATE_CSS, json.dumps(hashes), json.dumps(report_path))


def load_invite_hashes():
    path = os.path.join(KIT, "invites.json")
    if not os.path.exists(path):
        return []
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    return [i["hash"] for i in data.get("invites", []) if i.get("hash")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=None, help="report html (default: newest in output/)")
    ap.add_argument("--out", default=os.path.join(KIT, "site"))
    ap.add_argument("--base-url", default="https://tiger20240331.github.io/Intschool")
    ap.add_argument("--redact", action="store_true", help="remove names / parent emails / personal fields")
    ap.add_argument("--private", action="store_true",
                    help="invitation-only: a gate page at the root, report under an unguessable path, no indexing")
    args = ap.parse_args()

    src = args.src
    if not src:
        outdir = os.path.join(KIT, "output")
        cands = [os.path.join(outdir, f) for f in os.listdir(outdir) if f.startswith("Radar_") and f.endswith(".html")]
        if not cands:
            die("no Radar_*.html in output/ - run the collect + render steps first")
        src = max(cands, key=os.path.getmtime)

    doc = open(src, encoding="utf-8").read()
    payload, i, j = parse_payload(doc)
    if args.redact:
        doc = redact(doc, payload, i, j)
        payload, i, j = parse_payload(doc)

    title, desc, head_tags = seo_head(payload, args.base_url, args.redact, args.private)

    # 1. title + head metadata
    doc, n = re.subn(r"<title>[^<]*</title>", "<title>%s</title>" % html.escape(title), doc, count=1)
    if not n:
        die("no <title> to replace")
    doc = doc.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + head_tags, 1)
    doc = doc.replace("</style>", STYLE + "</style>", 1)

    # 2. static-host behaviour: no /refresh, no /outlook-draft bridge
    doc = doc.replace("const D = ", "window.RADAR_STATIC=true;\nconst D = ", 1)
    doc = doc.replace(
        "if(!location.protocol.startsWith('http')) return;",
        "if(!location.protocol.startsWith('http')||window.RADAR_STATIC) return;", 1)
    doc = doc.replace(
        "if(location.protocol.indexOf('http')===0){",
        "if(location.protocol.indexOf('http')===0&&!window.RADAR_STATIC){", 1)

    # 3. crawlable intro above the app shell
    doc = doc.replace('<main>\n  <div id="card"></div>', '<main>\n' + intro_block(payload, args.base_url, args.redact)
                      + '\n  <div id="card"></div>', 1)

    os.makedirs(args.out, exist_ok=True)
    base = args.base_url.rstrip("/") + "/"

    if args.private:
        hashes = load_invite_hashes()
        if not hashes:
            die("private mode needs invitations - run: python3 tools/make_invites.py")
        report_dir = "p-" + secrets.token_hex(8)
        os.makedirs(os.path.join(args.out, report_dir), exist_ok=True)
        open(os.path.join(args.out, report_dir, "index.html"), "w", encoding="utf-8").write(doc)
        open(os.path.join(args.out, "index.html"), "w", encoding="utf-8").write(
            gate_page(report_dir + "/", hashes))
        open(os.path.join(args.out, "robots.txt"), "w", encoding="utf-8").write(
            "User-agent: *\nDisallow: /\n")
        open(os.path.join(args.out, ".nojekyll"), "w").write("")
        open(os.path.join(args.out, "404.html"), "w", encoding="utf-8").write(
            '<!doctype html><meta charset="utf-8"><title>Redirecting</title>'
            '<meta http-equiv="refresh" content="0;url=/"><p>Redirecting…</p>')
        print("site   :", args.out)
        print("source :", src)
        print("mode   : private - %d access codes, report at %s" % (len(hashes), report_dir))
        print("gate   :", base)
        print("redact :", "yes - names and personal data removed" if args.redact else "no - real data")
        return

    open(os.path.join(args.out, "index.html"), "w", encoding="utf-8").write(doc)

    open(os.path.join(args.out, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n" % base)
    today = datetime.date.today().isoformat()
    open(os.path.join(args.out, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>daily</changefreq>"
        "<priority>1.0</priority></url>\n</urlset>\n" % (base, today))
    open(os.path.join(args.out, ".nojekyll"), "w").write("")
    keyfile = os.path.join(KIT, "indexnow.key")
    if os.path.exists(keyfile):
        key = open(keyfile, encoding="utf-8").read().strip()
        if key:
            open(os.path.join(args.out, key + ".txt"), "w").write(key)
    open(os.path.join(args.out, "404.html"), "w", encoding="utf-8").write(
        '<!doctype html><meta charset="utf-8"><title>Redirecting</title>'
        '<meta http-equiv="refresh" content="0;url=/"><p>Redirecting to the report…</p>')

    size = os.path.getsize(os.path.join(args.out, "index.html"))
    print("site   :", args.out)
    print("source :", src)
    print("title  :", title)
    print("pages  : index.html (%.1f MB) + robots.txt + sitemap.xml + 404.html" % (size / 1e6))
    print("redact :", "yes - names and personal data removed" if args.redact else "no - real data")
    print("url    :", base)


if __name__ == "__main__":
    main()
