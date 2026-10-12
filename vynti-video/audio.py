"""Bande-son 100 % synthétisée (aucun sample externe, donc libre de droits).

Suit le script : musique à 120 BPM (intro filtrée, groove A, groove B avec basse, montée,
100 ms de silence, drop à 0:46, outro qui résout sur l'accord final) et les 55 bruitages
de la feuille, à leurs temps, crêtes et places dans le champ (out/cues.json, exporté
depuis la timeline de scene.html).

Mixage : ducking de la musique sous les impacts et carillons, creux de 2 dB vers 2-4 kHz,
passe-haut 120 Hz et pièce courte (0,6 s, 10 %) sur l'interface, passe-haut 40 Hz et subs
en mono sur les transitions, maître à -14 LUFS intégrés et -1 dBTP, 48 kHz / 24 bits.

    python3 audio.py  ->  out/audio.wav
"""
import json
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy import ndimage, signal

SR = 48000
DIR = Path(__file__).resolve().parent
OUT = DIR / "out"
data = json.loads((OUT / "cues.json").read_text())
DUR = float(data["duration"])
M = data["marks"]
N = int((DUR + .5) * SR)
rng = np.random.default_rng(11)
BEAT = .5
BAR = 2.0


# ----------------------------------------------------------------- outils
def T(d):
    return np.arange(int(round(d * SR))) / SR


def sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output="sos")


def filt(x, kind, f, order=2):
    return signal.sosfilt(sos(kind, f, order), x, axis=0)


def st(x, pan=0.0):
    """mono -> stéréo, panoramique à puissance constante (pan de -1 à +1)"""
    a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def st_sweep(x, p0, p1):
    pans = np.linspace(p0, p1, len(x))
    a = (pans + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def place(bus, x, t, gain=1.0):
    i = int(round(t * SR))
    if x.ndim == 1:
        x = st(x)
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(bus), i + len(x))
    if j > i:
        bus[i:j] += x[: j - i] * gain


def placem(bus, x, t, gain=1.0):
    i = int(round(t * SR))
    j = min(len(bus), i + len(x))
    if j > i:
        bus[i:j] += x[: j - i] * gain


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_ar(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na) ** 1.6
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e


def add(*xs):
    n = max(len(x) for x in xs)
    out = np.zeros(n)
    for x in xs:
        out[:len(x)] += x
    return out


def norm_peak(x, db):
    p = np.max(np.abs(x))
    return x * (10 ** (db / 20) / p) if p > 0 else x


def peaking(x, f0, gain_db, q):
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]
    a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def sweep_filter(x, kind, f_of_t, t0=0.0, blk=256, order=2):
    """filtre dont la fréquence de coupure varie dans le temps (bloc par bloc)"""
    out = np.zeros_like(x)
    zi = None
    for i in range(0, len(x), blk):
        f = float(np.clip(f_of_t(t0 + i / SR), 20, SR / 2 - 200))
        s = sos(kind, f, order)
        if zi is None:
            zi = np.zeros((s.shape[0], 2) + x.shape[1:])
        out[i:i + blk], zi = signal.sosfilt(s, x[i:i + blk], axis=0, zi=zi)
    return out


