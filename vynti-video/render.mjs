// Rendu image par image de scene.html (Chromium headless) puis encodage ffmpeg.
//
//   node render.mjs --stills 1.2,8.5,15 [--scale 2]   -> out/stills/*.png (aperçus)
//   node render.mjs --cues                            -> out/cues.json (feuille de bruitages)
//   node render.mjs --video [--fps 60] [--workers 3] [--scale 2] [--mb 12] [--from 0 --to 60] [--out video-noaudio.mp4]
//                                                     -> out/video-noaudio.mp4 + out/cues.json
//
// --scale 2 : la page est rendue à 2 pixels par pixel CSS, capture 3840 × 2160 (4K UHD).
// Flou de mouvement : sur les plans que la scène marque (window.mbAt), chaque image est la
// moyenne de sous-images réparties sur un obturateur à 180° centré sur l'instant de l'image :
// --mb sous-images sur les raccords, la moitié sur les mouvements rapides, aucune ailleurs.
// La moyenne est faite par avg.py, qui envoie des images RVB brutes à ffmpeg.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch {
  playwright = require(path.join(process.execPath, '../../lib/node_modules/playwright'));
}

const DIR = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(DIR, 'out');
fs.mkdirSync(OUT, { recursive: true });
const URL_SCENE = pathToFileURL(path.join(DIR, 'scene.html')).href;

const args = process.argv.slice(2);
const arg = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const SCALE = +arg('--scale', 1);
const W = 1920 * SCALE, H = 1080 * SCALE;

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: SCALE });
  page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto(URL_SCENE);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 120000 });
  const cdp = await page.context().newCDPSession(page);
  // capture à la pleine définition (le clip à l'échelle 2 donne les vrais 3840 × 2160)
  const shot = async (format = 'jpeg') => Buffer.from((await cdp.send('Page.captureScreenshot', {
    format, ...(format === 'jpeg' ? { quality: 96 } : {}), optimizeForSpeed: true,
    clip: { x: 0, y: 0, width: 1920, height: 1080, scale: SCALE },
  })).data, 'base64');
  return { page, shot };
}

const launch = () => playwright.chromium.launch({
  args: ['--force-color-profile=srgb', '--hide-scrollbars', '--font-render-hinting=none', '--disable-lcd-text'],
});

async function stills(times) {
  const browser = await launch();
  const { page, shot } = await openPage(browser);
  const dir = path.join(OUT, 'stills');
  fs.mkdirSync(dir, { recursive: true });
  for (const t of times) {
    await page.evaluate(t => window.renderFrame(t), t);
    const f = path.join(dir, `t${t.toFixed(2).padStart(6, '0')}${SCALE > 1 ? '@' + SCALE + 'x' : ''}.png`);
    fs.writeFileSync(f, await shot('png'));
    console.log(f);
  }
  await browser.close();
}

async function worker(id, frames, fps, K) {
  const browser = await launch();
  const { page, shot } = await openPage(browser);
  const seg = path.join(OUT, `seg${id}.mp4`);
  const py = spawn('python3', [path.join(DIR, 'avg.py')], { stdio: ['pipe', 'pipe', 'inherit'] });
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', `${W}x${H}`, '-r', String(fps), '-i', '-',
    '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '10', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
    seg], { stdio: [py.stdout, 'inherit', 'inherit'] });
  const write = async buf => { if (!py.stdin.write(buf)) await new Promise(r => py.stdin.once('drain', r)); };
  const u32 = n => { const b = Buffer.alloc(4); b.writeUInt32LE(n); return b; };
  const t0 = Date.now();
  let blurred = 0;
  for (let k = 0; k < frames.length; k++) {
    const t = frames[k] / fps;
    const mb = K > 1 ? await page.evaluate(t => window.mbAt(t), t) : 0;
    // niveau 2 : K sous-images ; niveau 1 : K/2 ; sinon une seule
    const n = mb >= 2 ? K : mb === 1 ? Math.max(2, K / 2) : 1;
    if (n > 1) blurred++;
    await write(u32(n));
    for (let i = 0; i < n; i++) {
      const ts = n > 1 ? t + ((i + .5) / n - .5) * (0.5 / fps) : t;
      await page.evaluate(t => window.renderFrame(t), ts);
      const buf = await shot();
      await write(u32(buf.length)); await write(buf);
    }
    if (k % 60 === 0) console.log(`w${id} ${k}/${frames.length} (${((Date.now() - t0) / 1000).toFixed(0)} s, ${blurred} floues)`);
  }
  py.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
  await browser.close();
  return seg;
}

async function exportCues() {
  const browser = await launch();
  const { page } = await openPage(browser);
  const data = await page.evaluate(() => ({ duration: window.DURATION, marks: window.MARKS, cues: window.CUES }));
  await browser.close();
  fs.writeFileSync(path.join(OUT, 'cues.json'), JSON.stringify(data, null, 1));
  return data.duration;
}

async function video() {
  const fps = +arg('--fps', 60);
  const nw = +arg('--workers', 3);
  const K = +arg('--mb', 12);
  const duration = await exportCues();
  const f0 = Math.round(+arg('--from', 0) * fps), f1 = Math.round(+arg('--to', duration) * fps);
  const total = f1 - f0;
  const per = Math.ceil(total / nw);
  const jobs = [];
  for (let w = 0; w < nw; w++) {
    const frames = [];
    for (let f = f0 + w * per; f < Math.min(f1, f0 + (w + 1) * per); f++) frames.push(f);
    if (frames.length) jobs.push(worker(w, frames, fps, K));
  }
  const segs = await Promise.all(jobs);
  const list = path.join(OUT, 'segments.txt');
  fs.writeFileSync(list, segs.map(s => `file '${s}'`).join('\n'));
  const out = path.join(OUT, arg('--out', 'video-noaudio.mp4'));
  await new Promise((res, rej) => {
    const p = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', out], { stdio: 'inherit' });
    p.on('close', c => (c === 0 ? res() : rej(new Error('concat ' + c))));
  });
  segs.forEach(s => fs.unlinkSync(s)); fs.unlinkSync(list);
  console.log('ok ->', out, `${total} images @ ${fps} i/s, ${W}x${H}`);
}

if (args.includes('--cues')) console.log('cues ->', path.join(OUT, 'cues.json'), await exportCues(), 's');
else if (args.includes('--stills')) await stills(arg('--stills').split(',').map(Number));
else if (args.includes('--video')) await video();
else console.log('usage: node render.mjs --stills 1,2,3 [--scale 2] | --cues | --video [--fps 60] [--workers 3] [--scale 2] [--mb 12] [--from s --to s] [--out f.mp4]');
