#!/usr/bin/env python3
"""Render a word mind-map card: the word in an ellipse, meanings around it -> PNG.

Usage:
    uv run --with cairosvg python card.py spec.json out.png
    uv run --with cairosvg python card.py --selftest
Spec: {"word": "get", "subtitle": "/ɡet/", "items": [{"head", "tr", "ex": [..], "vs"}]} — see SKILL.md.
"""
import json
import math
import os
import sys
import tempfile
import textwrap
from xml.sax.saxutils import escape

W, PAD, GAP, VGAP = 1600, 40, 36, 80
SIDE_W = 380
AVG = 0.58  # DejaVu Sans average advance per em; wrap is estimated, vision check catches the rest
RED, GREEN, INK, ORANGE, GREY = "#d62828", "#2a7a3b", "#222222", "#c25e00", "#666666"
STYLE = {  # kind -> (size, color, weight, style)
    "head": (34, RED, "bold", "normal"),
    "tr": (26, GREEN, "bold", "normal"),
    "ex": (22, INK, "normal", "normal"),
    "vs": (21, ORANGE, "normal", "italic"),
}
MAX_ITEMS = 10


def lines_for(item, width):
    """Wrap one item into [(kind, text)] for a box `width` px wide."""
    out = []

    def add(kind, s, first="", rest=""):
        size = STYLE[kind][0]
        cols = max(8, int(width / (size * AVG)))
        out.extend((kind, ln) for ln in textwrap.wrap(s, cols, initial_indent=first, subsequent_indent=rest))

    add("head", item["head"])
    if item.get("tr"):
        add("tr", item["tr"])
    for ex in item.get("ex", []):
        add("ex", ex, "• ", "  ")
    if item.get("vs"):
        add("vs", item["vs"], "≠ ", "  ")
    return out


def box_height(lines):
    return sum(STYLE[k][0] * 1.3 for k, _ in lines) + 8


def draw_box(x, y, lines):
    svg, cy = [], y
    for kind, s in lines:
        size, color, weight, style = STYLE[kind]
        cy += size * 1.3
        svg.append(f'<text x="{x:.1f}" y="{cy - size * 0.3:.1f}" font-family="DejaVu Sans" '
                   f'font-size="{size}" fill="{color}" font-weight="{weight}" font-style="{style}" '
                   f'xml:space="preserve">{escape(s)}</text>')
    return svg


def split(n):
    """Items -> (top, left, right, bottom) counts: one per side once there are 4+, rest top/bottom."""
    side = 1 if n >= 4 else 0
    rest = n - 2 * side
    top = math.ceil(rest / 2)
    return top, side, side, rest - top


def row(items, y0):
    """Lay out a row across the full width; return [(x0, x1, lines)] and the row height."""
    k = len(items)
    if not k:
        return [], 0
    bw = (W - 2 * PAD - (k - 1) * GAP) / k
    boxes = [(PAD + i * (bw + GAP), PAD + i * (bw + GAP) + bw, lines_for(it, bw)) for i, it in enumerate(items)]
    return boxes, max(box_height(b[2]) for b in boxes)


def render_svg(spec):
    items = spec["items"]
    assert 1 <= len(items) <= MAX_ITEMS, f"1..{MAX_ITEMS} items, got {len(items)}"
    nt, nl, nr, nb = split(len(items))
    top_items, rest = items[:nt], items[nt:]
    left, right, bot_items = rest[:nl], rest[nl:nl + nr], rest[nl + nr:]

    y = PAD
    top, ht = row(top_items, y)
    y_mid = y + ht + (VGAP if top else 0)
    sides = [(PAD, PAD + SIDE_W, lines_for(left[0], SIDE_W))] if left else []
    sides += [(W - PAD - SIDE_W, W - PAD, lines_for(right[0], SIDE_W))] if right else []
    hm = max([240] + [box_height(b[2]) for b in sides])
    y_bot = y_mid + hm + VGAP
    bottom, hb = row(bot_items, y_bot)
    H = int(y_bot + hb + PAD + (30 if spec.get("footer") else 0)) if bottom else int(y_mid + hm + PAD)

    cx, cy = W / 2, y_mid + hm / 2
    inner = W - 2 * PAD - (2 * SIDE_W + 2 * GAP if sides else 0)
    rx, ry = min(280, inner / 2 - 20), 105
    word = spec["word"]
    fs = min(110, 1.7 * rx / (len(word) * 0.62))

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">',
           '<defs><marker id="a" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">'
           f'<path d="M0,0 L12,6 L0,12 z" fill="{INK}"/></marker></defs>',
           f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="white" stroke="{INK}" stroke-width="4"/>',
           f'<text x="{cx}" y="{cy + fs * 0.35:.1f}" font-family="DejaVu Sans" font-size="{fs:.0f}" '
           f'font-weight="bold" fill="{RED}" text-anchor="middle">{escape(word)}</text>']
    if spec.get("subtitle"):
        svg.append(f'<text x="{cx}" y="{cy + ry - 18:.1f}" font-family="DejaVu Sans" font-size="24" '
                   f'fill="{GREY}" text-anchor="middle">{escape(spec["subtitle"])}</text>')

    def arrow(tx, ty):
        dx, dy = tx - cx, ty - cy
        t = 1.04 / math.hypot(dx / rx, dy / ry)
        svg.append(f'<line x1="{cx + dx * t:.1f}" y1="{cy + dy * t:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" '
                   f'stroke="{INK}" stroke-width="3" marker-end="url(#a)"/>')

    near = lambda x0, x1: min(max(cx, x0 + 40), x1 - 40)  # anchor on the box edge closest to the centre
    for x0, x1, lines in top:
        svg += draw_box(x0, y, lines)
        arrow(near(x0, x1), y + box_height(lines) + 6)
    for x0, x1, lines in sides:
        h = box_height(lines)
        by = cy - h / 2
        svg += draw_box(x0, by, lines)
        arrow(x1 + 8 if x0 < cx else x0 - 14, cy)
    for x0, x1, lines in bottom:
        svg += draw_box(x0, y_bot, lines)
        arrow(near(x0, x1), y_bot - 6)
    if spec.get("footer"):
        svg.append(f'<text x="{W / 2}" y="{H - 16}" font-family="DejaVu Sans" font-size="18" '
                   f'fill="{GREY}" text-anchor="middle">{escape(spec["footer"])}</text>')
    svg.append("</svg>")
    return "\n".join(svg)


def render(spec, png_path):
    import cairosvg
    cairosvg.svg2png(bytestring=render_svg(spec).encode(), write_to=png_path)


def selftest():
    item = {"head": "get along (with)", "tr": "ладить, быть в хороших отношениях",
            "ex": ["Do you get along with your team?", "We get along fine."], "vs": "get on — то же, но британское"}
    for n in (1, 3, 4, 7, 10):
        svg = render_svg({"word": "get", "subtitle": "/ɡet/", "items": [item] * n})
        assert svg.count("<line") == n, n
    out = os.path.join(tempfile.gettempdir(), "word_card_selftest.png")
    render({"word": "get", "subtitle": "/ɡet/", "items": [item] * 10, "footer": "selftest"}, out)
    assert os.path.getsize(out) > 10_000
    print("selftest ok:", out)


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    elif len(sys.argv) == 3:
        render(json.load(open(sys.argv[1])), sys.argv[2])
        print("ok:", sys.argv[2])
    else:
        sys.exit(__doc__)
