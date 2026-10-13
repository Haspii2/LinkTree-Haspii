"""Render every frame of the animation at 3840x2160, 60 fps, as 16-bit grey PNGs."""
import sys, os, time
import cv2
cv2.setNumThreads(1)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from multiprocessing import Pool
import numpy as np

W, H, FPS, DUR = 3840, 2160, 60, 3.0
OUT = sys.argv[1]
_ctx = None


def job(n):
    global _ctx
    import anim
    if _ctx is None:
        _ctx = anim.Ctx(W, H, ss=2)
    path = os.path.join(OUT, f'f{n:04d}.png')
    if os.path.exists(path):
        return n, 0.0
    t0 = time.time()
    t = n / FPS
    img = anim.render(_ctx, t)
    cv2.imwrite(path + '.tmp.png', np.round(img * 65535.0).astype(np.uint16), [cv2.IMWRITE_PNG_COMPRESSION, 1])
    os.replace(path + '.tmp.png', path)
    return n, time.time() - t0


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    N = int(round(FPS * DUR))
    order = list(range(8, 96)) + list(range(0, 8)) + list(range(96, N))   # heavy 3D frames first
    t0 = time.time()
    with Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 4) as p:
        for k, (n, dt) in enumerate(p.imap_unordered(job, order)):
            if k % 10 == 0:
                print(f'{k + 1}/{N} frame {n} {dt:.1f}s elapsed {time.time() - t0:.0f}s', flush=True)
    print('done', time.time() - t0, flush=True)