def reverb(x, secs, tone=6000, pre=.01, seed=3):
    r = np.random.default_rng(seed)
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = r.standard_normal((n, 2)) * np.exp(-t * 6.9 / secs)[:, None]
    ir = filt(ir, "lowpass", tone)
    ir[: int(pre * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(axis=0))
    return np.stack([signal.fftconvolve(x[:, k], ir[:, k])[: len(x)] for k in range(2)], axis=1)


# =============================================================== musique
CH = {  # tonalité : do majeur / la mineur
    "Am7": [57, 60, 64, 67], "Fmaj7": [53, 57, 60, 64], "Cmaj7": [48, 55, 59, 64], "G6": [55, 59, 62, 64],
    "Fmaj9": [53, 57, 60, 64, 67], "Cmaj9": [48, 55, 59, 62, 64, 67],
}
ROOT = {"Am7": 45, "Fmaj7": 41, "Cmaj7": 48, "G6": 43, "Fmaj9": 41, "Cmaj9": 36}
PROG = ["Am7", "Fmaj7", "Cmaj7", "G6"]


def chord_at(t):
    if t >= M["resolve"]:
        return "Cmaj9"
    if t >= M["outro"]:
        return "Fmaj9"
    return PROG[int(t // BAR) % 4]


def pad_note(f, d, bright=1.0, seed=0):
    r = np.random.default_rng(seed)
    t = T(d)
    out = np.zeros((len(t), 2))
    for det, pan in ((-.08, -.75), (0.0, 0.0), (.08, .75)):
        ff = f * 2 ** (det / 12)
        v = np.zeros(len(t))
        for k in range(1, 10):
            v += np.sin(2 * np.pi * ff * k * t + r.uniform(0, 6.28)) / k ** (1.45 - .2 * bright)
        out += st(v, pan)
    return out


def pluck(f, d=.8, bright=1.0):
    t = T(d)
    v = np.sin(2 * np.pi * f * t + 1.1 * bright * np.exp(-t * 16) * np.sin(2 * np.pi * 2 * f * t))
    v += .3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 12)
    return v * np.exp(-t * 6) * np.minimum(1, t / .003)


def kick(punch=1.0):
    t = T(.45)
    f = 45 + 115 * np.exp(-t * 30)
    v = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    v += filt(rng.standard_normal(len(t)), "bandpass", [1800, 6000]) * np.exp(-t * 300) * .22 * punch
    return v


def hat(open_=False):
    t = T(.22 if open_ else .06)
    return filt(rng.standard_normal(len(t)), "highpass", 7000) * np.exp(-t * (14 if open_ else 75))


def clap():
    t = T(.3)
    e = np.exp(-t * 17)
    for o in (0, .01, .021):
        e += .6 * np.exp(-np.maximum(t - o, 0) * 200) * (t >= o)
    return filt(rng.standard_normal(len(t)), "bandpass", [900, 3000]) * e * .5


def bassnote(f, d):
    t = T(d)
    v = np.sin(2 * np.pi * f * t) + .22 * np.sin(4 * np.pi * f * t) + .08 * np.sin(6 * np.pi * f * t)
    return v * env_ar(len(t), .006, .06) * np.exp(-t * 1.8)


def music():
    pad = np.zeros((N, 2))
    arp = np.zeros((N, 2))
    drums = np.zeros((N, 2))
    low = np.zeros(N)
    end_main = M["silence"]
    # nappe : un accord par mesure ; plus pleine dans le drop
    t = 0.0
    while t < M["nearsilence"]:
        name = chord_at(t)
        d = BAR + 1.0
        drop = M["drop"] <= t < M["nearsilence"]
        g = .05 * (1.25 if drop else 1)
        for j, m in enumerate(CH[name] + ([CH[name][0] + 12] if drop else [])):
            x = pad_note(midi(m), d, 1.3 if drop else 1, seed=int(t * 10) + j) * env_ar(int(d * SR), .45, .9)[:, None]
            place(pad, x, t, g)
        t += BAR
    # sortie : Fmaj9 puis résolution sur Cmaj9 à 56,4 s, queue jusqu'à la fin
    for name, a, b in (("Fmaj9", M["outro"], M["resolve"] + .6), ("Cmaj9", M["resolve"], DUR + .5)):
        d = b - a
        for j, m in enumerate(CH[name]):
            x = pad_note(midi(m), d, .9, seed=90 + j) * env_ar(int(d * SR), .25 if name == "Fmaj9" else .02, 2.6 if name == "Cmaj9" else .6)[:, None]
            place(pad, x, a, .055)
    for m in (60, 64, 67, 72):   # le « coup » d'accord de la résolution
        place(arp, st(pluck(midi(m), 2.4, .7), .2 * (m % 3 - 1)), M["resolve"], .07)
    # arpège : croches dès l'intro, doubles croches dans le drop
    pattern = [0, 2, 1, 3, 2, 1, 3, 2]
    t, k = 0.0, 0
    while t < M["nearsilence"]:
        drop = M["drop"] <= t
        step = BEAT / (4 if drop else 2)
        if not (end_main <= t < M["drop"]):
            notes = CH[chord_at(t)]
            m = notes[pattern[k % 8] % len(notes)] + 12 + (12 if drop and k % 4 == 3 else 0)
            g = (.085 if not drop else .07) * (.8 if k % 2 else 1)
            place(arp, st(pluck(midi(m), .7, 1.2 if drop else 1), -.4 if k % 2 else .4), t, g)
        t += step
        k += 1
    # batterie : groove A dès 0:06, groove B (+ basse) à 32,5 s, drop à 0:46
    beats = np.arange(M["groove"], M["nearsilence"] - 1e-6, BEAT)
    sc = np.ones(N)
    for i, bt in enumerate(beats):
        if end_main <= bt < M["drop"]:
            continue
        drop = bt >= M["drop"]
        build = M["build"] <= bt < end_main
        place(drums, st(kick(1.0)), bt, .44 if drop else .42)
        i0 = int(bt * SR)
        seg = 1 - (.6 if drop else .45) * np.exp(-T(.45) * 9)
        sc[i0:i0 + len(seg)] = np.minimum(sc[i0:i0 + len(seg)], seg[: len(sc[i0:i0 + len(seg)])])
        place(drums, st(hat(open_=drop), .25), bt + BEAT / 2, .2 if drop else .13)
        if bt >= M["bass"]:
            place(drums, st(hat(), -.25), bt + BEAT / 4, .06)
            place(drums, st(hat(), -.25), bt + 3 * BEAT / 4, .05)
        if i % 2 == 1:
            place(drums, st(clap(), 0), bt, .26 if drop else .2)
        if build:   # roulement qui se resserre vers le drop
            for q in (.25, .5, .75) if bt > M["build"] + .6 else (.5,):
                place(drums, st(clap(), 0), bt + q * BEAT, .07 + .1 * (bt - M["build"]) / 1.3)
        if bt >= M["bass"]:
            root = ROOT[chord_at(bt)]
            placem(low, bassnote(midi(root), BEAT * .9), bt + (0 if drop else BEAT / 2), .5 if drop else .38)
            if drop:
                placem(low, bassnote(midi(root + 12), BEAT * .4), bt + BEAT / 2, .25)
    pad *= sc[:, None] ** .7
    low *= sc
    mus = pad + arp + drums + st(low)
    mus += reverb(pad * .5 + arp * .9 + drums * .12, 2.4, 5200, seed=5) * .3
    # intro : passe-bas qui s'ouvre de 400 Hz à 20 kHz sur 6 s
    i6 = int(M["groove"] * SR)
    mus[:i6] = sweep_filter(mus[:i6], "lowpass", lambda t: 400 * (20000 / 400) ** min(1, t / M["groove"]))
    # montée : passe-haut qui grimpe, puis 100 ms de silence avant le drop
    a, b = int(M["build"] * SR), int(M["silence"] * SR)
    mus[a:b] = sweep_filter(mus[a:b], "highpass", lambda t: 30 * (900 / 30) ** ((t - M["build"]) / (M["silence"] - M["build"])), t0=M["build"])
    mus[b:int(M["drop"] * SR)] *= 0.0
    c, d = int(M["nearsilence"] * SR), int(M["outro"] * SR)
    mus[c:d] *= .03
    # creux de 2 dB entre 2 et 4 kHz pour laisser la place aux sons d'interface
    mus = peaking(mus, 2800, -2.0, .8)
    # niveaux relatifs : intro et outro calmes, drop fort
    lv = np.ones(N)
    tt = np.arange(N) / SR
    lv *= np.where(tt < M["groove"], .55, 1.0)
    lv *= np.where((tt >= M["drop"]) & (tt < M["nearsilence"]), 1.28, 1.0)
    lv *= np.where(tt >= M["outro"], .6, 1.0)
    return mus * lv[:, None]


# ============================================================ bruitages
def noise(d):
    return rng.standard_normal(len(T(d)))


def click_core(d=.012, f=(2500, 9000)):
    t = T(d)
    return filt(rng.standard_normal(len(t)), "bandpass", list(f)) * np.exp(-t * 500)


def tick(f=2300, d=.04):
    t = T(d)
    return add(np.sin(2 * np.pi * f * t) * np.exp(-t * 110) * np.minimum(1, t / .0008), .25 * click_core(min(d, .012)))


def blip(f0, f1, d, dec=35, h2=.25):
    t = T(d)
    f = f1 + (f0 - f1) * np.exp(-t * 50)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + h2 * np.sin(2 * ph)) * np.exp(-t * dec) * np.minimum(1, t / .0015)


def thud(f=110, d=.12):
    t = T(d)
    v = np.sin(2 * np.pi * np.cumsum(f * (1 + .6 * np.exp(-t * 60))) / SR) * np.exp(-t * 28)
    return v + filt(rng.standard_normal(len(t)), "lowpass", 900) * np.exp(-t * 60) * .5


def bell(f, d=.6, dec=4.0):
    t = T(d)
    v = np.zeros(len(t))
    for ratio, amp, k in ((1, 1, 1), (2.0, .38, 1.6), (3.0, .16, 2.4), (4.16, .1, 3.2), (5.43, .05, 4.5)):
        v += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * dec * k)
    return v * np.minimum(1, t / .0015)


