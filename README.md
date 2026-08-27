# Priyanshu Pandey — AI Engineer Portfolio

Live: `http://localhost:8002/` → `http://localhost:8002/PriyanshuMLPortfolio/` (portfolio) + `http://localhost:8002/Smart_Fog_Vision/` (demo) — **single lite server**

## Run — one command, very light

```powershell
# Recommended: lite server (gzip + cache + single port for both)
python serve.py
# open http://localhost:8002/  (auto-redirects to portfolio)
# Demo at http://localhost:8002/Smart_Fog_Vision/ — iframe loads on scroll (saves initial ~200KB)

# Or double-click:
#   run.bat  or  run.ps1

# Legacy (two servers, heavier):
python -m http.server 8002 --directory "D:\PriyanshuMLPortfolio"
python -m http.server 8001 --directory "D:\Smart_Fog_Vision"
```

**Lightness:** `89% smaller` — Tailwind `407KB → 27KB` (purged + inlined), `lucide 419KB → 9KB` (lite, 46 icons, `gzip 3.1KB`), `GSAP 115KB → 0` (replaced with `IntersectionObserver` + CSS), fonts trimmed `8→4` weights + `media=print` async, iframe lazy until viewport, `content-visibility:auto`, `gzip` + `Cache-Control: immutable` via `serve.py`. Total transferred `~22KB HTML + 3KB icons` gzipped vs `~250KB` before. Runs at `~5MB RAM`, `http://localhost:8002/?lite=1` forces lite (no blur).

## Build (optional)
```powershell
npm run build:css   # rebuild assets/tailwind.css + inlines into index.html (needs node_modules)
npm run build:prod  # creates dist/ — recruiter-ready, self-contained, 71KB ZIP
npm run dev         # same as python serve.py but via npm
# After building, you can delete node_modules/ (~27MB) — not needed at runtime.
```

## For Recruiters — One-Click Deploy

**Production build ready:** `dist/` (270KB uncompressed, 71KB ZIP) + `Priyanshu_Pandey_Portfolio_For_Recruiters.zip`

| Method | Command |
|--------|---------|
| **Preview locally** | `python -m http.server 8003 --directory dist` → http://localhost:8003 |
| **Vercel** | `npx vercel --prod` or drag `dist/` to https://vercel.com/new |
| **Netlify** | Drag `dist/` to https://app.netlify.com/drop |
| **GitHub Pages** | `git subtree push --prefix dist origin gh-pages` |
| **ZIP** | Send `Priyanshu_Pandey_Portfolio_For_Recruiters.zip` — unzip & double-click `index.html` (works offline) |

`dist/` contains:
- `index.html` (inlined Tailwind 36KB, gzip 27KB) + `assets/resume.pdf` (Resume click) + `assets/lucide-lite.js` (9KB)
- `Smart_Fog_Vision/` bundled so `./Smart_Fog_Vision/` works at root (no sibling-folder issue)
- `Chrono` live at https://chrono-j9pf.onrender.com (Render) + `vercel.json`/`netlify.toml`/`robots.txt`/`sitemap.xml`

**Contacts for recruiters:** `pandeyshreyansh0204@gmail.com` | [Resume](assets/resume.pdf) | [GitHub](https://github.com/Priyyanxhu) | [LinkedIn](https://www.linkedin.com/in/priyanshu-pandey-8b8160287) | Live demos: **Smart Fog Vision** → https://smart-fog-vision-sytem.onrender.com & **Chrono** → https://chrono-j9pf.onrender.com

## What’s inside
- Hero as AI Engineer (CV • LLMs • MLOps) — enhanced with gradient orb, glass nav, scroll progress
- Featured: **Smart Fog Vision** + **Chrono (ZYNC) — AI Missing Person** — both embedded iframe + deep dive
- Projects grid (RAG, U-Net, ForecastX, Kavach, StyleForge, Traffic Analytics)
- Skills: ML, DL, CV, NLP/GenAI, MLOps, mobile
- Experience/Education + About + Contact (mailto: pandeyshreyansh0204@gmail.com)

## Customise
- Email: `pandeyshreyansh0204@gmail.com` (all mailto updated)
- Resume: `assets/resume.pdf` (click any **Resume** → PDF)
- Links: GitHub `Priyyanxhu` / LinkedIn `priyanshu-pandey-8b8160287` / Chrono `https://chrono-j9pf.onrender.com`
- Theme: toggle persists in `localStorage.theme`

## Smart Fog Vision — **Live:** https://smart-fog-vision-sytem.onrender.com
File: `D:\Smart_Fog_Vision/` — bundled into `dist/Smart_Fog_Vision/` for offline. Production iframe now uses **Live Render** `https://smart-fog-vision-sytem.onrender.com` (all 9 demo buttons/links). Local fallback: `../Smart_Fog_Vision/` or `http://localhost:8002/Smart_Fog_Vision/`. See its own `README.md`.

© 2026 Priyanshu Pandey — Built lite (89% smaller) & premium UI for recruiters.
