"""3D 'tech' dive of the logo (GIF frames 4..40, t = 0.12 .. 1.60 s).

The logo is rebuilt as an extruded voxel structure: ribbed side walls, a greebled 'tech' floor,
raised rims along every piece's outline, depth of field, bokeh, bloom and anamorphic streaks.
Geometry is a stack of planes parallel to the logo; each plane is projected with an exact
homography of a perspective camera and composited back to front (camera always in front).
"""
import math, os, json
import numpy as np, cv2
from anim import Track, fk, gblur, rng_for, HERE

TEX_PPU = 16.0
TX0, TX1, TY0, TY1 = -112.0, 112.0, -96.0, 96.0
TW, TH = int((TX1 - TX0) * TEX_PPU), int((TY1 - TY0) * TEX_PPU)
CELL = 4.0           # voxel size (u)
D_WALL = 40.0        # depth of the extrusion below the floor
H_RIM = 9.0         # rim height above the floor
RIM_W = 2.5          # rim width
HFOV = 84.0

# ----------------------------------------------------------------------------- camera (measured)
_SI = [0.8436, 0.8652, 0.9064, 0.9347, 0.9393, 0.9503, 0.9463, 0.9429, 0.9546, 0.9741, 0.9829, 0.9948,
       0.9967, 0.9972, 0.9974, 0.9989, 0.9996, 1.0014, 1.0003, 1.0007, 1.0021, 0.9970, 0.9895, 0.9882,
       0.9928, 0.9961, 1.0002, 1.0020, 1.0065, 1.0116, 1.0186, 1.0304, 1.0450, 1.0631, 1.0897, 1.1377, 1.0731]
_ROT = [0.82, 1.38, 0.94, 0.60, 0.08, 0.19, 0.93, 1.49, 1.14, 0.84, 0.23, -0.14, -0.20, -0.43, -0.21, -0.28,
        -0.18, -0.16, -0.16, -0.27, -0.28, -0.25, -0.22, -0.22, -0.09, -0.13, -0.03, -0.22, -0.07, -0.06,
        -0.01, 0.05, -0.13, 0.06, -0.77, 0.58, 0.24]
_logS = np.concatenate([[0.0], np.cumsum(-np.log(_SI))])           # frames 4..41
_logS += math.log(0.935) - _logS[-1]                                # matches the flat pose at f41
_cr = np.concatenate([[0.0], np.cumsum(_ROT)])
_cr -= _cr[37 - 4]
SCALE = Track([(fk(4 + i), v) for i, v in enumerate(_logS)])
ROLL = Track([(fk(4 + i), v) for i, v in enumerate(_cr) if 4 + i <= 37] + [(fk(39), 0.25), (fk(41), 0.0)])
PITCH = Track([(fk(4), 15.0), (fk(10), 8.0), (fk(16), 5.0), (fk(30), 3.0), (fk(38), 0.8), (fk(41), 0.0)])
YAW = Track([(fk(4), -9.0), (fk(10), -5.5), (fk(16), -3.5), (fk(30), -2.0), (fk(38), -0.4), (fk(41), 0.0)])
# structure flattening for the hand-off to the flat logo, and voxel -> clean edges
FLAT = Track([(fk(4), 1.0), (fk(33), 1.0), (fk(38), 0.45), (fk(40), 0.12), (fk(41), 0.0)])
DETAIL = Track([(fk(4), 1.0), (fk(30), 1.0), (fk(36), 0.35), (fk(39), 0.0), (fk(41), 0.0)])
CLEAN = Track([(fk(4), 0.0), (fk(38), 0.0), (fk(39.5), 0.5), (fk(40.6), 1.0), (fk(41), 1.0)])
APERTURE = Track([(fk(4), 1.0), (fk(12), 1.0), (fk(20), 0.6), (fk(30), 0.6), (fk(38), 0.4), (fk(41), 0.0)])

# exposure / bloom / haze / streak tracks (calibrated against the GIF by calib3d.py)
_CAL = os.path.join(HERE, 'cal3d.json')


