"""Logo animation renderer — reproduces pandore.gif's motion/light design on logo.png.

All spatial quantities are expressed in GIF units (1 u = 1 pixel of the 250x250 reference
GIF, whose frame maps to the central HxH square of the output). Times are in seconds on the
3.00 s loop of the GIF (GIF frame i is shown at t=(i-1)*0.04).
"""
import math, json, os, sys
import numpy as np, cv2
from scipy.interpolate import PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import logo_geom

DUR = 3.0
GIF_DT = 0.04


def fk(i):
    """time of GIF frame i (1-based)"""
    return (i - 1) * GIF_DT


# ----------------------------------------------------------------------------- tracks
class Track:
    def __init__(self, keys, wrap=False):
        keys = sorted(keys)
        self.t = np.array([k[0] for k in keys], float)
        self.v = np.array([k[1] for k in keys], float)
        self.f = PchipInterpolator(self.t, self.v, extrapolate=False) if len(keys) > 1 else None

    def __call__(self, t):
        if self.f is None:
            return float(self.v[0])
        t = min(max(t, self.t[0]), self.t[-1])
        return float(self.f(t))


def flat_time(t):
    """flat (2D) phases live on [1.60, 3.12): the start of the loop (0..0.12) continues after 2.96"""
    return t + DUR if t < 0.5 else t


# measured (centred) homography elements, smoothed; keys are GIF frames
_HK = {
    # f : a, b, c, d, tx, ty, p(e-4), q(e-4)
    41: (0.9452, 0.0050, -0.0459, 0.9254, 0.00, -1.70, -0.98, -0.45),
    42: (0.8958, -0.0007, -0.0358, 0.8795, 0.35, -0.96, -0.52, 0.12),
    43: (0.8667, -0.0047, -0.0300, 0.8533, 0.45, -0.66, -0.57, 0.18),
    44: (0.8495, -0.0062, -0.0249, 0.8388, 0.41, -0.50, -0.68, 0.12),
    45: (0.8394, -0.0057, -0.0216, 0.8313, 0.31, -0.41, -0.77, 0.07),
    46: (0.8346, -0.0043, -0.0197, 0.8284, 0.16, -0.37, -0.87, -0.01),
    47: (0.8338, -0.0037, -0.0179, 0.8287, 0.06, -0.34, -0.93, -0.08),
    48: (0.8369, -0.0037, -0.0181, 0.8328, 0.13, -0.39, -0.68, -0.40),
    57: (0.8867, -0.0025, -0.0079, 0.8744, 0.37, 0.08, 0.04, -0.35),
    59: (0.8956, -0.0012, -0.0031, 0.8834, 0.32, 0.13, 0.17, -0.30),
    61: (0.9044, -0.0005, -0.0018, 0.8960, 0.23, 0.03, 0.11, -0.36),
    63: (0.9129, 0.0004, -0.0003, 0.9100, 0.14, 0.04, 0.07, -0.25),
    65: (0.9241, 0.0012, -0.0005, 0.9244, 0.08, 0.03, 0.04, -0.11),
    67: (0.9391, 0.0008, -0.0007, 0.9390, 0.02, 0.02, 0.00, -0.12),
    69: (0.9543, 0.0012, -0.0008, 0.9548, 0.02, 0.01, 0.01, -0.14),
    71: (0.9692, 0.0006, -0.0005, 0.9699, 0.02, 0.02, 0.02, -0.08),
    73: (0.9844, 0.0003, -0.0002, 0.9848, 0.01, 0.01, 0.01, -0.02),
    75: (1.0000, 0.0, 0.0, 1.0000, 0.0, 0.0, 0.0, 0.0),
    76: (1.0075, 0.0, 0.0, 1.0080, 0.0, 0.0, 0.0, 0.0),
    77: (1.0145, 0.0, 0.0, 1.0143, 0.0, 0.0, 0.0, 0.0),
    78: (1.0190, 0.0, 0.0, 1.0190, 0.0, 0.0, 0.0, 0.0),
    79: (1.0225, 0.0, 0.0, 1.0225, 0.0, 0.0, 0.0, 0.0),
}
_HTRACKS = [Track([(fk(f), v[j]) for f, v in _HK.items()]) for j in range(8)]


def flat_homography(t):
    """centred homography (GIF units) mapping the reference logo pose to the frame"""
    tt = flat_time(t)
    a, b, c, d, tx, ty, p, q = [tr(tt) for tr in _HTRACKS]
    return np.array([[a, b, tx], [c, d, ty], [p * 1e-4, q * 1e-4, 1.0]])


