# Vendored assets

Every third-party asset the public site depends on is committed here so the
site loads no third-party files at runtime (the map-lab prototypes still
load KaTeX and dagre from jsDelivr). Downloaded from the official
jsDelivr npm CDN and Google Fonts at build time. Licenses: THIRD_PARTY_NOTICES
at the repository root and the texts in LICENSES/.

| Asset | Version | Files | Source |
| --- | --- | --- | --- |
| KaTeX | 0.16.9 | `katex/dist/katex.min.js`, `katex/dist/katex.min.css`, `katex/dist/contrib/auto-render.min.js`, `katex/dist/fonts/*.woff2` (20) | `cdn.jsdelivr.net/npm/katex@0.16.9/dist/` |
| dagre | 0.8.5 | `dagre.min.js` | `cdn.jsdelivr.net/npm/dagre@0.8.5/dist/dagre.min.js` |
| 3d-force-graph | 1.80.0 | `3d-force-graph/3d-force-graph.min.js` (~1.28 MB) | `cdn.jsdelivr.net/npm/3d-force-graph@1.80.0/dist/3d-force-graph.min.js` |
| pdf.js (pdfjs-dist) | 4.10.38 | `pdfjs/pdf.min.mjs`, `pdfjs/pdf.worker.min.mjs` | `cdn.jsdelivr.net/npm/pdfjs-dist@4/build/` |
| Newsreader, JetBrains Mono | Google Fonts, 2026-10-15 (Newsreader v26, JetBrains Mono v24) | `../fonts/newsreader-latin.woff2` (131,848 bytes), `../fonts/jetbrains-mono-latin.woff2` (40,480 bytes), `../fonts/jetbrains-mono-greek.woff2` (9,084 bytes), `../fonts/OFL-Newsreader.txt`, `../fonts/OFL-JetBrainsMono.txt` | fonts.gstatic.com latin and greek subsets of github.com/productiontype/Newsreader and github.com/JetBrains/JetBrainsMono (OFL 1.1) |

## Modifications made for self-containment

- **KaTeX CSS**: the `@font-face` `src` lists were trimmed to the `.woff2`
  format only (the `.woff` and `.ttf` fallbacks were dropped, and those files
  are not vendored). Every current browser supports woff2. 20 woff2 faces are
  vendored under `katex/dist/fonts/`. The files keep the canonical npm `dist/`
  layout (`dist/katex.min.js`, `dist/katex.min.css`, `dist/contrib/auto-render.min.js`,
  `dist/fonts/`).
- **3d-force-graph**: the official jsDelivr `dist/3d-force-graph.min.js` UMD
  bundle. It embeds its own copy of three.js (the WebGL renderer, cameras, and
  sprite/canvas-texture classes are all inside), so the 3D map page needs only
  this one file, no separate three vendoring. The bundle exposes a single
  `ForceGraph3D` global and does not re-export `THREE`; the 3D map page therefore
  encodes node symbols with the library's built-in `nodeLabel` hover overlay
  (plain-string, KaTeX-free) rather than custom three text sprites, keeping the
  page to this one script with zero external fetches.

Total committed vendored size: ~3.9 MB (3d-force-graph ~1.28 MB), license texts included.
