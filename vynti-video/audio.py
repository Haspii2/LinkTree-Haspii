"""Bande-son 100 % synthétisée (aucun sample externe, libre de droits).

- musique : nappe (Am7 – Fmaj7 – Cmaj7 – G6), arpège pluck, basse, groove doux à 120 BPM
- bruitages calés sur out/cues.json (exporté par render.mjs depuis la timeline de scene.html)

    python3 audio.py  ->  out/audio.wav
"""
import json
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
DIR = Path(__file__).resolve().parent
OUT = DIR / "out"
data = json.loads((OUT / "cues.json").read_text())
DUR = data["duration"]
N = int((DUR + 3) * SR)
rng = np.random.default_rng(7)

BPM = 120
BEAT = 60 / BPM
SC = data["scenes"]


def q(t):
    return round(t / BEAT) * BEAT


# repères musicaux calés sur la timeline : drop à l'arrivée du fil d'actualité,
# coupure juste avant le mur de captures, accord final sur le logo
DROP = q(SC["s2"][0] + .2)
BREAK_A, BREAK_B = q(SC["s7"][0] - .3), q(SC["s7"][0] + .2)
OUTRO = q(SC["s8"][0])


def T(d):
    return np.arange(int(d * SR)) / SR


def sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output="sos")


def filt(x, kind, f, order=2):
    return signal.sosfilt(sos(kind, f, order), x, axis=0)


