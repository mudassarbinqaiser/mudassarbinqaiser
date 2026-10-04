#!/usr/bin/env python3
"""
Turns a background-removed portrait (transparent PNG) into the ASCII blocks
used by profile_card.py.

    python make_ascii.py cutout.png

Writes ascii_dark.txt (for light glyphs on a dark card) and ascii_light.txt
(dark glyphs on a light card). Requires Pillow and numpy.

What makes this read as a face rather than noise:

1. The silhouette comes from the PNG's alpha channel, not a brightness guess,
   so the outline is exact and the background is genuinely empty.

2. Cells are sized to the real glyph box. Monospace glyphs are ~1.8x taller
   than wide, so the row count is derived from the crop's aspect ratio
   instead of being hard-coded; the face is no longer squashed.

3. The glyph ramp is measured. Each candidate glyph is rasterised in Consolas
   and its ink coverage recorded, then glyphs are picked at evenly spaced
   densities. "Looks darker" and "is darker" finally agree.

4. Tone is computed in linear light, stretched between the subject's own 1st
   and 99th percentiles, then mapped per theme: brightness -> ink on the dark
   card, darkness -> ink on the light card. One file for both themes would
   render one of them as a negative.
"""

import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFile, ImageFilter, ImageFont

ImageFile.LOAD_TRUNCATED_IMAGES = True   # phone exports often lack IEND

COLS = 62                 # pairs with ASCII_FS / X in profile_card.py
CELL_ASPECT = 1.818       # glyph box height / advance width (1 / 0.55em)
CROP_ASPECT = 1.35        # crop height / width: head to just below the arms
FLOOR = 0.18              # minimum ink for a subject cell so the figure stays solid
COVER_MIN = 0.35          # alpha coverage below which a cell is background
LEVELS = 18
FONT = "C:/Windows/Fonts/consola.ttf"
POOL = " .:-~;=+*cvsxoaeSZXAHO#%8&@"   # visually even glyphs; ramp is picked from these
OUT = {"dark": "ascii_dark.txt", "light": "ascii_light.txt"}


def measure_ramp():
    """Pick LEVELS glyphs from POOL at evenly spaced measured ink densities."""
    try:
        font = ImageFont.truetype(FONT, 64)
    except OSError:                                # classic fallback
        ramp = list(" .:-=+*#%@")
        return ramp, np.linspace(0, 1, len(ramp))
    adv = int(font.getlength("M"))
    asc, desc = font.getmetrics()
    dens = {}
    for ch in POOL:
        im = Image.new("L", (adv + 4, asc + desc + 4), 0)
        ImageDraw.Draw(im).text((2, 2), ch, font=font, fill=255)
        dens[ch] = np.asarray(im).mean() / 255
    top = max(dens.values())
    picked = {min(dens, key=lambda c: abs(dens[c] / top - t)) for t in np.linspace(0, 1, LEVELS)}
    ramp = sorted(picked, key=dens.get)
    return ramp, np.array([dens[c] / top for c in ramp])


def load(path):
    im = Image.open(path).convert("RGBA")
    im.load()
    a = np.asarray(im)[:, :, 3]
    rows = np.where((a > 8).any(1))[0]
    cols = np.where((a > 8).any(0))[0]
    im = im.crop((int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1))
    w, h = im.size
    return im.crop((0, 0, w, min(h, int(w * CROP_ASPECT))))


def main(path):
    im = load(path)
    w, h = im.size
    rows = max(1, round(COLS * (h / w) / CELL_ASPECT))

    # local contrast at roughly one cell's radius so glasses, eyes and the
    # beard line survive the downsample instead of averaging into skin tone
    cell = w / COLS
    im = im.filter(ImageFilter.UnsharpMask(radius=cell * 0.8, percent=90, threshold=2))

    rgba = np.asarray(im, dtype=float) / 255
    alpha = rgba[:, :, 3]
    lin = ((0.2126 * rgba[:, :, 0] + 0.7152 * rgba[:, :, 1] + 0.0722 * rgba[:, :, 2]) ** 2.2)

    # box-average alpha and alpha-weighted linear luminance into the grid
    def grid(arr):
        return np.asarray(Image.fromarray((arr * 65535).astype(np.uint16))
                          .resize((COLS, rows), Image.BOX), dtype=float) / 65535

    cover = grid(alpha)
    lum = grid(lin * alpha) / np.maximum(cover, 1e-6)
    subject = cover > COVER_MIN
    if not subject.any():
        sys.exit("no subject found - is the PNG transparent?")

    lo, hi = np.percentile(lum[subject], [1, 99])
    bright = np.clip((lum - lo) / max(hi - lo, 1e-6), 0, 1) ** (1 / 2.2)
    edge = np.clip((cover - COVER_MIN) / (0.85 - COVER_MIN), 0, 1)   # feather the outline

    ramp, dens = measure_ramp()
    print(f"ramp: {''.join(ramp)!r}")
    for theme, fname in OUT.items():
        tone = bright if theme == "dark" else 1 - bright
        density = (FLOOR + (1 - FLOOR) * tone) * (0.4 + 0.6 * edge)
        # nearest measured density, never the blank glyph for a subject cell
        idx = np.abs(density[..., None] - dens[None, None, 1:]).argmin(-1) + 1
        lines = ["".join(ramp[idx[r, c]] if subject[r, c] else " "
                         for c in range(COLS)).rstrip() for r in range(rows)]
        while lines and not lines[-1]:
            lines.pop()
        open(fname, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
        print(f"-> {fname}: {len(lines)} rows x {COLS} cols")
    print("\n".join(open(OUT["dark"], encoding="utf-8").read().split("\n")))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "cutout.png")
