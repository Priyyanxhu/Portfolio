#!/usr/bin/env python3
"""
Production build for recruiter-ready portfolio
- Creates dist/ folder (self-contained, ready to deploy to Vercel/Netlify/GitHub Pages)
- Copies index.html + assets (resume, lucide-lite, tailwind inlined already)
- Bundles Smart_Fog_Vision as dist/Smart_Fog_Vision/ so ../Smart_Fog_Vision/ links work OR as dist/demo/
- Fixes paths for root deployment (ensures relative links work from dist/)
- Adds vercel.json, netlify.toml, robots.txt, sitemap.xml, .nojekyll
- Minifies HTML slightly (remove comments, collapse whitespace where safe) — keeps readability
- Prints deploy instructions and file sizes
"""
import pathlib, shutil, re, gzip, json

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"
SRC_HTML = ROOT / "index.html"
ASSETS = ROOT / "assets"
SMART_SRC = pathlib.Path(r"D:\Smart_Fog_Vision")

# Clean dist
def rm(p):
    import stat, os
    def onexc(func, path, exc):
        try: os.chmod(path, stat.S_IWRITE); func(path)
        except: pass
    shutil.rmtree(p, onexc=onexc)
if DIST.exists():
    rm(DIST)
DIST.mkdir(parents=True)
(ASSETS / "resume.pdf").exists() or print("WARN resume.pdf missing")
print(f"Building production to {DIST}")

# 1. Copy index.html (already has inlined tailwind, so self-contained)
html = SRC_HTML.read_text(encoding="utf-8")

# For production at root, assets are relative (assets/...) so fine.
# Smart Fog Vision live demo is now at https://smart-fog-vision-sytem.onrender.com — keep external, no path rewrite needed
# Keep bundled ./Smart_Fog_Vision/ as offline fallback, but primary live is external
html_prod = html  # already points to https://smart-fog-vision-sytem.onrender.com in source
# Also fix the code snippet that shows python -m http.server --directory "D:\\Smart_Fog_Vision" to be more generic for prod
# Keep as is for docs

# Add production meta: og, twitter, canonical, etc. Inject before </head> if not present
if 'property="og:title"' not in html_prod:
    og = '''
  <meta property="og:title" content="Priyanshu Pandey — Freelance Developer | Android Apps • Websites • AI/ML Models & Training"/>
  <meta property="og:description" content="Freelance developer building Android apps (Kotlin/Compose), websites (React/FastAPI) & AIML models with full training. Creator of J.A.R.V.I.S. Android (3200 LOC, bilingual), Smart Fog Vision (YOLOv8 + DCP, 100% in-browser) & Chrono (FaceNet, 90%+). Available for hire."/>
  <meta property="og:type" content="website"/>
  <meta property="og:url" content="https://priyanshupandey.ai"/>
  <meta property="og:image" content="https://priyanshupandey.ai/og-image.png"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="Priyanshu Pandey — Freelance Developer | Android • Web • AIML"/>
  <meta name="twitter:description" content="Android • Websites • AIML with full training — 15+ projects shipped, Play Store ready, ONNX/TF Lite"/>
  <link rel="canonical" href="https://priyanshupandey.ai/"/>
'''
    html_prod = html_prod.replace("</head>", og + "\n</head>")

# Minify for fastest load: remove HTML comments, collapse whitespace between tags (keep readability in source, minify only dist)
# Keep conditional comments and preserve <style>/<script> content
orig_len = len(html_prod)
# Remove HTML comments (except conditional) — saves ~2KB without affecting render
html_prod = re.sub(r'<!--(?!\[).*?-->', '', html_prod, flags=re.S)
# Collapse multiple blank lines
html_prod = re.sub(r'\n\s*\n', '\n', html_prod)
html_prod = html_prod.strip()
print(f"  Minified {orig_len} -> {len(html_prod)} bytes (saved {orig_len-len(html_prod)})")
(DIST / "index.html").write_text(html_prod, encoding="utf-8")
print(f"  index.html -> {len(html_prod)} bytes (gzip {len(gzip.compress(html_prod.encode()))} bytes)")

# 2. Copy assets (resume, lucide-lite, tailwind.css, input.css etc) — but html already inlined, still copy for completeness
shutil.copytree(ASSETS, DIST / "assets")
print(f"  assets/ -> {len(list((DIST/'assets').glob('*')))} files")

# 3. Bundle Smart_Fog_Vision (offline fallback, live is https://smart-fog-vision-sytem.onrender.com)
if SMART_SRC.exists():
    dest = DIST / "Smart_Fog_Vision"
    shutil.copytree(SMART_SRC, dest, ignore=shutil.ignore_patterns('.git', '.git*', '__pycache__', '*.pyc', 'node_modules'))
    # Ensure .git removed even if ignore failed
    shutil.rmtree(dest / ".git", ignore_errors=True)
    print(f"  Smart_Fog_Vision/ -> {len(list(dest.glob('*')))} files")
