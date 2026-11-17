#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local / LAN live server: serves the report, refreshes on demand, and can post drafts to Outlook.

  python3 tools/serve.py                     # this Mac only: http://127.0.0.1:8765/
  RADAR_HOST=0.0.0.0 RADAR_CODE=abc123 python3 tools/serve.py   # same Wi-Fi colleagues
"""
import os, sys, json, glob, socket, subprocess, threading
from urllib.parse import quote, urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(KIT, "output")
HOST = os.environ.get("RADAR_HOST", "127.0.0.1")
PORT = int(os.environ.get("RADAR_PORT", "8765"))
CODE = (os.environ.get("RADAR_CODE") or "").strip()
LOCK = threading.Lock()


def lan_addresses():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ips.add(s.getsockname()[0]); s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."): ips.add(ip)
    except Exception:
        pass
    return sorted(ips)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=OUT, **kw)

    def log_message(self, *a):
        pass

    def _cookie_ok(self):
        return ("radar_code=" + CODE) in (self.headers.get("Cookie") or "")

    def _authorized(self):
        if not CODE:
            return True
        return self._cookie_ok() or parse_qs(urlparse(self.path).query).get("code", [""])[0] == CODE

    def _deny(self):
        self.send_response(401)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(("需要访问码：在链接后加 ?code=你的码\n").encode())

    def do_GET(self):
        if not self._authorized():
            self._deny(); return
        # first visit with ?code= sets a cookie and cleans the URL
        if CODE and not self._cookie_ok():
            q = parse_qs(urlparse(self.path).query)
            if q.get("code", [""])[0] == CODE:
                path = urlparse(self.path).path
                self.send_response(302)
                self.send_header("Location", path or "/")
                self.send_header("Set-Cookie", f"radar_code={CODE}; Path=/; HttpOnly; SameSite=Lax")
                self.end_headers(); return
        if self.path in ("/", "/index.html"):
            files = sorted(glob.glob(os.path.join(OUT, "Radar_*.html")), key=os.path.getmtime, reverse=True)
            if files:
                self.send_response(302)
                self.send_header("Location", "/" + quote(os.path.basename(files[0])))
                self.end_headers(); return
        super().do_GET()

    def do_POST(self):
        if not self._authorized():
            self._deny(); return
        if self.path == "/outlook-draft":
            try:
                n = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(min(n, 200000)) or b"{}")
                r = subprocess.run([sys.executable, os.path.join(KIT, "tools", "outlook_draft.py")],
                                   input=json.dumps(payload, ensure_ascii=False),
                                   capture_output=True, text=True, timeout=60)
                out = (r.stdout or "").strip() or json.dumps({"ok": False, "error": (r.stderr or "no output")[-300:]})
                self.send_response(200 if '"ok": true' in out else 500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers(); self.wfile.write(out.encode())
            except Exception as e:
                self.send_response(500); self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers(); self.wfile.write(json.dumps({"ok": False, "error": str(e)[:300]}).encode())
            return
        if self.path != "/refresh":
            self.send_response(404); self.end_headers(); return
        if not LOCK.acquire(blocking=False):
            self.send_response(409); self.end_headers(); return
        try:
            ok = True; err = ""
            for script in ["collect.py", "render_radar.py"]:
                r = subprocess.run([sys.executable, os.path.join(KIT, "tools", script)],
                                   cwd=KIT, capture_output=True, text=True, timeout=900)
                if r.returncode != 0:
                    ok = False; err = (r.stderr or r.stdout)[-800:]; break
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers(); self.wfile.write(json.dumps({"ok": ok, "error": err}, ensure_ascii=False).encode())
        finally:
            LOCK.release()


if __name__ == "__main__":
    print(f"Radar live server on {HOST}:{PORT}  (Ctrl+C 退出)")
    if HOST in ("0.0.0.0", "::"):
        for ip in lan_addresses():
            print(f"  同一 Wi-Fi 打开： http://{ip}:{PORT}/" + (f"?code={CODE}" if CODE else ""))
        if CODE:
            print(f"  访问码：{CODE}（只发给要分享的人；换一个码重启即可失效）")
    else:
        print(f"  本机打开： http://127.0.0.1:{PORT}/" + (f"?code={CODE}" if CODE else ""))
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
