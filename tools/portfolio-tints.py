#!/usr/bin/env python3
"""Pick the scroll background tint for each portfolio image.

The portfolio page eases its background between these colours as you scroll.
For each image: quantise it to a small palette, keep the most common colours,
discard the ones too near black to carry a hue, take the darkest of what is
left, and clamp its brightness so white text stays readable.

Usage:
    python3 tools/portfolio-tints.py            # print a tint per image
    python3 tools/portfolio-tints.py --check    # list images missing a bg

Paste the printed value into the matching cell's `bg:` in _data/portfolio.yml.
Requires ImageMagick (`magick` on PATH).
"""
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "assets", "portfolio")
DATA = os.path.join(ROOT, "_data", "portfolio.yml")

MAX_CHANNEL = 34   # brightest channel allowed in the result; lower = darker page
MIN_LIGHT = 30     # bright enough to carry a hue even if close to neutral
MIN_CHROMA = 14    # or dark but visibly coloured, like a deep green backdrop
TOP_N = 6          # how many of the most common colours to consider


def histogram(path):
    out = subprocess.run(
        ["magick", path, "-resize", "200x200", "-colors", "10",
         "-format", "%c", "histogram:info:"],
        capture_output=True, text=True, check=True).stdout
    entries = []
    for line in out.splitlines():
        m = re.search(r"^\s*(\d+):\s*\([^)]*\)\s*#([0-9A-Fa-f]{6})\b", line)
        if m:
            hexcode = m.group(2)
            rgb = tuple(int(hexcode[i:i + 2], 16) for i in (0, 2, 4))
            entries.append((int(m.group(1)), rgb))
    entries.sort(key=lambda e: -e[0])
    return entries


def luminance(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def tint(path):
    top = histogram(path)[:TOP_N]
    # keep colours that carry a hue: either bright enough to read as a colour,
    # or dark but saturated. Only near-black neutrals are dropped, since those
    # would flatten the page to black instead of tinting it.
    candidates = [e for e in top
                  if max(e[1]) >= MIN_LIGHT or max(e[1]) - min(e[1]) >= MIN_CHROMA] or top
    rgb = min(candidates, key=lambda e: luminance(e[1]))[1]
    peak = max(rgb)
    if peak == 0:
        return (16, 21, 15)
    scale = min(1.0, MAX_CHANNEL / peak)
    out = tuple(int(round(c * scale)) for c in rgb)
    if max(out) - min(out) < 2:      # fully neutral reads as flat black
        out = (out[0], min(255, out[1] + 4), out[2])
    return out


def main():
    check = "--check" in sys.argv
    referenced = open(DATA, encoding="utf-8").read() if os.path.exists(DATA) else ""
    missing = []
    for path in sorted(glob.glob(os.path.join(IMAGES, "*.webp"))):
        name = os.path.basename(path)
        r, g, b = tint(path)
        hexcode = "#%02x%02x%02x" % (r, g, b)
        if check:
            if 'image: %s' % name in referenced and hexcode not in referenced:
                missing.append((name, hexcode))
        else:
            print('%-20s bg: "%s"' % (name, hexcode))
    if check:
        for name, hexcode in missing:
            print('%s has no matching bg, suggest "%s"' % (name, hexcode))
        if not missing:
            print("every referenced image has a tint")


if __name__ == "__main__":
    main()