else:
    print("  WARN Smart_Fog_Vision source not found, skipping bundle")

# 4. Add deployment configs
( DIST / ".nojekyll").write_text("", encoding="utf-8")

vercel = {
  "version": 2,
  "public": True,
  "headers": [
    {"source": "/assets/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]},
    {"source": "/Smart_Fog_Vision/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]},
    {"source": "/(.*).html", "headers": [{"key": "Cache-Control", "value": "public, max-age=0, must-revalidate"}]}
  ],
  "rewrites": [{"source": "/(.*)", "destination": "/index.html"}]
}
(DIST / "vercel.json").write_text(json.dumps(vercel, indent=2), encoding="utf-8")

netlify = """[build]
  publish = "."
  command = "echo 'no build'"

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/Smart_Fog_Vision/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
"""
(DIST / "netlify.toml").write_text(netlify, encoding="utf-8")

robots = """User-agent: *
Allow: /
Sitemap: https://priyanshupandey.ai/sitemap.xml
"""
(DIST / "robots.txt").write_text(robots, encoding="utf-8")

sitemap = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://schemas.xmlsoap.org/sitemap/0.9">
  <url><loc>https://priyanshupandey.ai/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
  <url><loc>https://priyanshupandey.ai/#projects</loc><priority>1.0</priority></url>
  <url><loc>https://priyanshupandey.ai/#skills</loc><priority>0.95</priority></url>
  <url><loc>https://priyanshupandey.ai/#experience</loc><priority>0.9</priority></url>
  <url><loc>https://smart-fog-vision-sytem.onrender.com</loc><priority>0.9</priority></url>
  <url><loc>https://priyanshupandey.ai/Smart_Fog_Vision/</loc><priority>0.7</priority></url>
  <url><loc>https://chrono-j9pf.onrender.com</loc><priority>0.8</priority></url>
</urlset>
"""
(DIST / "sitemap.xml").write_text(sitemap, encoding="utf-8")

# 5. Add README for recruiter
readme = """# Priyanshu Pandey — Portfolio (Production Build) — Freelance: Android • Web • AIML

**Live Demos:** J.A.R.V.I.S. Android (D:\\Jarvis, Kotlin/Compose, bilingual) | Smart Fog Vision → https://smart-fog-vision-sytem.onrender.com | Chrono → https://chrono-j9pf.onrender.com
**Freelance:** Android apps (Kotlin/Compose) • Websites (React/FastAPI) • AIML models with full training (PyTorch→ONNX/TF Lite) — available for hire.

This `dist/` folder is production-ready. Upload to any static host.

## Quick Deploy (choose one)

**Vercel (recommended, 30s):**
```bash
npx vercel --prod
# or drag dist/ to https://vercel.com/new
```
**Netlify:**
- Drag `dist/` to https://app.netlify.com/drop
- or `npx netlify deploy --prod --dir dist`

**GitHub Pages:**
```bash
git checkout -b gh-pages
git add dist -f && git commit -m "deploy"
git subtree push --prefix dist origin gh-pages
```

**Any static server:**
```bash
npx serve dist
# or python -m http.server --directory dist 8002
```

## What's inside
- `index.html` — single file with inlined Tailwind (36KB, gzip 27KB), 90% lighter than CDN
- `assets/resume.pdf` — Priyanshu Pandey resume (view on Resume click)
- `assets/lucide-lite.js` — 46 icons only (9KB, gzip 3KB)
- `Smart_Fog_Vision/` — bundled so ./Smart_Fog_Vision/ works in production (no sibling-folder issue)
- `Chrono` live at https://chrono-j9pf.onrender.com (Render, cold start ~30s)

## For Recruiters
- Email: pandeyshreyansh0204@gmail.com
- Resume: click **Resume** → `assets/resume.pdf`
- Live Demos: **Smart Fog Vision** (in-browser YOLOv8 + DCP) & **Chrono** (FaceNet + Spring Boot, 90%+)
- This build is fully static, no API keys, no server required.

Generated: automated build-prod.py
"""
(DIST / "README.md").write_text(readme, encoding="utf-8")

# Print sizes
total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
print(f"Total dist size: {total} bytes ({total/1024:.1f} KB)")
for f in sorted(DIST.rglob("*")):
    if f.is_file():
        rel = f.relative_to(DIST)
        print(f"  {rel} — {f.stat().st_size} bytes")
print("\nDone. To preview locally:")
print("  npx serve dist")
print("  python -m http.server 8003 --directory dist")
print("Then open http://localhost:8003")
