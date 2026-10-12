// Rendu image par image de scene.html (Chromium headless) puis encodage ffmpeg.
//
//   node render.mjs --stills 1.2,8.5,15     -> out/stills/*.png (aperçus)
//   node render.mjs --cues                 -> out/cues.json (feuille de bruitages)
//   node render.mjs --video [--fps 60] [--workers 3] [--scale 1] [--mb 12]
//                                          -> out/video-noaudio.mp4 + out/cues.json
//
// Flou de mouvement : sur les plans que la scène marque (window.mbAt), chaque image est
// la moyenne de sous-images réparties sur un obturateur à 180° (une demi-image) :
// --mb sur les raccords et fouettés, la moitié sur les mouvements plus lents.
// Les autres images sont envoyées --mb fois à l'identique, puis ffmpeg (tmix) fait la moyenne.
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

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: SCALE });
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

async function worker(id, frames, fps, K) {
  const browser = await launch();
  const page = await openPage(browser);
  const seg = path.join(OUT, `seg${id}.mp4`);
  const vf = `tmix=frames=${K},select='eq(mod(n\\,${K})\\,${K - 1})',setpts=N/(${fps}*TB)`;
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps * K), '-c:v', 'png', '-i', '-',
    '-vf', vf, '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p',
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-r', String(fps), seg], { stdio: ['pipe', 'inherit', 'inherit'] });
  const write = async buf => { if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); };
  const t0 = Date.now();
  let blurred = 0;
  for (let k = 0; k < frames.length; k++) {
    const t = frames[k] / fps;
    const mb = await page.evaluate(t => window.mbAt(t), t);
    if (mb && K > 1) {
      // niveau 2 : K sous-images distinctes ; niveau 1 : K/2 sous-images, chacune écrite deux fois
      blurred++;
      const n = mb >= 2 ? K : Math.max(1, K / 2), rep = K / n;
      for (let i = 0; i < n; i++) {
        await page.evaluate(t => window.renderFrame(t), t + (i / n) * (0.5 / fps));
        const buf = await page.screenshot({ type: 'png' });
        for (let r = 0; r < rep; r++) await write(buf);
      }
    } else {
      await page.evaluate(t => window.renderFrame(t), t);
      const buf = await page.screenshot({ type: 'png' });
      for (let i = 0; i < K; i++) await write(buf);
    }
    if (k % 120 === 0) console.log(`w${id} ${k}/${frames.length} (${((Date.now() - t0) / 1000).toFixed(0)}s, ${blurred} floues)`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
  await browser.close();
  return seg;
}

async function exportCues() {
  const browser = await launch();
  const page = await openPage(browser);
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
  const total = Math.round(duration * fps);
  const per = Math.ceil(total / nw);
  const jobs = [];
  for (let w = 0; w < nw; w++) {
    const frames = [];
    for (let f = w * per; f < Math.min(total, (w + 1) * per); f++) frames.push(f);
    jobs.push(worker(w, frames, fps, K));
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
else console.log('usage: node render.mjs --stills 1,2,3 | --cues | --video [--fps 60] [--workers 3] [--scale 1] [--mb 6]');
