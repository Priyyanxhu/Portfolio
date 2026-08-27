#!/usr/bin/env python3
r"""
Lightweight static server for portfolio + Smart Fog Vision.
- Serves D:/ so both /PriyanshuMLPortfolio/ and /Smart_Fog_Vision/ work from one port (single server, zero config).
  Portfolio: http://localhost:8002/PriyanshuMLPortfolio/  -> also redirects / to portfolio for convenience
  Demo:      http://localhost:8002/Smart_Fog_Vision/
- Gzip compression for text assets (saves ~70% on tailwind.css, html, js)
- Strong caching for assets (1 year), no-cache for HTML
- Threaded, low overhead (~5 MB RAM)
Usage:
  python serve.py            # port 8002, serves D:/
  python serve.py --port 8002 --dir "D:\\"
  # or legacy: python -m http.server 8002 --directory "D:\PriyanshuMLPortfolio"
"""
import argparse
import gzip
import mimetypes
import os
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path("D:/")
PORT = 8002

# compressible types
GZIP_TYPES = (".html", ".css", ".js", ".json", ".svg", ".txt", ".xml", ".map")

class LiteHandler(SimpleHTTPRequestHandler):
    # serve from ROOT, but allow friendly / -> portfolio redirect
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        # Perf + security headers for fastest load
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Vary", "Accept-Encoding")
        # CORS for iframe
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "unsafe-none")
        # cache control — assets immutable, html no-cache, pdf immutable
        path = self.path.split("?")[0].split("#")[0].lower()
        if path.endswith((".css",".js",".woff2",".woff",".png",".jpg",".webp",".svg",".pdf")):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        elif path.endswith(".html") or path.endswith("/"):
            self.send_header("Cache-Control", "public, max-age=0, must-revalidate")
        # Early hints for fastest first paint (Link preload for critical is in HTML, but also header helps)
        if path.endswith("/") or path.endswith("/index.html"):
            self.send_header("Link", '<https://fonts.googleapis.com>; rel=preconnect; crossorigin, <https://smart-fog-vision-sytem.onrender.com>; rel=preconnect, <https://chrono-j9pf.onrender.com>; rel=preconnect')
        super().end_headers()

    def do_GET(self):
        # friendly: / -> /PriyanshuMLPortfolio/ only when serving from D:/ (dev)
        if self.path in ("/", "/index.html"):
            if (ROOT / "PriyanshuMLPortfolio" / "index.html").exists():
                self.path = "/PriyanshuMLPortfolio/"
            else:
                self.path = "/index.html" if (ROOT / "index.html").exists() else self.path
        # normalize /PriyanshuMLPortfolio -> /PriyanshuMLPortfolio/
        if self.path == "/PriyanshuMLPortfolio" and (ROOT / "PriyanshuMLPortfolio").is_dir():
            self.path = "/PriyanshuMLPortfolio/"
        return self._serve_gzip()

    def _serve_gzip(self):
        # resolve file path
        url_path = self.path.split("?")[0].split("#")[0]
        fs_path = (ROOT / url_path.lstrip("/")).resolve()
        try:
            fs_path.relative_to(ROOT.resolve())
        except ValueError:
            self.send_error(403)
            return None
        if fs_path.is_dir():
            # Try to serve index.html/.htm with gzip if present
            for idx in ("index.html", "index.htm"):
                idx_path = fs_path / idx
                if idx_path.is_file():
                    # Temporarily treat as file request for gzip
                    fs_path = idx_path
                    break
            else:
                return SimpleHTTPRequestHandler.do_GET(self)
        accept = self.headers.get("Accept-Encoding", "")
        # try brotli first (better ~15% smaller), fallback gzip
        use_br = "br" in accept
        use_gz = "gzip" in accept
        should_compress = fs_path.suffix.lower() in GZIP_TYPES and fs_path.is_file() and fs_path.stat().st_size > 512
        if should_compress and (use_br or use_gz):
            try:
                data = fs_path.read_bytes()
                enc = None
                comp = None
                if use_br:
                    try:
                        import brotli
                        comp = brotli.compress(data, quality=4)
                        if len(comp) < len(data):
                            enc = "br"
                    except ImportError:
                        pass
                if enc is None and use_gz:
                    comp = gzip.compress(data, compresslevel=6)
                    if len(comp) < len(data):
                        enc = "gzip"
                if enc and comp:
                    ctype = mimetypes.guess_type(str(fs_path))[0] or "application/octet-stream"
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(comp)))
                    self.send_header("Content-Encoding", enc)
                    self.end_headers()
                    self.wfile.write(comp)
                    return None
            except Exception:
                pass
        return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        sys.stdout.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), format % args))

def main():
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--dir", type=str, default=str(ROOT))
    args = ap.parse_args()
    ROOT = Path(args.dir).resolve()
    addr = ("", args.port)
    httpd = ThreadingHTTPServer(addr, LiteHandler)
    print(f"Serving {ROOT} at http://localhost:{args.port}/")
    print(f"  Portfolio : http://localhost:{args.port}/PriyanshuMLPortfolio/  (or http://localhost:{args.port}/ -> redirect)")
    print(f"  Demo      : http://localhost:{args.port}/Smart_Fog_Vision/")
    print("  Gzip: on  |  Cache: assets 1y, html no-cache  |  Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
        httpd.shutdown()

if __name__ == "__main__":
    main()