# glow weights fitted on the GIF (calib_glow2.py): sigma list + streak + const + haze
_GW = json.load(open(os.path.join(HERE, 'glow_w.json')))
GLOW_SIG = _GW['sig']
_gk = {int(k): v for k, v in _GW['w'].items()}
for k in (1, 2, 3):
    _gk[75 + k] = _gk.pop(k)
_GTRACKS = [Track([(fk(f), v[j]) for f, v in _gk.items()]) for j in range(len(GLOW_SIG) + 3)]


def glow_weights(t):
    tt = flat_time(t)
    if tt < fk(41):
        tt = fk(41)
    return [tr(tt) for tr in _GTRACKS]


# exposure of the logo fill (measured mean fill per frame)
FILL_EXP = Track([(fk(41), 1.25), (fk(69), 1.12), (fk(70), 1.09), (fk(71), 1.06), (fk(72), 1.04),
                  (fk(73), 1.02), (fk(74), 1.004), (fk(75), 1.0), (fk(78), 1.0)])
# softness ("burn") of the logo right after the 3D pull-back
FLAT_SOFT = Track([(fk(41), 1.1), (fk(42), 0.6), (fk(44), 0.15), (fk(46), 0.0), (fk(79), 0.0)])
# glitch intensity, GIF frames 49..62
GLITCH = Track([(fk(48), 0.0), (fk(49), 0.28), (fk(50), 0.62), (fk(51), 1.0), (fk(52), 1.0), (fk(53), 0.8),
                (fk(54), 0.55), (fk(55), 0.36), (fk(56), 0.2), (fk(57), 0.09), (fk(58), 0.07), (fk(59), 0.03),
                (fk(60), 0.012), (fk(62), 0.0), (fk(79), 0.0)])
BANDS = Track([(fk(56), 0.0), (fk(57), 0.5), (fk(58), 1.0), (fk(60), 0.6), (fk(62), 0.25), (fk(64), 0.0), (fk(79), 0.0)])
DUST = Track([(fk(39), 0.0), (fk(41), 1.0), (fk(48), 1.0), (fk(51), 0.6), (fk(57), 0.25), (fk(60), 0.0), (fk(79), 0.0)])


# ----------------------------------------------------------------------------- image helpers
def gblur(img, sx, sy=None):
    """Gaussian blur with zero borders; large sigmas are computed on a decimated image."""
    sy = sx if sy is None else sy
    if sx <= 0 and sy <= 0:
        return img
    h, w = img.shape[:2]
    fx = 1 if sx < 6 else 2 ** int(math.floor(math.log2(sx / 3.0)))
    fy = 1 if sy < 6 else 2 ** int(math.floor(math.log2(sy / 3.0)))
    if fx == 1 and fy == 1:
        return cv2.GaussianBlur(img, (0, 0), max(sx, 1e-3), sigmaY=max(sy, 1e-3), borderType=cv2.BORDER_CONSTANT)
    sw, sh = max(1, int(math.ceil(w / fx))), max(1, int(math.ceil(h / fy)))
    small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), max(sx / fx, 1e-3), sigmaY=max(sy / fy, 1e-3), borderType=cv2.BORDER_CONSTANT)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def softclip(x, knee=0.82):
    y = np.where(x < knee, x, 1.0 - (1.0 - knee) * np.exp(-(x - knee) / (1.0 - knee)))
    return np.clip(y, 0.0, 1.0)


def rng_for(*keys):
    h = 0
    for k in keys:
        h = (h * 1000003 + int(k)) & 0x7FFFFFFF
    return np.random.default_rng(h)


