"""Synthesise the 30 s percussion bed (assets/audio/bed.wav) with numpy only.

120 BPM, one beat = 0.5 s = 15 frames at 30 fps. Section times match SPEC.md:
  0.0 - 9.75  tension: clock ticks (accelerating), heartbeat sub, rising drone
  9.75 - 10.0 silence before the reveal
  10.0        trailer boom (NEXUS reveal)
  12.0 - 22.5 groove: kick / clap / hats / pumping sub-bass
  22.5 - 23.0 drop-out (hold before the payoff)
  23.0        boom (savings land), groove returns with 16th hats
  26.0 - 26.9 snare roll build, 26.9 - 27.0 gap
  27.0        final boom (end card), low tail fades out by 30.0

Effects with a picture cause (glitch, whooshes, pops, riser) are placed as their own <audio>
clips in index.html, not baked in here.
"""
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000
DUR = 30.0
N = int(SR * DUR)
BEAT = 0.5
rng = np.random.default_rng(20261125)  # seeded: the bed is identical on every build


def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


def lp_hp(x, lo=None, hi=None, order=2):
    """Zero-phase Butterworth-shaped FFT filter. lo = high-pass corner, hi = low-pass corner."""
    n = len(x)
    size = 1 << int(np.ceil(np.log2(max(n, 2))))
    X = np.fft.rfft(x, size)
    f = np.fft.rfftfreq(size, 1 / SR)
    H = np.ones_like(f)
    if hi:
        H *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    if lo:
        with np.errstate(divide="ignore"):
            H *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-6)) ** (2 * order))
    return np.fft.irfft(X * H, size)[:n]


def env_exp(sec, decay, attack=0.002):
    t = t_axis(sec)
    a = np.minimum(t / attack, 1.0) if attack > 0 else 1.0
    return a * np.exp(-t / decay)


def db(v):
    return 10 ** (v / 20)


class Bus:
    def __init__(self):
        self.L = np.zeros(N)
        self.R = np.zeros(N)

    def add(self, sig, at, gain=1.0, pan=0.0):
        i = int(round(at * SR))
        if i >= N:
            return
        # every voice ends on a 30 ms fade so no buffer edge clicks
        f = min(len(sig), int(0.03 * SR))
        sig = sig.copy()
        sig[-f:] *= np.linspace(1, 0, f)
        sig = sig[: N - i]
        gl = gain * np.sqrt(0.5 * (1 - pan))
        gr = gain * np.sqrt(0.5 * (1 + pan))
        self.L[i : i + len(sig)] += sig * gl * np.sqrt(2)
        self.R[i : i + len(sig)] += sig * gr * np.sqrt(2)


dry = Bus()
verb_send = Bus()

# ---------------------------------------------------------------- voices


def tick(high=True):
    sec = 0.12
    t = t_axis(sec)
    f = 2600 if high else 1900
    body = np.sin(2 * np.pi * f * t) * env_exp(sec, 0.014, 0.0005)
    wood = np.sin(2 * np.pi * (1050 if high else 820) * t) * env_exp(sec, 0.028, 0.0005)
    click = lp_hp(rng.standard_normal(len(t)), lo=2500) * env_exp(sec, 0.003, 0.0002)
    return 0.55 * body + 0.8 * wood + 0.5 * click


def thump(f0=90, f1=48, decay=0.2):
    sec = decay * 5
    t = t_axis(sec)
    f = f1 + (f0 - f1) * np.exp(-t / 0.04)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env_exp(sec, decay, 0.003)
    return np.tanh(2.2 * s) / np.tanh(2.2)  # harmonics so it survives small speakers


def kick():
    sec = 1.1
    t = t_axis(sec)
    f = 46 + 150 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env_exp(sec, 0.28, 0.001)
    click = lp_hp(rng.standard_normal(len(t)), lo=1800, hi=9000) * env_exp(sec, 0.004, 0.0002)
    s = np.tanh(1.8 * body) / np.tanh(1.8) + 0.35 * click
    return s


def clap():
    sec = 0.35
    t = t_axis(sec)
    noise = lp_hp(rng.standard_normal(len(t)), lo=900, hi=5200)
    e = np.zeros_like(t)
    for k, off in enumerate((0.0, 0.011, 0.022)):
        i = int(off * SR)
        e[i:] += (0.8 if k < 2 else 1.0) * np.exp(-(t[i:] - off) / (0.008 if k < 2 else 0.11))
    return noise * e * 0.6