def whoosh_noise(d, f0, f1, f2, peak=.5, bw=1.0):
    t = T(d)
    n = rng.standard_normal(len(t))
    def fc(tt):
        x = tt / d
        return f0 * (f1 / f0) ** (x / peak) if x < peak else f1 * (f2 / f1) ** ((x - peak) / (1 - peak))
    lo = sweep_filter(n[:, None], "lowpass", lambda tt: fc(tt) * (1 + bw))[:, 0]
    v = sweep_filter(lo[:, None], "highpass", lambda tt: fc(tt) / (1 + bw))[:, 0]
    x = t / d
    e = np.where(x < peak, (x / peak) ** 2.2, np.exp(-np.minimum((x - peak) / max(1 - peak, 1e-3), 40) * 4.5))
    return v * e


def sfx_typing(d, rate=(.045, .085)):
    out = np.zeros((int((d + .1) * SR), 2))
    tt = 0.0
    while tt < d:
        t = T(.03)
        k = filt(rng.standard_normal(len(t)), "bandpass", [1400, 5200]) * np.exp(-t * 300) + np.sin(2 * np.pi * 150 * t) * np.exp(-t * 150) * .35
        place(out, st(k, rng.uniform(-.25, .25)), tt, rng.uniform(.55, 1))
        tt += rng.uniform(*rate)
    return out