def _load_cal():
    if os.path.exists(_CAL):
        c = json.load(open(_CAL))
        return {k: Track([(float(a), float(b)) for a, b in v]) for k, v in c.items()}
    base = {
        'exp': [(fk(4), 1.0), (fk(8), 1.1), (fk(12), 1.35), (fk(16), 1.9), (fk(22), 2.8), (fk(29), 3.2),
                (fk(33), 2.9), (fk(36), 2.4), (fk(38), 2.0), (fk(40), 1.7), (fk(41), 1.5)],
        'bloom': [(fk(4), 0.9), (fk(8), 1.1), (fk(12), 1.4), (fk(20), 1.8), (fk(29), 2.0), (fk(36), 2.0),
                  (fk(38), 2.2), (fk(40), 2.0), (fk(41), 1.8)],
        'haze': [(fk(4), 0.0), (fk(10), 0.02), (fk(12), 0.05), (fk(16), 0.18), (fk(20), 0.3), (fk(29), 0.38),
                 (fk(33), 0.32), (fk(35), 0.22), (fk(36), 0.15), (fk(37), 0.08), (fk(38), 0.04), (fk(41), 0.03)],
        'vig': [(fk(4), 0.35), (fk(12), 0.3), (fk(16), 0.1), (fk(33), 0.1), (fk(38), 0.25), (fk(41), 0.15)],
        'streak': [(fk(4), 0.35), (fk(10), 0.25), (fk(16), 0.1), (fk(33), 0.1), (fk(38), 0.3), (fk(41), 0.3)],
    }
    return {k: Track(v) for k, v in base.items()}


CAL = _load_cal()


def reload_cal(d):
    global CAL
    CAL = {k: Track([(float(a), float(b)) for a, b in v]) for k, v in d.items()}


# ----------------------------------------------------------------------------- textures
_TEX = {}


def _tex_poly(polys, scale=1.0):
    out = []
    for p in polys:
        q = np.stack([(p[:, 0] - TX0) * TEX_PPU * scale - 0.5, (p[:, 1] - TY0) * TEX_PPU * scale - 0.5], 1)
        out.append(np.round(q * 16).astype(np.int32))
    return out


def _mask_clean(polys):
    m = np.zeros((TH, TW), np.uint8)
    cv2.fillPoly(m, _tex_poly(polys), 255, lineType=cv2.LINE_AA, shift=4)
    return m


def _mask_vox(polys, cell):
    k = int(round(cell * TEX_PPU))
    gw, gh = int(math.ceil(TW / k)), int(math.ceil(TH / k))
    ss = 8
    can = np.zeros((gh * ss, gw * ss), np.uint8)
    pl = []
    for p in polys:
        q = np.stack([(p[:, 0] - TX0) / cell * ss - 0.5, (p[:, 1] - TY0) / cell * ss - 0.5], 1)
        pl.append(np.round(q * 16).astype(np.int32))
    cv2.fillPoly(can, pl, 255, lineType=cv2.LINE_8, shift=4)
    cov = cv2.resize(can, (gw, gh), interpolation=cv2.INTER_AREA)
    vox = (cov >= 128).astype(np.uint8) * 255
    big = cv2.resize(vox, (gw * k, gh * k), interpolation=cv2.INTER_NEAREST)[:TH, :TW]
    return np.ascontiguousarray(big)