# ----------------------------------------------------------------------------- context
class Ctx:
    def __init__(self, W=3840, H=2160, ss=2):
        self.W, self.H, self.ss = W, H, ss
        self.ppu = 8.64 * H / 2160.0          # output px per GIF unit
        self.cx, self.cy = (W - 1) / 2.0, (H - 1) / 2.0
        polys = logo_geom.build()
        allp = np.vstack(polys)
        x0, y0 = allp.min(0); x1, y1 = allp.max(0)
        c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
        # same bounding-box area as the reference logo (168 x 194 u)
        s = math.sqrt(168.0 * 194.0 / ((x1 - x0) * (y1 - y0)))
        self.polys = [(p - c) * s for p in polys]          # logo in GIF units, centred
        self.logo_w, self.logo_h = (x1 - x0) * s, (y1 - y0) * s
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.gx = (xx - self.cx) / self.ppu                # GIF-unit coordinates of every pixel
        self.gy = (yy - self.cy) / self.ppu
        r2 = (self.gx ** 2 + self.gy ** 2) / (2 * 125.0 ** 2)
        self.haze = np.clip(1.0 - r2, 0, None).astype(np.float32)

    # map GIF-unit points (centred) to output pixels
    def to_px(self, pts):
        return np.stack([self.cx + pts[:, 0] * self.ppu, self.cy + pts[:, 1] * self.ppu], 1)

    def fill_polys(self, polys_px, value=1.0, img=None):
        """anti-aliased polygon coverage (supersampled), polys in output px"""
        ss = self.ss
        can = np.zeros((self.H * ss, self.W * ss), np.uint8)
        pl = [np.round(((p + 0.5) * ss - 0.5) * 16).astype(np.int32) for p in polys_px]
        cv2.fillPoly(can, pl, 255, lineType=cv2.LINE_AA, shift=4)
        m = cv2.resize(can, (self.W, self.H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        return m

    def logo_polys_px(self, Hc, polys=None):
        polys = self.polys if polys is None else polys
        out = []
        for p in polys:
            q = np.c_[p, np.ones(len(p))] @ Hc.T
            q = q[:, :2] / q[:, 2:3]
            out.append(self.to_px(q))
        return out


# ----------------------------------------------------------------------------- flat phases
def logo_fill(ctx, Hc, exp):
    """vertical light falloff measured on the reference (253 -> 231 over the logo height)"""
    sc = math.sqrt(abs(Hc[0, 0] * Hc[1, 1]))
    yl = (ctx.gy - Hc[1, 2]) / sc
    g = 0.994 * (1.0 - 0.0907 * np.clip((yl + 97.0) / 194.0, 0, 1))
    return np.minimum(g * exp, 1.0).astype(np.float32)


def glow_layer(ctx, M, w):
    p = ctx.ppu
    out = np.zeros_like(M)
    for wk, s in zip(w[:len(GLOW_SIG)], GLOW_SIG):
        if wk > 1e-4:
            out += wk * gblur(M, s * p)
    ws, wc, wh = w[len(GLOW_SIG):]
    if ws > 1e-4:
        out += ws * gblur(M, 60 * p, 5.0 * p)
    out += wc + wh * ctx.haze
    return out


def dust_layer(ctx, t, amount):
    if amount <= 0:
        return None
    rng = rng_for(7)
    n = 60
    ang = rng.uniform(0, 2 * np.pi, n); rad = rng.uniform(70, 135, n)
    pos = np.stack([np.cos(ang) * rad * 1.25, np.sin(ang) * rad * 0.95], 1)
    vel = rng.normal(0, 5, (n, 2)) + np.array([3.0, -5.0])
    size = rng.uniform(0.3, 0.8, n)
    bri = rng.uniform(0.3, 0.9, n)
    ph = rng.uniform(0, 2 * np.pi, n)
    tt = flat_time(t) - fk(41)
    img = np.zeros((ctx.H, ctx.W), np.float32)
    P = ctx.to_px(pos + vel * tt)
    for (x, y), s, b, f in zip(P, size, bri, ph):
        tw = 0.55 + 0.45 * math.sin(f + tt * 9.0)
        r = max(1.0, s * ctx.ppu * 0.6)
        cv2.circle(img, (int(round(x * 16)), int(round(y * 16))), int(round(r * 16)), float(b * tw * amount), -1,
                   lineType=cv2.LINE_AA, shift=4)
    return gblur(img, 0.35 * ctx.ppu)


def _hshift(band, sh):
    if sh == 0:
        return band
    out = np.empty_like(band)
    if sh > 0:
        out[:, sh:] = band[:, :-sh]; out[:, :sh] = band[:, :1]
    else:
        out[:, :sh] = band[:, -sh:]; out[:, sh:] = band[:, -1:]
    return out


def glitch(ctx, t, img, M, g, Hc):
    """horizontal slice displacement, smear, outline ghosts and block fragments (25 Hz pattern)"""
    if g <= 1e-3:
        return img
    p = ctx.ppu
    gi = int(math.floor(flat_time(t) / GIF_DT + 1e-6))
    rng = rng_for(11, gi)
    H, W = img.shape
    sc = math.sqrt(abs(Hc[0, 0] * Hc[1, 1]))
    hh = ctx.logo_h * sc / 2 + 8
    hw = ctx.logo_w * sc / 2 + 8
    out = img.copy()
    # 1) slice displacement of the logo + its glow
    nb = int(round(2 + 16 * g))
    for _ in range(nb):
        y0 = rng.uniform(-hh, hh)
        h = rng.uniform(0.7, 2.0 + 10.0 * g)
        dx = rng.normal(0, 1) * (4 + 26 * g)
        r0 = int(ctx.cy + y0 * p); r1 = int(ctx.cy + (y0 + h) * p)
        r0, r1 = max(0, r0), min(H, r1)
        if r1 > r0:
            out[r0:r1] = _hshift(out[r0:r1], int(round(dx * p)))
    # 2) horizontal smear, saturating at the peak
    a = float(np.clip((g - 0.35) / 0.65, 0, 1)) ** 1.2
    if a > 0:
        sm = gblur(out, (8 + 26 * a) * p, 1.0 * p) * (1.0 + 1.5 * a)
        out = np.maximum(out, sm * (0.3 + 0.55 * a))
    # 3) crisp outline ghosts of the logo, offset
    if g > 0.3:
        er = cv2.erode(M, np.ones((3, 3), np.uint8), iterations=max(1, int(round(1.1 * p))))
        edge = np.clip(M - er, 0, 1)
        for k in range(1 if g < 0.7 else 2):
            dx = rng.uniform(6, 38) * g * rng.choice([-1, 1])
            dy = rng.uniform(-16, 5) * g
            Mt = np.float32([[1, 0, dx * p], [0, 1, dy * p]])
            ghost = cv2.warpAffine(edge, Mt, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
            out = np.maximum(out, ghost * (1.25 * min(1.0, g * 1.4)))
    # 4) block fragments beside the logo
    for _ in range(int(round(22 * g))):
        y = rng.uniform(-hh, hh)
        side = rng.choice([-1, 1])
        x = side * rng.uniform(hw * 0.55, hw + 40) - (rng.uniform(4, 20) if side < 0 else 0)
        w = rng.uniform(2, 14); h = rng.uniform(0.6, 2.6)
        v = rng.uniform(0.3, 1.0)
        x0 = int(ctx.cx + x * p); y0 = int(ctx.cy + y * p)
        cv2.rectangle(out, (x0, y0), (int(x0 + w * p), int(y0 + h * p)), float(v), -1)
    return out


def bg_bands(ctx, t, amount):
    gi = int(math.floor(flat_time(t) / GIF_DT + 1e-6))
    rng = rng_for(23, gi // 2)
    prof = np.zeros(ctx.H, np.float32)
    for _ in range(26):
        y = rng.uniform(-125, 125); h = rng.uniform(1, 9)
        r0 = int(ctx.cy + y * ctx.ppu); r1 = int(ctx.cy + (y + h) * ctx.ppu)
        prof[max(0, r0):max(0, min(ctx.H, r1))] += rng.uniform(-0.03, 0.035)
    prof = cv2.GaussianBlur(prof[:, None], (0, 0), 0.6 * ctx.ppu)[:, 0]
    return (prof * amount)[:, None]


def render_flat(ctx, t):
    tt = flat_time(t)
    Hc = flat_homography(t)
    M = ctx.fill_polys(ctx.logo_polys_px(Hc))
    soft = FLAT_SOFT(tt)
    if soft > 0.02:
        M = gblur(M, soft * ctx.ppu)
    w = glow_weights(t)
    outside = glow_layer(ctx, M, w)
    fill = logo_fill(ctx, Hc, FILL_EXP(tt))
    img = M * fill + (1 - M) * outside
    d = DUST(tt)
    if d > 0:
        img = img + dust_layer(ctx, t, d)
    b = BANDS(tt)
    if b > 0:
        img = img + bg_bands(ctx, t, b) * (1 - M)
    g = GLITCH(tt)
    if g > 0:
        img = glitch(ctx, t, img, M, g, Hc)
    return img


# ----------------------------------------------------------------------------- frame
def grain(ctx, t, img, amt=0.012):
    rng = rng_for(99, int(round(t * 1000)))
    n = rng.standard_normal((ctx.H // 2 + 1, ctx.W // 2 + 1), dtype=np.float32)
    n = cv2.resize(n, (ctx.W, ctx.H), interpolation=cv2.INTER_LINEAR)[:ctx.H, :ctx.W]
    x = np.clip(img, 0, 1)
    return img + n * amt * (0.3 + 2.8 * x * (1 - x))


def render(ctx, t, phase3d=None):
    if 0.12 <= t < fk(41):
        if phase3d is None:
            import scene3d as phase3d
        img = softclip(phase3d.render_3d(ctx, t))
        xf = (t - (fk(41) - 0.07)) / 0.07
        if xf > 0:
            img = img * (1 - xf) + np.clip(render_flat(ctx, fk(41)), 0, 1) * xf
    else:
        img = np.clip(render_flat(ctx, t), 0, 1)
    img = grain(ctx, t, img)
    return np.clip(img, 0, 1)


def to8(img, t):
    rng = rng_for(5, int(round(t * 1000)))
    d = rng.random(img.shape, dtype=np.float32)
    return np.clip(img * 255.0 + d, 0, 255).astype(np.uint8)
