#!/usr/bin/env python3
"""Acoustic analysis of a short English voice message — stdlib + ffmpeg only.

Usage:
    python3 voice.py AUDIO [--text "transcript as recognised"] [--target "target sentence"] [--json]

Measures (no numpy/librosa on this host, no pip):
    * duration, speech/pause split (RMS gate), pause count and longest pause
    * speech rate in words per minute (needs --text), rate inside speech only
    * F0 contour by autocorrelation at 4 kHz: median, range in semitones,
      phrase-final direction (rise/fall), loudest-word position
    * target-vs-heard diff (needs --target): which words the recogniser lost

Deliberately does NOT judge phoneme quality — that would be guessing.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from operator import mul

SR = 4000          # analysis rate: enough for F0 up to ~350 Hz
FRAME_MS = 40
HOP_MS = 20
F0_MIN, F0_MAX = 60, 350


def decode(path: str) -> array.array:
    """ffmpeg -> mono 16-bit PCM at SR, returned as array('h')."""
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found")
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False,
                                      dir=os.environ.get("TMPDIR", "/tmp"))
    tmp.close()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", path,
           "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", tmp.name]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        os.unlink(tmp.name)
        sys.exit(f"ffmpeg failed: {res.stderr.strip()[:300]}")
    with wave.open(tmp.name) as wf:
        raw = wf.readframes(wf.getnframes())
    os.unlink(tmp.name)
    samples = array.array("h")
    samples.frombytes(raw)
    return samples


def frames(samples: array.array):
    n = int(SR * FRAME_MS / 1000)
    hop = int(SR * HOP_MS / 1000)
    for start in range(0, max(0, len(samples) - n), hop):
        yield start / SR, samples[start:start + n]


def rms(frame) -> float:
    if not frame:
        return 0.0
    return math.sqrt(sum(s * s for s in frame) / len(frame))


def f0(frame, energy: float, gate: float) -> float | None:
    """Autocorrelation pitch with center clipping. None when unvoiced."""
    if energy < gate:
        return None
    clip = 0.3 * max(abs(min(frame)), abs(max(frame)))
    sig = [s - math.copysign(clip, s) if abs(s) > clip else 0.0 for s in frame]
    if not any(sig):
        return None
    zero = sum(x * x for x in sig)
    if zero <= 0:
        return None
    lo, hi = int(SR / F0_MAX), int(SR / F0_MIN)
    best_lag, best_val = 0, 0.0
    for lag in range(lo, min(hi, len(sig) - 1)):
        val = sum(map(mul, sig[:-lag], sig[lag:]))
        if val > best_val:
            best_val, best_lag = val, lag
    if not best_lag or best_val / zero < 0.3:   # weak periodicity -> unvoiced
        return None
    return SR / best_lag


def semitones(a: float, b: float) -> float:
    return 12 * math.log2(a / b) if a > 0 and b > 0 else 0.0


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, int(p * len(s)))]


def analyse(path: str, text: str | None, target: str | None) -> dict:
    samples = decode(path)
    dur = len(samples) / SR
    if dur < 0.3:
        sys.exit("clip too short to analyse")

    stamped = list(frames(samples))
    energies = [rms(f) for _, f in stamped]
    peak = max(energies) if energies else 0.0
    gate = max(peak * 0.08, pct(energies, 0.25) * 1.6)   # silence threshold

    # Trim leading/trailing silence: a recorder's dead air is not a speech
    # feature, and leaving it in inflates silence_ratio and wpm_speaking and
    # puts the phrase-final window inside the dead air.
    live = [i for i, e in enumerate(energies) if e >= gate]
    if live:
        lo_f, hi_f = live[0], live[-1]
        stamped = stamped[lo_f:hi_f + 1]
        energies = energies[lo_f:hi_f + 1]
        t0 = stamped[0][0]
        stamped = [(t - t0, f) for t, f in stamped]
        dur = len(stamped) * HOP_MS / 1000 + FRAME_MS / 1000
        peak = max(energies)

    # ---- pauses -------------------------------------------------------
    voiced_flags = [e >= gate for e in energies]
    pauses, run = [], 0
    for i, flag in enumerate(voiced_flags):
        if flag:
            if run * HOP_MS >= 250 and 0 < i - run:      # ignore leading silence
                pauses.append(round(run * HOP_MS / 1000, 2))
            run = 0
        else:
            run += 1
    speech_s = sum(voiced_flags) * HOP_MS / 1000

    # ---- pitch --------------------------------------------------------
    contour = []
    for (t, frame), e in zip(stamped, energies):
        p = f0(frame, e, gate)
        if p:
            contour.append((round(t, 2), round(p, 1)))
    pitches = [p for _, p in contour]
    med = pct(pitches, 0.5) if pitches else 0.0
    p10, p90 = pct(pitches, 0.1), pct(pitches, 0.9)
    span = round(semitones(p90, p10), 1) if pitches else 0.0

    # phrase-final direction: last 600 ms of VOICED pitch, not of the file —
    # trailing dead air would otherwise leave this window empty.
    tail = [p for t, p in contour if t >= contour[-1][0] - 0.6] if contour else []
    direction = "n/a"
    if len(tail) >= 4:
        half = len(tail) // 2
        delta = semitones(pct(tail[half:], 0.5), pct(tail[:half], 0.5))
        direction = ("rise" if delta > 1.5 else
                     "fall" if delta < -1.5 else "flat")

    loudest_t = round(stamped[energies.index(peak)][0], 2) if energies else 0.0

    words = re.findall(r"[a-zA-Z']+", text or "")
    wpm = round(len(words) / (dur / 60)) if words and dur else None
    wpm_speech = round(len(words) / (speech_s / 60)) if words and speech_s else None

    lost = []
    if target and text:
        tw = [w.lower() for w in re.findall(r"[a-zA-Z']+", target)]
        hw = [w.lower() for w in words]
        lost = [w for w in tw if w not in hw]

    return {
        "file": os.path.basename(path),
        "duration_s": round(dur, 2),
        "speech_s": round(speech_s, 2),
        "silence_ratio": round(1 - speech_s / dur, 2),
        "pauses_over_250ms": pauses,
        "longest_pause_s": max(pauses) if pauses else 0.0,
        "wpm_overall": wpm,
        "wpm_speaking": wpm_speech,
        "f0_median_hz": round(med, 1),
        "f0_p10_hz": round(p10, 1),
        "f0_p90_hz": round(p90, 1),
        "f0_range_semitones": span,
        "phrase_final": direction,
        "loudest_point_s": loudest_t,
        "voiced_frames": len(contour),
        "contour_sample": contour[::max(1, len(contour) // 12)][:12],
        "target_words_not_recognised": lost,
    }


def report(m: dict) -> str:
    out = [f"🎙 {m['file']} — {m['duration_s']} s, речь {m['speech_s']} s "
           f"(тишина {int(m['silence_ratio'] * 100)}%)"]
    if m["wpm_overall"]:
        out.append(f"Темп: {m['wpm_overall']} wpm общий / {m['wpm_speaking']} wpm "
                   f"внутри речи (носитель в разговоре: 140–180)")
    if m["pauses_over_250ms"]:
        out.append(f"Паузы >250 мс: {len(m['pauses_over_250ms'])} шт, "
                   f"самая длинная {m['longest_pause_s']} s "
                   f"({', '.join(str(p) for p in m['pauses_over_250ms'][:8])})")
    else:
        out.append("Паузы >250 мс: нет — речь идёт слитно")
    out.append(f"Тон: медиана {m['f0_median_hz']} Гц, диапазон "
               f"{m['f0_range_semitones']} полутонов "
               f"({m['f0_p10_hz']}–{m['f0_p90_hz']} Гц) — "
               f"{'монотонно' if m['f0_range_semitones'] < 5 else 'живая интонация'}")
    out.append(f"Конец фразы: {m['phrase_final']} "
               f"(rise = вопрос/незавершённость, fall = утверждение)")
    out.append(f"Громче всего на {m['loudest_point_s']} s — это слово ты выделил")
    if m["target_words_not_recognised"]:
        out.append("Распознавание потеряло слова: "
                   + ", ".join(m["target_words_not_recognised"])
                   + " ← сигнал проблемного произношения")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--text", help="what the recogniser heard")
    ap.add_argument("--target", help="sentence he was asked to say")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    m = analyse(a.audio, a.text, a.target)
    print(json.dumps(m, ensure_ascii=False, indent=2) if a.json else report(m))


if __name__ == "__main__":
    main()