def _floor_texture(sil, rim, rng):
    """procedural 'tech' panels: seams, hatching, window grids, LEDs"""
    k = int(round(CELL * TEX_PPU))
    tex = np.full((TH, TW), 1.0, np.float32)
    gre1 = np.zeros((TH, TW), np.uint8)
    gre2 = np.zeros((TH, TW), np.uint8)
    lw = max(2, int(0.35 * TEX_PPU))

    def split(x0, y0, x1, y1, depth):
        w, h = x1 - x0, y1 - y0
        if depth > 0 and (w > 2 * k or h > 2 * k) and (rng.random() < 0.85 or w > 5 * k or h > 5 * k):
            if w >= h and w > 2 * k:
                c = x0 + k * int(rng.integers(1, w // k))
                split(x0, y0, c, y1, depth - 1); split(c, y0, x1, y1, depth - 1); return
            if h > 2 * k:
                c = y0 + k * int(rng.integers(1, h // k))
                split(x0, y0, x1, c, depth - 1); split(x0, c, x1, y1, depth - 1); return
        kind = rng.choice(['plain', 'hatch', 'win', 'raise', 'raise2'], p=[0.3, 0.16, 0.24, 0.21, 0.09])
        ix0, iy0, ix1, iy1 = x0 + lw, y0 + lw, x1 - lw, y1 - lw
        if ix1 <= ix0 or iy1 <= iy0:
            return
        if kind == 'plain':
            tex[iy0:iy1, ix0:ix1] = rng.uniform(0.92, 1.08)
        elif kind == 'hatch':
            per = int(rng.uniform(1.4, 2.2) * TEX_PPU)
            tex[iy0:iy1, ix0:ix1] = 1.0
            for yy in range(iy0, iy1, per):
                tex[yy:min(iy1, yy + per // 2), ix0:ix1] = rng.uniform(0.3, 0.5)
        elif kind == 'win':
            tex[iy0:iy1, ix0:ix1] = 0.25
            cs = int(rng.uniform(1.2, 2.4) * TEX_PPU)
            g = max(2, int(0.3 * TEX_PPU))
            for yy in range(iy0 + g, iy1 - g, cs):
                for xx in range(ix0 + g, ix1 - g, cs):
                    tex[yy:min(iy1 - g, yy + cs - g), xx:min(ix1 - g, xx + cs - g)] = rng.choice([1.0, 1.15, 0.8, 1.3])
        elif kind in ('raise', 'raise2'):
            tex[iy0:iy1, ix0:ix1] = 1.18
            (gre2 if kind == 'raise2' else gre1)[iy0:iy1, ix0:ix1] = 255
        # seams
        tex[y0:y0 + lw, x0:x1] = 0.3; tex[y1 - lw:y1, x0:x1] = 0.3
        tex[y0:y1, x0:x0 + lw] = 0.3; tex[y0:y1, x1 - lw:x1] = 0.3

    split(0, 0, (TW // k) * k, (TH // k) * k, 14)
    # LEDs
    for _ in range(260):
        x, y = int(rng.uniform(0, TW)), int(rng.uniform(0, TH))
        r = int(rng.uniform(0.25, 0.5) * TEX_PPU)
        cv2.circle(tex, (x, y), r, float(rng.uniform(1.3, 1.8)), -1, lineType=cv2.LINE_AA)
    inner = cv2.subtract(sil, rim)
    tex *= inner.astype(np.float32) / 255.0
    gre1 = cv2.bitwise_and(gre1, cv2.erode(inner, np.ones((5, 5), np.uint8)))
    gre2 = cv2.bitwise_and(gre2, cv2.erode(inner, np.ones((5, 5), np.uint8)))
    return tex, gre1, gre2


def _rim_texture(rim, rng):
    tex = rim.astype(np.float32) / 255.0 * 1.22
    k = int(round(CELL * TEX_PPU))
    lw = max(2, int(0.3 * TEX_PPU))
    for x in range(0, TW, 2 * k):
        tex[:, x:x + lw] *= 0.6
    for y in range(0, TH, 2 * k):
        tex[y:y + lw, :] *= 0.6
    return tex


def _pyr(img, levels=3):
    out = [img]
    for _ in range(levels - 1):
        h, w = out[-1].shape[:2]
        out.append(cv2.resize(out[-1], ((w + 1) // 2, (h + 1) // 2), interpolation=cv2.INTER_AREA))
    return out


def textures(ctx):
    if 'ok' in _TEX:
        return _TEX
    rng = rng_for(31337)
    polys = ctx.polys
    sil = _mask_vox(polys, CELL)
    rim = cv2.subtract(sil, cv2.erode(sil, cv2.getStructuringElement(cv2.MORPH_RECT, (int(2 * RIM_W * TEX_PPU) + 1,) * 2)))
    ftex, g1, g2 = _floor_texture(sil, rim, rng)
    rtex = _rim_texture(rim, rng)
    clean = _mask_clean(polys)
    vox2 = _mask_vox(polys, CELL / 2)
    vox4 = _mask_vox(polys, CELL / 4)
    T = dict(sil=sil, rim=rim, g1=g1, g2=g2, clean=clean, vox2=vox2, vox4=vox4,
             ftex=np.clip(ftex * 140, 0, 255).astype(np.uint8),       # stored /140
             rtex=np.clip(rtex * 140, 0, 255).astype(np.uint8))
    for k_, v in T.items():
        _TEX[k_] = _pyr(v)
    _TEX['ok'] = True
    return _TEX


# ----------------------------------------------------------------------------- projection
class Cam:
    def __init__(self, ctx, t):
        self.S = math.exp(SCALE(t))
        self.f = (ctx.W / 2.0) / math.tan(math.radians(HFOV / 2))
        self.d = self.f / (ctx.ppu * self.S)            # distance to the floor plane (u)
        self.roll = math.radians(ROLL(t))
        p, y = math.radians(PITCH(t)), math.radians(YAW(t))
        Rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
        Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
        self.R = Rx @ Ry
        # orbit: the camera keeps looking at the logo centre
        v = self.R.T @ np.array([0.0, 0.0, self.d])
        self.pos = np.array([-v[0], -v[1], v[2]])
        self.cx, self.cy = ctx.cx, ctx.cy

    def project(self, X, Y, Z):
        P = np.stack([X - self.pos[0], Y - self.pos[1], self.pos[2] - Z], 0)   # camera looks toward -Z
        Pc = self.R @ P
        u = self.f * Pc[0] / Pc[2]; v = self.f * Pc[1] / Pc[2]
        c, s = math.cos(self.roll), math.sin(self.roll)
        return self.cx + u * c + v * s, self.cy - u * s + v * c, Pc[2]

    def depth(self, Z):
        return self.project(np.array([0.0]), np.array([0.0]), np.array([Z]))[2][0]

    def H(self, Z, level):
        sc = 2 ** level
        w, h = TW / sc, TH / sc
        src = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
        X = TX0 + (src[:, 0] + 0.5) * sc / TEX_PPU
        Y = TY0 + (src[:, 1] + 0.5) * sc / TEX_PPU
        u, v, _ = self.project(X, Y, np.full(4, Z))
        return cv2.getPerspectiveTransform(src, np.float32(np.stack([u, v], 1)))


def _level(cam, ctx, Z):
    px_per_u = cam.f / cam.depth(Z)
    ratio = TEX_PPU / max(px_per_u, 1e-3)
    return int(np.clip(math.floor(math.log2(max(ratio, 1.0)) + 0.15), 0, 2))


def _warp(ctx, tex, cam, Z):
    L = _level(cam, ctx, Z)
    return cv2.warpPerspective(tex[L], cam.H(Z, L), (ctx.W, ctx.H), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=0)


# ----------------------------------------------------------------------------- render
def _layers(t):
    fl = FLAT(t)
    det = DETAIL(t)
    L = []
    D = D_WALL * fl
    if D > 0.3:
        n = 30
        for k in range(n):
            Z = -D + D * k / n
            depthf = (k + 0.5) / n                      # 0 deep .. 1 near floor
            rib = 1.0 if (k % 3 == 0) else (0.55 if k % 3 == 1 else 0.75)
            shade = (0.4 + 0.6 * depthf) * rib
            L.append((Z, 'sil', 1.0 - det * (1.0 - shade), None))
    L.append((0.0, 'floor', None, det))
    for key, hmax in (('g1', 3.0), ('g2', 6.5)):
        h = hmax * fl
        if h > 0.2:
            for k in range(4):
                L.append((h * k / 4 + 0.01, key, 1.0 - det * 0.35, None))
            L.append((h, key, 1.0 + 0.2 * det, None))
    hr = H_RIM * fl
    if hr > 0.3:
        n = 18
        for k in range(n):
            Z = hr * k / n + 0.02
            rib = 1.0 if (k % 3 == 0) else (0.55 if k % 3 == 1 else 0.75)
            L.append((Z, 'rim', 1.0 - det * (1.0 - (0.35 + 0.45 * k / n) * rib), None))
        L.append((hr, 'rtex', None, det))
    L.sort(key=lambda x: x[0])
    return L


def render_3d(ctx, t):
    T = textures(ctx)
    cam = Cam(ctx, t)
    clean = CLEAN(t)
    det = DETAIL(t)
    W, H = ctx.W, ctx.H
    zf = cam.depth(-4.0 * FLAT(t))
    ap = 48.0 * APERTURE(t)                             # aperture radius (u)
    acc = np.zeros((H, W), np.float32)

    def sigma(Z):
        z = cam.depth(Z)
        return 0.5 * ap * cam.f * abs(1.0 / z - 1.0 / zf)

    def sil_mask(Z):
        if clean <= 0:
            return _warp(ctx, T['sil'], cam, Z).astype(np.float32) / 255.0
        if clean < 0.34:
            a = _warp(ctx, T['sil'], cam, Z); b = _warp(ctx, T['vox2'], cam, Z)
            w = clean / 0.34
        elif clean < 0.67:
            a = _warp(ctx, T['vox2'], cam, Z); b = _warp(ctx, T['vox4'], cam, Z)
            w = (clean - 0.34) / 0.33
        else:
            a = _warp(ctx, T['vox4'], cam, Z); b = _warp(ctx, T['clean'], cam, Z)
            w = (clean - 0.67) / 0.33
        w = 1.0 if w > 0.5 else 0.0                       # digital step, no cross-dissolve
        return (a.astype(np.float32) * (1 - w) + b.astype(np.float32) * w) / 255.0

    groups = []
    cur = None
    for Z, key, val, d in _layers(t):
        s = sigma(Z)
        if cur is None or abs(s - cur['s']) > max(1.2, 0.22 * cur['s']):
            cur = dict(s=s, items=[]); groups.append(cur)
        cur['items'].append((Z, key, val, d))
        cur['s'] = s if len(cur['items']) == 1 else cur['s']

    for g in groups:
        C = np.zeros((H, W), np.float32); A = np.zeros((H, W), np.float32)
        for Z, key, val, d in g['items']:
            if key == 'floor':
                m = sil_mask(Z)
                tx = _warp(ctx, T['ftex'], cam, Z).astype(np.float32) / 140.0
                c = m * (1 - d) + tx * d
            elif key == 'rtex':
                m = _warp(ctx, T['rim'], cam, Z).astype(np.float32) / 255.0
                tx = _warp(ctx, T['rtex'], cam, Z).astype(np.float32) / 140.0
                c = m * (1 - d) * 1.0 + tx * d
            elif key == 'sil':
                m = sil_mask(Z); c = m * val
            else:
                m = _warp(ctx, T[key], cam, Z).astype(np.float32) / 255.0; c = m * val
            C *= (1 - m); C += c
            A *= (1 - m); A += m
        s = g['s']
        if s > 0.6:
            C = gblur(C, s); A = gblur(A, s)
        acc *= (1 - np.clip(A, 0, 1)); acc += C

    hdr = acc * CAL['exp'](t)
    hdr += _bokeh(ctx, cam, t, sigma) * CAL['exp'](t) ** 0.5
    p = ctx.ppu
    b = CAL['bloom'](t)
    src = np.maximum(hdr - 0.75, 0) + 0.12 * hdr          # highlights drive the bloom
    bl = (0.30 * gblur(src, 2.0 * p) + 0.26 * gblur(src, 6.0 * p) + 0.22 * gblur(src, 16.0 * p)
          + 0.16 * gblur(src, 40.0 * p) + 0.12 * gblur(src, 100.0 * p))
    hot = np.maximum(hdr - 1.2, 0)
    st = gblur(hot, 60.0 * p, 6.0 * p) + 0.5 * gblur(hot, 25.0 * p, 3.0 * p)
    out = hdr + b * bl + CAL['streak'](t) * st + CAL['haze'](t) * (0.55 + 0.45 * ctx.haze)
    kv = CAL['vig'](t) if 'vig' in CAL else 0.0
    if kv > 0:
        out *= 1.0 - kv * _vig_ramp(ctx)
    return out


_VR = {}


def _vig_ramp(ctx):
    key = (ctx.W, ctx.H)
    if key not in _VR:
        r = np.sqrt(ctx.gx ** 2 + ctx.gy ** 2)
        _VR[key] = (np.clip((r - 55.0) / 120.0, 0, 1) ** 1.4).astype(np.float32)
    return _VR[key]


def _bokeh(ctx, cam, t, sigma):
    rng = rng_for(4242)
    n = 22
    X = rng.uniform(-260, 260, n); Y = rng.uniform(-170, 170, n); Z = rng.uniform(-20, 190, n)
    br = rng.uniform(0.25, 1.0, n)
    img = np.zeros((ctx.H, ctx.W), np.float32)
    u, v, z = cam.project(X, Y, Z)
    vis = DETAIL(t)
    for i in range(n):
        if z[i] < 8:
            continue
        r = max(1.2, 2.0 * sigma(Z[i]))
        if r > 0.12 * ctx.H:
            continue
        a = br[i] * vis * min(1.0, (3.0 / r) ** 2 * 4) * 0.7
        if a < 0.01:
            continue
        x, y = u[i], v[i]
        if not (-r < x < ctx.W + r and -r < y < ctx.H + r):
            continue
        cv2.circle(img, (int(round(x * 16)), int(round(y * 16))), int(round(r * 16)), float(a), -1,
                   lineType=cv2.LINE_AA, shift=4)
    return gblur(img, 0.6 * ctx.ppu)
