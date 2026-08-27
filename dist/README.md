# Priyanshu Pandey — Portfolio (Production Build)

**Live Demos:** Smart Fog Vision → https://smart-fog-vision-sytem.onrender.com | Chrono → https://chrono-j9pf.onrender.com

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