def stereo(x, pan=0.0):
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def place(bus, x, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(bus):
        return
    if x.ndim == 1:
        x = stereo(x)
    j = min(len(bus), i + len(x))
    if i < 0:
        x, i = x[-i:], 0
    bus[i:j] += x[: j - i] * gain


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def adsr(n, a, r, total):
    env = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    env[:na] = np.linspace(0, 1, na) ** 1.5
    if nr:
        env[-nr:] *= np.linspace(1, 0, nr) ** 2
    return env


def reverb(x, secs=2.4, tone=5500, wet=1.0):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t * 6.9 / secs)[:, None]
    ir = filt(ir, "lowpass", tone)
    ir[: int(.012 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(axis=0))
    y = np.stack([signal.fftconvolve(x[:, k], ir[:, k])[: len(x)] for k in range(2)], axis=1)
    return y * wet


# ------------------------------------------------------------------ musique
CHORDS = {
    "Am7": [57, 60, 64, 67], "Fmaj7": [53, 57, 60, 64], "Cmaj7": [48, 55, 59, 64], "G6": [55, 59, 62, 64],
    "Cmaj9": [48, 55, 59, 62, 64, 67],
}
ROOT = {"Am7": 45, "Fmaj7": 41, "Cmaj7": 48, "G6": 43, "Cmaj9": 36}
PROG = ["Am7", "Fmaj7", "Cmaj7", "G6"]


def chord_at(t):
    if t >= OUTRO:
        return "Cmaj9"
    return PROG[int(t // (4 * BEAT)) % 4]


def pad_note(f, d):
    t = T(d)
    x = np.zeros((len(t), 2))
    for det, pan in ((-0.09, -.7), (0.0, 0.0), (0.09, .7)):
        ff = f * 2 ** (det / 12)
        v = np.zeros(len(t))
        for k in range(1, 9):
            v += np.sin(2 * np.pi * ff * k * t + rng.uniform(0, 6.28)) / k ** 1.3
        x += stereo(v, pan)
    return x


def pluck(f, d=0.9):
    t = T(d)
    v = (np.sin(2 * np.pi * f * t + 1.2 * np.exp(-t * 18) * np.sin(2 * np.pi * 2 * f * t))
         + .35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 14))
    env = np.exp(-t * 5.5) * np.minimum(1, t / .003)
    return v * env


def kick():
    t = T(.5)
    f = 46 + 120 * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    v = np.sin(ph) * np.exp(-t * 6.5)
    v += filt(rng.standard_normal(len(t)), "bandpass", [1500, 6000]) * np.exp(-t * 260) * .25
    return v


def hat():
    t = T(.07)
    return filt(rng.standard_normal(len(t)), "highpass", 7500) * np.exp(-t * 70)


def clap():
    t = T(.35)
    env = np.exp(-t * 16)
    for o in (0, .011, .022):
        env += .6 * np.exp(-np.maximum(t - o, 0) * 180) * (t >= o)
    return filt(rng.standard_normal(len(t)), "bandpass", [900, 3200]) * env * .5


def bass(f, d=.22):
    t = T(d)
    v = np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t)
    return v * np.minimum(1, t / .004) * np.exp(-t * 4) * adsr(len(t), .004, .05, d)


def music():
    pad = np.zeros((N, 2))
    arp = np.zeros((N, 2))
    drums = np.zeros((N, 2))
    low = np.zeros((N, 2))
    bar = 4 * BEAT
    # nappe : un accord par mesure, enveloppes qui se chevauchent
    nbars = int(OUTRO // bar) + 1
    for b in range(nbars):
        t0 = b * bar
        if t0 >= OUTRO:
            break
        name = chord_at(t0)
        d = min(bar + 1.2, OUTRO - t0 + .9)
        for m in CHORDS[name]:
            x = pad_note(midi(m), d) * adsr(int(d * SR), .5, .9, d)[:, None]
            place(pad, x, t0, .055)
    # accord final
    d = DUR - OUTRO + 2.5
    for m in CHORDS["Cmaj9"]:
        x = pad_note(midi(m), d) * adsr(int(d * SR), .25, 2.2, d)[:, None]
        place(pad, x, OUTRO, .06)
    pad = filt(filt(pad, "lowpass", 2300), "highpass", 140)
    # arpège (croches), à partir de l'accroche
    pattern = [0, 2, 1, 3, 2, 1, 3, 2]
    t = 3.0
    k = 0
    while t < OUTRO - .01:
        notes = CHORDS[chord_at(t)]
        m = notes[pattern[k % 8] % len(notes)] + 12
        g = .11 * (0.85 if k % 2 else 1.0) * (0.7 if BREAK_A <= t < BREAK_B else 1)
        place(arp, stereo(pluck(midi(m)), -.35 if k % 2 else .35), t, g)
        t += BEAT / 2
        k += 1
    # groove
    sidechain = np.ones(N)
    beat_times = np.arange(DROP, OUTRO - 1e-6, BEAT)
    for i, bt in enumerate(beat_times):
        if BREAK_A <= bt < BREAK_B:
            continue
        place(drums, kick(), bt, .5)
        sc_t = T(.45)
        i0 = int(bt * SR)
        seg = 1 - .55 * np.exp(-sc_t * 9)
        sidechain[i0:i0 + len(seg)] = np.minimum(sidechain[i0:i0 + len(seg)], seg[: len(sidechain[i0:i0 + len(seg)])])
        place(drums, stereo(hat(), .25), bt + BEAT / 2, .16)
        if i % 2 == 1:
            place(drums, clap(), bt, .22)
        root = ROOT[chord_at(bt)]
        place(low, bass(midi(root)), bt + BEAT / 2, .30)
    # légère montée avant le mur
    t = T(1.4)
    riser = filt(rng.standard_normal(len(t)), "highpass", 2500) * (t / 1.4) ** 3
    place(drums, stereo(riser), BREAK_A - 1.4 + .05, .12)

    pad *= sidechain[:, None] ** .6
    low *= sidechain[:, None]
    # fondu d'entrée
    fade = np.clip(np.arange(N) / (2.5 * SR), 0, 1)[:, None] ** 2
    pad *= fade
    mix = pad + arp + drums + low
    mix += reverb(pad * .5 + arp * .8 + drums * .15, 2.8, 5000, .35)
    return mix


# ----------------------------------------------------------------- bruitages
def sweep_noise(d, f0, f1, f2, peak=.4, q_bw=1.0):
    """bruit filtré dont la fréquence centrale monte puis redescend (whoosh)"""
    t = T(d)
    n = rng.standard_normal(len(t))
    out = np.zeros(len(t))
    blk = 256
    zi = None
    for i in range(0, len(t), blk):
        x = i / len(t)
        fc = f0 * (f1 / f0) ** (x / peak) if x < peak else f1 * (f2 / f1) ** ((x - peak) / (1 - peak))
        lo, hi = fc / (1 + q_bw), min(fc * (1 + q_bw), SR / 2 - 100)
        s_ = sos("bandpass", [lo, hi], 1)
        if zi is None:
            zi = np.zeros((s_.shape[0], 2))
        out[i:i + blk], zi = signal.sosfilt(s_, n[i:i + blk], zi=zi)
    env = np.where(t / d < peak, (t / (d * peak)) ** 2.2, np.exp(-((t / d - peak) / (1 - peak)) * 4.5))
    return out * env


def whoosh(d=.75):
    x = sweep_noise(d, 250, 3200, 500, .55, 1.2)
    pans = np.linspace(-.6, .6, len(x))
    a = (pans + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1) * 1.3


def swish():
    x = sweep_noise(.4, 1200, 7000, 2500, .5, .8)
    return stereo(x * 1.1, .15)


def pop():
    t = T(.18)
    f = 520 + 700 * np.exp(-t * 55)
    v = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32) * np.minimum(1, t / .002)
    v += .3 * np.sin(2 * np.pi * np.cumsum(2 * f) / SR) * np.exp(-t * 60)
    return stereo(v * .55, rng.uniform(-.3, .3))


def click():
    t = T(.05)
    v = filt(rng.standard_normal(len(t)), "bandpass", [2000, 7000]) * np.exp(-t * 400) * .6
    v += np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 180) * .35
    v += np.sin(2 * np.pi * 180 * t) * np.exp(-t * 90) * .3
    return stereo(v, .1)


