#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local live server: serves the report and refreshes data on demand."""
import os, sys, json, glob, subprocess, threading
from urllib.parse import quote
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(KIT, "output")
PORT = int(os.environ.get("RADAR_PORT", "8765"))
LOCK = threading.Lock()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=OUT, **kw)
    def log_message(self, *a):
        pass
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            files = sorted(glob.glob(os.path.join(OUT, "Radar_*.html")), key=os.path.getmtime, reverse=True)
            if files:
                self.send_response(302)
                self.send_header("Location", "/" + quote(os.path.basename(files[0])))
                self.end_headers(); return
        super().do_GET()
    def do_POST(self):
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
            self.end_headers()
            self.wfile.write(json.dumps({"ok": ok, "error": err}, ensure_ascii=False).encode())
        finally:
            LOCK.release()

if __name__ == "__main__":
    print(f"Radar live server: http://127.0.0.1:{PORT}/ (Ctrl+C 退出)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
