#!/usr/bin/env python3
"""Rebuild purged Tailwind and inline into index.html (lite)."""
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).parent
css_in = ROOT / "assets" / "input.css"
css_out = ROOT / "assets" / "tailwind.css"
html = ROOT / "index.html"

# 1. build tailwind
print("Building tailwind.css...")
import shutil, os
tw = shutil.which("tailwindcss") or str(ROOT / "node_modules" / ".bin" / "tailwindcss")
# on Windows the bin is tailwindcss.ps1 / tailwindcss.cmd, use npx
if os.name == "nt":
    cmd = ["npx", "tailwindcss", "-i", str(css_in), "-o", str(css_out), "--minify"]
else:
    cmd = [tw, "-i", str(css_in), "-o", str(css_out), "--minify"]
proc = subprocess.run(cmd, capture_output=True, text=True, shell=(os.name=="nt"))
print(proc.stdout)
if proc.returncode != 0:
    print(proc.stderr)
    sys.exit(proc.returncode)
print(f"  -> {css_out.stat().st_size} bytes")

# 2. inline into html
css = css_out.read_text(encoding="utf-8")
h = html.read_text(encoding="utf-8")
old = '<link rel="preload" href="assets/tailwind.css" as="style">\n<link rel="stylesheet" href="assets/tailwind.css">'
new = f'<style id="tailwind-lite">\n{css}\n</style>'
if old in h:
    h = h.replace(old, new)
    print("Inlined tailwind.css into index.html")
else:
    # already inlined? replace existing style
    import re
    h = re.sub(r'<style id="tailwind-lite">.*?</style>', new, h, flags=re.S)
    print("Re-inlined existing tailwind-lite")

# ensure lucide lite
if 'lucide@0.511.0' in h:
    h = h.replace('<script src="https://unpkg.com/lucide@0.511.0/dist/umd/lucide.min.js" defer></script>', '<script src="assets/lucide-lite.js" defer></script>')
    print("Switched to lucide-lite.js")
elif 'lucide@latest' in h:
    h = h.replace('<script src="https://unpkg.com/lucide@latest"></script>', '<script src="assets/lucide-lite.js" defer></script>')

html.write_text(h, encoding="utf-8")
print(f"  -> {html.stat().st_size} bytes html")
import gzip
print(f"  gzip html {len(gzip.compress(h.encode()))} bytes, css {len(gzip.compress(css.encode()))} bytes")
print("Done. You can now run: python serve.py")