def make(c):
    ty, d, k = c["type"], float(c["dur"]), int(c.get("k", 0))
    pan = c["pan"]
    p0, p1 = (pan, pan) if not isinstance(pan, list) else pan
    kind = "ui"
    if ty == "scrollticks":
        x = np.zeros((int((d + .05) * SR), 2))
        for j in range(int(d * 20)):
            place(x, st(filt(tick(3200, .015), "highpass", 2000), rng.uniform(-.2, .2)), j / 20 + rng.uniform(0, .01), rng.uniform(.6, 1))
    elif ty == "revcymbal":
        t = T(d)
        v = filt(rng.standard_normal(len(t)), "highpass", 3500) * np.exp(-t[::-1] * 7) * (t / d) ** 1.5
        x, kind = st(v), "fx"
    elif ty == "lock":
        x, kind = st(add(click_core(.02, (2000, 8000)) * 1.2, thud(80, .12) * 1.4)), "fx"
    elif ty == "micropop":
        x = st(blip(1300, 700, .03, 90), p0)
    elif ty == "signature":
        x = np.zeros((int(.75 * SR), 2))
        place(x, st(bell(midi(76), .7, 3.2), -.15), 0)            # mi 5
        place(x, st(bell(midi(83), .7, 3.0), .15), .12, .9)       # si 5 : la quinte au-dessus
        kind = "chime"
    elif ty == "riser":
        t = T(d)
        v = whoosh_noise(d, 300, 7000, 7000, .999, .6)
        v += np.sin(2 * np.pi * np.cumsum(220 * 5 ** (t / d)) / SR) * (t / d) ** 2 * .25
        v *= 10 ** ((-6 + 6 * (t / d)) / 20)                    # −20 → −14 dBFS
        w = (t / d) ** 1.5                                        # le champ s'élargit
        dec = filt(rng.standard_normal(len(t)), "highpass", 2000) * (t / d) ** 3 * .15
        x, kind = np.stack([v + dec * w, v - dec * w], axis=1), "fx"
    elif ty == "sub":
        t = T(d)
        x, kind = st(np.sin(2 * np.pi * 50 * t) * np.exp(-t * 7) * np.minimum(1, t / .004)), "sub"
    elif ty == "tick":
        x = st(tick(2200, .04), p0)
    elif ty == "softpop":
        x = st(blip(650, 420, .08, 40), p0)
    elif ty == "air":
        v = whoosh_noise(d, 250, 1800, 600, .55, .8)
        x, kind = st_sweep(v, p0, p1), "fx"
    elif ty == "accelticks":
        x = np.zeros((int((d + .1) * SR), 2))
        tt, gap, f = 0.0, .13, 2000
        while tt < d:
            place(x, st(tick(f, .03)), tt, .6 + .4 * tt / d)
            tt += gap
            gap = max(.03, gap * .82)
            f += 40
    elif ty == "bell":
        x, kind = st(bell(midi(96), d, 7)), "chime"           # do 7 : aiguë et brève
    elif ty in ("whoosh", "whoosh_back"):
        v = whoosh_noise(d, 300, 3500 if ty == "whoosh" else 2200, 500, .55 if ty == "whoosh" else .35, 1.1)
        x, kind = st_sweep(v, -.3, .3) if ty == "whoosh" else st(v), "fx"
    elif ty == "snap":
        t = T(d)
        v = click_core(.025, (1500, 9000)) * 1.5
        v = np.pad(v, (0, len(t) - len(v)))
        v += np.sin(2 * np.pi * 420 * t) * np.exp(-t * 90) * .5
        x, kind = st(v), "fx"
    elif ty == "typing":
        x = sfx_typing(d)
        x = x * np.array([np.cos((p0 + 1) * np.pi / 4), np.sin((p0 + 1) * np.pi / 4)]) * 1.41
    elif ty == "pop":
        x = st(blip(1050, 560, .07, 45), p0)
    elif ty == "toggle":
        a = click_core(.012, (3000, 9000))
        b = thud(160, .08) * .8
        v = np.zeros(int(.09 * SR))
        v[:len(a)] += a
        v[int(.018 * SR):int(.018 * SR) + len(b)] += b[: len(v) - int(.018 * SR)]
        x = st(v, p0)
    elif ty == "microticks":
        x = np.zeros((int((d + .05) * SR), 2))
        for j in range(16):
            u = j / 16
            place(x, st(tick(2600, .015)), d * (1 - (1 - u) ** 2.2), .4 + .6 * (1 - u))
    elif ty == "swish":
        v = whoosh_noise(d, 900, 7000, 2500, .5, .7)
        x, kind = st_sweep(v, p0, p1), "fx"
    elif ty == "thud":
        x = st(thud(105, d), p0)
    elif ty == "glass":
        t = T(d)
        f = rng.uniform(2800, 3400)
        v = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * dd) for r, a, dd in ((1, 1, 40), (1.51, .6, 55), (2.27, .35, 70)))
        c6 = click_core(.006, (5000, 12000))
        v[:len(c6)] += c6 * .3
        x = st(v, p0)
    elif ty == "magnet":
        t = T(d)
        v = blip(140, 260, d, 30, .1) * .9
        v[: int(.012 * SR)] += click_core(.012, (2500, 8000))
        x = st(v)
    elif ty == "flip":
        v = whoosh_noise(d, 400, 4000, 700, .5, 1.0)
        tk = np.zeros(len(v))
        tc = tick(2600, .03)
        i = int(.3 * SR)
        tk[i:i + len(tc)] = tc
        x, kind = st(v + tk * .5), "fx"
    elif ty == "zip":
        t = T(d)
        v = sweep_filter(rng.standard_normal(len(t))[:, None], "lowpass", lambda tt: 800 * 8 ** (tt / d))[:, 0]
        v = filt(v, "highpass", 600) * np.sin(np.pi * t / d) ** .8
        x = st_sweep(v, p0, p1)
    elif ty in ("sparkle", "sparkle_soft"):
        x = np.zeros((int((d + .3) * SR), 2))
        n = 26 if ty == "sparkle" else 10
        for j in range(n):
            u = j / n
            f = midi(int(rng.choice([84, 86, 88, 91, 93, 96])))
            pan_j = lerp(p0, p1, u) if ty == "sparkle" else rng.uniform(-.4, .4)
            place(x, st(bell(f, .3, 14), pan_j), d * u + rng.uniform(0, .02), rng.uniform(.4, 1))
    elif ty == "send":
        t = T(d)
        v = whoosh_noise(d, 1200, 6000, 6000, .8, .6)
        v += blip(700, 1100, d, 18, 0) * .25
        x = st(v, p0)
    elif ty == "receive":
        x = np.zeros((int(d * SR), 2))
        place(x, st(blip(880, 860, .1, 40, .15), p0), 0)
        place(x, st(blip(660, 650, .1, 40, .15), p0), .07, .9)
    elif ty == "writing":
        t = T(d)
        am = np.abs(filt(rng.standard_normal(len(t)), "lowpass", 18)) * 6
        v = filt(rng.standard_normal(len(t)), "bandpass", [2500, 7000]) * np.clip(am, 0, 1.5) * env_ar(len(t), .1, .15)
        x = st(v, p0)
    elif ty == "click":
        t = T(d)
        v = click_core(.01, (2000, 9000)) * 1.3
        v = np.pad(v, (0, len(t) - len(v))) + np.sin(2 * np.pi * 180 * t) * np.exp(-t * 120) * .35
        x = st(v, p0)
    elif ty in ("pluck_soft", "pluck_up"):
        scale = [69, 72, 74, 76, 79, 81, 84, 86]
        m = scale[k % len(scale)] if ty == "pluck_soft" else [72, 74, 76, 79, 83, 84][k % 6]
        x = st(pluck(midi(m), .5, .8), p0)
    elif ty == "countticks":
        x = np.zeros((int((d + .05) * SR), 2))
        for j in range(12):
            u = j / 12
            place(x, st(tick(1900 + 60 * j, .02), p0), d * (1 - (1 - u) ** (1 / 3)), .8 - .4 * u)
    elif ty == "riser_snare":
        t = T(d)
        v = whoosh_noise(d, 400, 9000, 9000, .999, .5)
        v *= 10 ** ((-8 + 8 * (t / d)) / 20)
        sn = filt(rng.standard_normal(len(t)), "bandpass", [700, 5000]) * np.exp(-(d - t) * 9) * (t / d) ** 2   # caisse claire inversée
        w = (t / d) ** 1.5
        dec = filt(rng.standard_normal(len(t)), "highpass", 2500) * (t / d) ** 3 * .2
        x, kind = np.stack([v + sn * .8 + dec * w, v + sn * .8 - dec * w], axis=1), "fx"
    elif ty == "drop":
        t = T(1.6)
        f = 34 + 55 * np.exp(-t * 7)
        v = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4) * np.minimum(1, t / .003)
        nz = filt(rng.standard_normal(len(t)), "lowpass", 2500) * np.exp(-t * 11) * .5
        x, kind = np.stack([v + nz, v + nz * .9], axis=1), "impact"
    elif ty == "whoomp":
        t = T(d)
        v = sweep_filter(rng.standard_normal(len(t))[:, None], "lowpass", lambda tt: 3500 * (180 / 3500) ** (tt / d))[:, 0] * env_ar(len(t), .03, .5)
        v += np.sin(2 * np.pi * np.cumsum(150 * (55 / 150) ** (t / d)) / SR) * np.exp(-t * 3) * .7
        x, kind = st(v), "impact"
    elif ty == "shimmer":
        x = np.zeros((int((d + .6) * SR), 2))
        for j, m in enumerate([84, 88, 91, 95, 96]):
            place(x, st(bell(midi(m), .9, 4), lerp(p0, p1, j / 4) if isinstance(pan, list) else (-1) ** j * .35), j * .05, .7)
        kind = "chime"
    elif ty == "revwhoosh":
        t = T(d)
        v = whoosh_noise(d, 300, 6000, 6000, .999, .8) * (t / d) ** 1.4
        wid = (1 - t / d) ** 1.2                                  # se resserre au centre
        dec = filt(rng.standard_normal(len(t)), "highpass", 2000) * (t / d) * .25
        x, kind = np.stack([v + dec * wid, v - dec * wid], axis=1), "fx"
        x[-int(.004 * SR):] *= np.linspace(1, 0, int(.004 * SR))[:, None]   # coupé net
    elif ty == "impact_light":
        t = T(d)
        v = add(thud(70, d) * 1.2, click_core(.01, (1500, 6000)) * .5)
        x, kind = st(v, p0), "impact"
    else:
        raise ValueError(ty)
    return x, kind


