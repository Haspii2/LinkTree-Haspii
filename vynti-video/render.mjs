// Rendu image par image de scene.html (Chromium headless) puis encodage ffmpeg.
//
//   node render.mjs --stills 1.2,8.5,15     -> out/stills/*.png (aperçus)
//   node render.mjs --cues                 -> out/cues.json (repères sonores)
//   node render.mjs --video [--fps 60] [--workers 3]
//                                          -> out/video-noaudio.mp4 + out/cues.json
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

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto(URL_SCENE);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });
  return page;
}

const launch = () => playwright.chromium.launch({
  args: ['--force-color-profile=srgb', '--hide-scrollbars', '--font-render-hinting=none', '--disable-lcd-text'],
});

async function stills(times) {
  const browser = await launch();
  const page = await openPage(browser);
  const dir = path.join(OUT, 'stills');
  fs.mkdirSync(dir, { recursive: true });
  for (const t of times) {
    await page.evaluate(t => window.renderFrame(t), t);
    const f = path.join(dir, `t${t.toFixed(2).padStart(6, '0')}.png`);
    await page.screenshot({ path: f });
    console.log(f);
  }
  await browser.close();
}

async function worker(id, frames, fps) {
  const browser = await launch();
  const page = await openPage(browser);
  const seg = path.join(OUT, `seg${id}.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
    '-r', String(fps), seg], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let k = 0; k < frames.length; k++) {
    const f = frames[k];
    await page.evaluate(t => window.renderFrame(t), f / fps);
    const buf = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (k % 120 === 0) console.log(`w${id} ${k}/${frames.length} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
  await browser.close();
  return seg;
}

async function exportCues() {
  const browser = await launch();
  const page = await openPage(browser);
  const { duration, cues, scenes } = await page.evaluate(() => ({ duration: window.DURATION, cues: window.CUES, scenes: window.SCENES }));
  await browser.close();
  fs.writeFileSync(path.join(OUT, 'cues.json'), JSON.stringify({ duration, scenes, cues }, null, 1));
  return duration;
}

async function video() {
  const fps = +arg('--fps', 60);
  const nw = +arg('--workers', 3);
  const duration = await exportCues();
  const total = Math.round(duration * fps);
  const per = Math.ceil(total / nw);
  const jobs = [];
  for (let w = 0; w < nw; w++) {
    const frames = [];
    for (let f = w * per; f < Math.min(total, (w + 1) * per); f++) frames.push(f);
    jobs.push(worker(w, frames, fps));
  }
  const segs = await Promise.all(jobs);
  const list = path.join(OUT, 'segments.txt');
  fs.writeFileSync(list, segs.map(s => `file '${s}'`).join('\n'));
  await new Promise((res, rej) => {
    const p = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', path.join(OUT, 'video-noaudio.mp4')], { stdio: 'inherit' });
    p.on('close', c => (c === 0 ? res() : rej(new Error('concat ' + c))));
  });
  segs.forEach(s => fs.unlinkSync(s)); fs.unlinkSync(list);
  console.log('ok ->', path.join(OUT, 'video-noaudio.mp4'), `${total} images @ ${fps} i/s`);
}

if (args.includes('--cues')) console.log('cues ->', path.join(OUT, 'cues.json'), await exportCues(), 's');
else if (args.includes('--stills')) await stills(arg('--stills').split(',').map(Number));
else if (args.includes('--video')) await video();
else console.log('usage: node render.mjs --stills 1,2,3 | --video [--fps 60] [--workers 3]');