def hat(decay=0.03):
    sec = decay * 6
    t = t_axis(sec)
    return lp_hp(rng.standard_normal(len(t)), lo=7000) * env_exp(sec, decay, 0.0005) * 0.5


def snare(level=1.0):
    sec = 0.2
    t = t_axis(sec)
    tone = np.sin(2 * np.pi * 190 * t) * env_exp(sec, 0.04)
    noise = lp_hp(rng.standard_normal(len(t)), lo=1500, hi=9000) * env_exp(sec, 0.06)
    return level * (0.5 * tone + 0.7 * noise)


def boom(decay=2.6, f0=150, f1=36):
    sec = decay * 4.0
    t = t_axis(sec)
    f = f1 + (f0 - f1) * np.exp(-t / 0.25)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * env_exp(sec, decay, 0.004)
    sub = np.tanh(1.6 * sub) / np.tanh(1.6)
    crack = lp_hp(rng.standard_normal(len(t)), lo=300, hi=6000) * env_exp(sec, 0.05, 0.0005)
    rumble = lp_hp(rng.standard_normal(len(t)), hi=180, order=3) * env_exp(sec, decay * 0.6, 0.01)
    rumble /= np.max(np.abs(rumble)) + 1e-9
    return sub + 0.55 * crack + 0.35 * rumble


def saw(freq, sec):
    t = t_axis(sec)
    ph = (freq * t) % 1.0
    return 2 * ph - 1


# ---------------------------------------------------------------- tension 0 - 9.75

# clock: quarter notes to 7.0, eighths to 9.0, sixteenths to 9.75
times = list(np.arange(0.0, 7.0, BEAT)) + list(np.arange(7.0, 9.0, BEAT / 2)) + list(np.arange(9.0, 9.75, BEAT / 4))
for k, tt in enumerate(times):
    lvl = db(-3) * (1 + 0.4 * max(0.0, (tt - 5.0) / 4.75))
    dry.add(tick(high=(k % 2 == 0)), tt, lvl, pan=(-0.25 if k % 2 == 0 else 0.25))
    verb_send.add(tick(high=(k % 2 == 0)), tt, lvl * 0.5)

# heartbeat: lub-dub every second from 4.5 to 9.5
for tt in np.arange(4.5, 9.5, 1.0):
    dry.add(thump(95, 50, 0.16), tt, db(-8))
    dry.add(thump(80, 46, 0.14), tt + 0.24, db(-12))

# drone 0 - 9.75, swelling, hard stop with 20 ms fade
dsec = 9.75
t = t_axis(dsec)
drone = (
    np.sin(2 * np.pi * 55 * t)
    + 0.7 * np.sin(2 * np.pi * 110.3 * t)
    + 0.5 * np.sin(2 * np.pi * 109.7 * t)
    + 0.35 * np.sin(2 * np.pi * 164.8 * t)
    + 0.25 * lp_hp(saw(220.4, dsec), hi=900)
    + 0.15 * lp_hp(saw(329.6, dsec), hi=700)
)
air = lp_hp(rng.standard_normal(len(t)), lo=200, hi=1400)
air /= np.max(np.abs(air))
drone = drone / np.max(np.abs(drone)) + 0.12 * air
swell = db(-17 + 10 * (t / dsec) ** 2)
fade = np.minimum(1.0, (dsec - t) / 0.02)
drone_sig = np.tanh(1.5 * drone) * swell * fade
dry.add(drone_sig, 0.0, 1.0)

# ---------------------------------------------------------------- reveal at 10.0
dry.add(boom(0.9), 10.0, db(-3))
verb_send.add(boom(0.9), 10.0, db(-10))

# ---------------------------------------------------------------- groove 12.0 - 26.0
BASS_BARS = [55.0, 43.65, 65.41, 49.0]  # A1 F1 C2 G1, one per 2 s bar


def in_groove(tt):
    return 12.0 <= tt < 22.5 or 23.0 <= tt < 26.0