def lerp(a, b, p):
    return a + (b - a) * p


def sfx():
    ui = np.zeros((N, 2))
    fx = np.zeros((N, 2))
    duck = np.zeros(N)
    for c in data["cues"]:
        x, kind = make(c)
        x = norm_peak(x, c["peak"])
        t = c["t"]
        if kind in ("ui", "chime"):
            place(ui, x, t)
        else:
            place(fx, x, t)
        if kind in ("chime", "impact", "sub") or c["type"] == "lock":
            i0, i1 = int(t * SR), int((t + min(c["dur"], .6)) * SR)
            duck[i0:i1] = 1
    ui = filt(ui, "highpass", 120)
    ui = ui + reverb(ui, .6, 7000, .004, seed=9) * .10 / .3   # pièce courte, ~10 % d'envoi
    fx = filt(fx, "highpass", 40)
    lowf = filt(fx.mean(axis=1), "lowpass", 120)               # subs en mono
    fx = fx - filt(fx, "lowpass", 120) + lowf[:, None]
    return ui + fx, duck


def ducking(flag, depth_db=3.5, att=.005, rel=.15):
    g = np.ones(len(flag))
    target = 10 ** (-depth_db / 20)
    a, r = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR))
    cur = 1.0
    out = np.empty(len(flag))
    for i, f in enumerate(flag):
        tgt = target if f else 1.0
        k = a if tgt < cur else r
        cur = tgt + (cur - tgt) * k
        out[i] = cur
    return out


