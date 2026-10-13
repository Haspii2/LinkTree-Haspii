"""Encode the 16-bit grey frames from render_all.py into a 4K 60 fps H.264 MP4.

Luma is written directly in BT.709 limited range with TPDF dither (no banding) and the chroma
planes are exactly neutral (U = V = 128), so the white stays pure white with no colour cast.
usage: python3 encode.py <frames_dir> <out.mp4> [crf]
"""
import os, sys, subprocess
import numpy as np, cv2

IN, OUT = sys.argv[1], sys.argv[2]
CRF = sys.argv[3] if len(sys.argv) > 3 else '12'
files = sorted(f for f in os.listdir(IN) if f.startswith('f') and f.endswith('.png') and '.tmp' not in f)
H, W = cv2.imread(os.path.join(IN, files[0]), cv2.IMREAD_UNCHANGED).shape[:2]
cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', '-s', f'{W}x{H}', '-r', '60',
       '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-i', '-',
       '-c:v', 'libx264', '-preset', 'slow', '-crf', CRF, '-profile:v', 'high', '-level:v', '5.2',
       '-x264-params', 'aq-mode=3:aq-strength=0.8:deblock=-1,-1',
       '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
       '-movflags', '+faststart', '-an', OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
chroma = np.full(2 * (H // 2) * (W // 2), 128, np.uint8).tobytes()
rng = np.random.default_rng(2026)
for f in files:
    x = cv2.imread(os.path.join(IN, f), cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535.0
    y = 16.0 + 219.0 * x + (rng.random(x.shape, np.float32) - rng.random(x.shape, np.float32))
    p.stdin.write(np.clip(np.round(y), 16, 235).astype(np.uint8).tobytes())
    p.stdin.write(chroma)
p.stdin.close()
sys.exit(p.wait())