for k in range(int((26.0 - 12.0) / BEAT)):
    tt = 12.0 + k * BEAT
    if not in_groove(tt):
        continue
    dry.add(kick(), tt, db(-5))
    if k % 2 == 1:  # beats 2 and 4
        dry.add(clap(), tt, db(-9), pan=0.05)
        verb_send.add(clap(), tt, db(-12))
    # off-beat hat
    off = tt + BEAT / 2
    if in_groove(off):
        dry.add(hat(0.035), off, db(-15), pan=0.3)
    # sixteenth ghost hats once the agents are flowing, and after the payoff
    if tt >= 16.0:
        for q in (0.125, 0.375):
            if in_groove(tt + q):
                dry.add(hat(0.018), tt + q, db(-24), pan=-0.35)
    # pumping bass on the off-beat eighth, note follows the bar
    bar = int((tt - 12.0) // 2.0) % 4
    f = BASS_BARS[bar]
    if in_groove(off):
        sec = 0.22
        tb = t_axis(sec)
        b = 0.7 * lp_hp(saw(f * 2, sec), hi=520) + np.sin(2 * np.pi * f * 2 * tb) + 0.6 * np.sin(2 * np.pi * f * tb)
        b *= np.minimum(tb / 0.006, 1) * np.minimum((sec - tb) / 0.03, 1)
        dry.add(np.tanh(1.6 * b) / np.tanh(1.6), off, db(-13))

# payoff boom 23.0
dry.add(boom(0.7, 130, 40), 23.0, db(-5))
verb_send.add(boom(0.7, 130, 40), 23.0, db(-12))

# snare roll 26.0 - 26.9, sixteenths then thirty-seconds, rising
roll = list(np.arange(26.0, 26.5, BEAT / 4)) + list(np.arange(26.5, 26.9, BEAT / 8))
for k, tt in enumerate(roll):
    g = db(-12 + 12 * k / max(1, len(roll) - 1))
    dry.add(snare(), tt, g, pan=(0.15 if k % 2 else -0.15))
    verb_send.add(snare(), tt, g * 0.6)

# ---------------------------------------------------------------- end card 27.0
dry.add(boom(1.3, 160, 34), 27.0, db(-2))
verb_send.add(boom(1.3, 160, 34), 27.0, db(-8))
# low A chord tail under the end card, fading out by 30.0
tsec = 3.0
t = t_axis(tsec)
tail = (
    np.sin(2 * np.pi * 55 * t)
    + 0.6 * np.sin(2 * np.pi * 110 * t)
    + 0.4 * np.sin(2 * np.pi * 164.8 * t)
    + 0.3 * np.sin(2 * np.pi * 220.6 * t)
    + 0.2 * lp_hp(saw(261.6, tsec), hi=1200)
)
tail = np.tanh(1.2 * tail / np.max(np.abs(tail)))
tail *= np.minimum(t / 0.05, 1) * np.clip((tsec - t) / 1.6, 0, 1) ** 1.5
dry.add(tail, 27.0, db(-21))

# ---------------------------------------------------------------- reverb (send) and master

ir_sec = 2.2
ti = t_axis(ir_sec)
irL = rng.standard_normal(len(ti)) * np.exp(-ti / 0.45)
irR = rng.standard_normal(len(ti)) * np.exp(-ti / 0.45)
irL = lp_hp(irL, lo=250, hi=6000)
irR = lp_hp(irR, lo=250, hi=6000)
irL /= np.sqrt(np.sum(irL**2))
irR /= np.sqrt(np.sum(irR**2))


def fftconv(x, h):
    size = 1 << int(np.ceil(np.log2(len(x) + len(h))))
    return np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(h, size), size)[: len(x)]


wetL = fftconv(verb_send.L, irL) * 0.5
wetR = fftconv(verb_send.R, irR) * 0.5

L = dry.L + wetL
R = dry.R + wetR

# gentle bus glue: soft clip, then peak-normalise to -1.5 dBFS
L = np.tanh(1.1 * L) / 1.1
R = np.tanh(1.1 * R) / 1.1
peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
gain = db(-1.5) / peak
L *= gain
R *= gain

# 8 ms fade at both ends
f = int(0.008 * SR)
for ch in (L, R):
    ch[:f] *= np.linspace(0, 1, f)
    ch[-f:] *= np.linspace(1, 0, f)

out = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/audio/bed.wav")
pcm = (np.stack([L, R], axis=1) * 32767).astype(np.int16)
with wave.open(str(out), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f"wrote {out} {DUR}s peak-gain {20 * np.log10(gain):.1f} dB")