# ================================================================ maître
def lufs_tp(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    i = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    return i, tp


def softclip(x, knee=.55, ceil=.97):
    """écrêteur à genou doux : linéaire sous le genou, arrondi au-dessus (avant le limiteur)"""
    a = np.abs(x)
    over = a > knee
    y = x.copy()
    y[over] = np.sign(x[over]) * (knee + (ceil - knee) * np.tanh((a[over] - knee) / (ceil - knee)))
    return y


def limiter(x, ceiling_db=-1.3, look=.003, rel=.08):
    """limiteur à anticipation, détection de crête sur-échantillonnée ×4 (crête vraie)"""
    up = signal.resample_poly(x, 4, 1, axis=0)
    pk = np.abs(up).max(axis=1).reshape(-1, 4).max(axis=1)[: len(x)]
    c = 10 ** (ceiling_db / 20)
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    w = int(look * SR)
    need = ndimage.minimum_filter1d(need, 2 * w + 1)
    need = np.minimum(need, ndimage.uniform_filter1d(need, w))
    g = np.empty_like(need)
    cur, r = 1.0, np.exp(-1 / (rel * SR))
    for i, n in enumerate(need):
        cur = n if n < cur else n + (cur - n) * r
        g[i] = cur
    return x * g[:, None], 20 * np.log10(g.min())


def write_wav24(path, x):
    pcm = np.clip(x, -1, 1 - 2 ** -23)
    q = np.round(pcm * (2 ** 23)).astype(np.int32)
    b = np.empty((q.size, 3), dtype=np.uint8)
    flat = q.reshape(-1)
    b[:, 0] = flat & 0xFF
    b[:, 1] = (flat >> 8) & 0xFF
    b[:, 2] = (flat >> 16) & 0xFF
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(b.tobytes())


def main():
    mus = music()
    fx, duck = sfx()
    mus *= ducking(duck)[:, None]
    mix = mus * .9 + fx * 1.0
    end = int(DUR * SR)
    mix = mix[:end]
    # queue jusqu'à −60 dB à 1:00
    tail = int(1.2 * SR)
    mix[-tail:] *= (10 ** (-60 / 20)) ** (np.linspace(0, 1, tail) ** 2)[:, None]
    tmp = OUT / "audio_tmp.wav"
    gain = 1.0
    for it in range(4):
        y, gr = limiter(softclip(mix * gain))
        write_wav24(tmp, y)
        i, tp = lufs_tp(tmp)
        print(f"passe {it}: {i:.1f} LUFS, crête vraie {tp:.1f} dBTP, réduction max {gr:.1f} dB")
        if abs(i + 14) < .3 and tp <= -1.0:
            break
        gain *= 10 ** ((-14 - i) / 20)
    tmp.replace(OUT / "audio.wav")
    print("audio ->", OUT / "audio.wav")


if __name__ == "__main__":
    main()
