#!/usr/bin/env python3
"""Render a 'marker on whiteboard' pronunciation card: syllables, stress, hints -> PNG.

Usage:
    uv run --with cairosvg python board.py spec.json out.png
    uv run --with cairosvg python board.py --selftest
Spec: see SKILL.md (syllables required; stress, above, below, ipa, hint, notes, trap optional).
"""
import json
import os
import sys
import tempfile
import textwrap
from xml.sax.saxutils import escape

W, PAD = 1200, 70
MONO = 0.602          # DejaVu Sans Mono advance width per em
BLUE, RED, INK, GREY, ORANGE, GREEN = "#1f3a93", "#d62828", "#222222", "#555555", "#c25e00", "#2a7a3b"


def layout(syllables):
    """Return (font_size, [(x_start, x_end, text)]) for syllables; leading space = new word."""
    n = sum(len(s) for s in syllables)
    fs = min(150, (W - 2 * PAD) / (n * MONO))
    cw = fs * MONO
    x = (W - n * cw) / 2
    spans = []
    for s in syllables:
        spans.append((x, x + len(s) * cw, s))
        x += len(s) * cw
    return fs, spans


def fit(x, s, size):
    """Shift a centred label so it stays on the board (0.55 em is DejaVu Sans' average glyph)."""
    half = len(s) * size * 0.55 / 2
    return min(max(x, PAD + half), W - PAD - half)


def text(x, y, s, size, color, anchor="middle", weight="normal", family="DejaVu Sans"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size:.1f}" '
            f'fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{escape(s)}</text>')


def render_svg(spec):
    syl = spec["syllables"]
    stress = set(spec.get("stress", []))
    above = {int(k): v for k, v in spec.get("above", {}).items()}
    below = {int(k): v for k, v in spec.get("below", {}).items()}
    fs, spans = layout(syl)
    small = max(26.0, fs * 0.32)

    y_above = 70 + small
    top = y_above + 20
    base = top + fs * 0.85
    bottom = base + fs * 0.25
    out = []

    for i, (x0, x1, s) in enumerate(spans):
        lead = len(s) - len(s.lstrip(" "))
        x0 += lead * fs * MONO              # skip the word-gap space
        mid = (x0 + x1) / 2
        out.append(text(x0, base, s.strip(), fs, BLUE, "start",
                        "bold" if i in stress else "normal", "DejaVu Sans Mono"))
        if i in stress:
            out.append(f'<line x1="{x0:.1f}" y1="{bottom:.1f}" x2="{x1:.1f}" y2="{bottom:.1f}" '
                       f'stroke="{RED}" stroke-width="5" stroke-linecap="round"/>')
        if i > 0 and not s.startswith(" "):  # red bar between syllables of one word
            out.append(f'<line x1="{x0:.1f}" y1="{top:.1f}" x2="{x0:.1f}" y2="{bottom + 10:.1f}" '
                       f'stroke="{RED}" stroke-width="4" stroke-linecap="round"/>')
        if i in above:
            out.append(text(fit(mid, above[i], small), y_above, above[i], small, RED))

    y = bottom + 30
    if below:
        arrow_top, arrow_bot = y, y + 55
        for i, label in below.items():
            x0, x1, s = spans[i]
            mid = (x0 + (len(s) - len(s.lstrip(" "))) * fs * MONO + x1) / 2
            out.append(f'<line x1="{mid:.1f}" y1="{arrow_top:.1f}" x2="{mid:.1f}" y2="{arrow_bot:.1f}" '
                       f'stroke="{RED}" stroke-width="3"/>')
            out.append(f'<path d="M{mid - 9:.1f},{arrow_bot - 12:.1f} L{mid:.1f},{arrow_bot:.1f} '
                       f'L{mid + 9:.1f},{arrow_bot - 12:.1f}" stroke="{RED}" stroke-width="3" fill="none"/>')
            out.append(text(fit(mid, label, small), arrow_bot + small + 4, label, small, RED))
        y = arrow_bot + small + 40

    if spec.get("translation"):
        y += 50
        out.append(text(W / 2, y, "= " + spec["translation"], 46, GREEN, weight="bold"))
    if spec.get("ipa"):
        y += 66 if spec.get("translation") else 50
        out.append(text(W / 2, y, spec["ipa"], 52, INK))
    if spec.get("hint"):
        y += 60
        out.append(text(W / 2, y, spec["hint"], 40, RED, weight="bold"))
    lines = []
    for note in spec.get("notes", []):
        lines += [("• " if j == 0 else "  ") + part
                  for j, part in enumerate(textwrap.wrap(note, 60))]
    if lines:
        y += 30
    for line in lines:
        y += 42
        out.append(text(PAD, y, line, 30, GREY, "start"))
    if spec.get("trap"):
        for j, part in enumerate(textwrap.wrap("⚠ " + spec["trap"], 58)):
            y += 46
            out.append(text(PAD, y, part, 32, ORANGE, "start", "bold"))

    h = int(y + 60)
    board = (f'<rect x="0" y="0" width="{W}" height="{h}" fill="#e9e9e6"/>'
             f'<rect x="20" y="20" width="{W - 40}" height="{h - 40}" rx="12" fill="#fbfbf8" '
             f'stroke="#c9c9c4" stroke-width="3"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
            f'viewBox="0 0 {W} {h}">{board}{"".join(out)}</svg>')


def render(spec, png_path):
    import cairosvg  # supplied by `uv run --with cairosvg`
    cairosvg.svg2png(bytestring=render_svg(spec).encode(), write_to=png_path)


def selftest():
    spec = {"syllables": ["cu", "cum", "ber"], "stress": [0], "above": {"0": "кью", "1": "а"},
            "below": {"0": "c → [k]", "2": "er → [ə]"}, "translation": "огурец", "ipa": "/ˈkjuː.kʌm.bə/",
            "hint": "КЬЮ-кам-бэ", "notes": ["c перед e/i/y = [s], иначе [k]"], "trap": "не «кукумбер»"}
    fs, spans = layout(spec["syllables"])
    assert all(a[1] == b[0] for a, b in zip(spans, spans[1:])), "syllables must be contiguous"
    assert spans[0][0] >= PAD - 1 and spans[-1][1] <= W - PAD + 1, "word must fit the board"
    _, phrase = layout(["long", " time", " no", " see"])
    assert phrase[-1][1] <= W - PAD + 1
    assert fit(0, "w — губы трубочкой", 40) - 9 * 40 * 0.55 >= PAD - 1, "label must not clip left edge"
    assert "= огурец" in render_svg(spec), "translation must be on the board"
    out = os.path.join(tempfile.gettempdir(), "wb_selftest.png")
    render(spec, out)
    with open(out, "rb") as fh:
        assert fh.read(8) == b"\x89PNG\r\n\x1a\n", "not a PNG"
    print("selftest ok:", out)


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    elif len(sys.argv) == 3:
        with open(sys.argv[1], encoding="utf-8") as fh:
            render(json.load(fh), sys.argv[2])
        print("ok:", sys.argv[2])
    else:
        sys.exit(__doc__)
