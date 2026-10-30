// SVG to PNG with resvg (WASM). The caller passes the compiled module and the font files, so the
// Worker bundles them (pngassets.js) and node tests read them from disk.
import { initWasm, Resvg } from "@resvg/resvg-wasm";

let ready = null;

export async function renderPNG(svg, { wasm, fonts }) {
  if (!ready) ready = initWasm(wasm);
  await ready;
  const r = new Resvg(svg, {
    fitTo: { mode: "width", value: 1200 },
    font: { fontBuffers: fonts, loadSystemFonts: false, defaultFontFamily: "Newsreader" },
  });
  return r.render().asPng();
}
