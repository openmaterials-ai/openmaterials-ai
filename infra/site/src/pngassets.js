// The resvg module and the card fonts, as the Worker bundle carries them (wrangler.jsonc rules).
import wasm from "@resvg/resvg-wasm/index_bg.wasm";
import newsreader from "../fonts/newsreader-latin.ttf";
import monoLatin from "../fonts/jetbrains-mono-latin.ttf";
import monoGreek from "../fonts/jetbrains-mono-greek.ttf";
import dejavu from "../fonts/DejaVuSans.ttf";

export const PNG_ASSETS = { wasm, fonts: [newsreader, monoLatin, monoGreek, dejavu].map((b) => new Uint8Array(b)) };