def tick(f=2400):
    t = T(.06)
    v = np.sin(2 * np.pi * f * t) * np.exp(-t * 90) * np.minimum(1, t / .001)
    return stereo(v * .32)


def key_click():
    t = T(.03)
    v = filt(rng.standard_normal(len(t)), "bandpass", [1500, 5500]) * np.exp(-t * 320)
    v += np.sin(2 * np.pi * 140 * t) * np.exp(-t * 160) * .4
    return stereo(v * .35, rng.uniform(-.25, .25))


def bell(f, d=1.6):
    t = T(d)
    v = np.zeros(len(t))
    for ratio, amp, dec in ((1, 1, 3.2), (2.0, .4, 5), (3.01, .22, 7), (4.2, .12, 10), (5.43, .06, 14)):
        v += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * dec)
    return v * np.minimum(1, t / .002)


def chime():
    x = np.zeros((int(1.8 * SR), 2))
    place(x, stereo(bell(midi(88)) * .28, -.2), 0)
    place(x, stereo(bell(midi(95)) * .24, .2), .085)
    return x


def shimmer():
    x = np.zeros((int(2.0 * SR), 2))
    for i, m in enumerate([76, 83, 88, 91]):
        place(x, stereo(bell(midi(m), 1.6) * .1, (-1) ** i * .4), i * .035)
    return x


def impact():
    t = T(1.8)
    f = 36 + 50 * np.exp(-t * 6)
    v = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6) * np.minimum(1, t / .003)
    v += filt(rng.standard_normal(len(t)), "lowpass", 1800) * np.exp(-t * 14) * .45
    return stereo(v * .9)


def rise(d):
    t = T(d)
    n = filt(rng.standard_normal(len(t)), "highpass", 1500) * (t / d) ** 2.5 * .5
    f = 300 * (6 ** (t / d))
    v = n + np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / d) ** 3 * .18
    return stereo(v)


def count(d, g):
    x = np.zeros((int((d + .2) * SR), 2))
    k = 14
    for i in range(1, k + 1):
        u = i / k
        tt = d * (1 - (1 - u) ** (1 / 3)) if u < 1 else d
        place(x, tick(1900 + 40 * i), tt, .55 * (1 - .4 * u))
    return x


def sfx():
    bus = np.zeros((N, 2))
    send = np.zeros((N, 2))
    for c in data["cues"]:
        ty, t, g, d = c["type"], c["t"], c["g"], c.get("d", 0)
        if ty == "whoosh":
            x = whoosh()
            t -= .35  # le pic du whoosh tombe sur le mouvement
            rv = .5
        elif ty == "swish":
            x, rv = swish(), .4
            t -= .12
        elif ty == "pop":
            x, rv = pop(), .4
        elif ty == "click":
            x, rv = click(), .2
        elif ty == "tick":
            x, rv = tick(), .3
        elif ty == "chime":
            x, rv = chime(), .8
        elif ty == "shimmer":
            x, rv = shimmer(), 1.0
        elif ty == "impact":
            x, rv = impact(), .6
        elif ty == "rise":
            x, rv = rise(d), .5
        elif ty == "count":
            x, rv = count(d, g), .2
        elif ty == "typing":
            x = np.zeros((int((d + .1) * SR), 2))
            tt = 0.0
            while tt < d:
                place(x, key_click(), tt, rng.uniform(.6, 1))
                tt += rng.uniform(.045, .085)
            rv = .15
        else:
            continue
        place(bus, x, t, g)
        place(send, x, t, g * rv)
    return bus + reverb(send, 1.8, 6500, .45)


def main():
    m = music()
    s = sfx()
    mix = m * .75 + s * .9
    # fondu de sortie
    end = int(DUR * SR)
    fo = int(1.6 * SR)
    mix[end - fo:end] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    mix = mix[:end]
    # compression douce + normalisation
    peak = np.max(np.abs(mix))
    mix = mix / peak * 1.25
    mix = np.tanh(mix) / np.tanh(1.25) * 10 ** (-1.2 / 20)
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
    with wave.open(str(OUT / "audio.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("audio ->", OUT / "audio.wav", f"{len(pcm) / SR:.2f}s")


if __name__ == "__main__":
    main()
