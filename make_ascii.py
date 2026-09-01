#!/usr/bin/env python3
"""
Turns a portrait into the ASCII block used by profile_card.py.

    python make_ascii.py photo.jpg                     # auto head-and-shoulders crop
    python make_ascii.py photo.jpg 600 840 1960 2900   # explicit crop box

Two things make this read as a person rather than a blob:

1. The subject is separated from the background, then its tonal range is
   equalised against *itself*. Normalising globally lets the background-vs-subject
   contrast dominate and flattens everything inside the subject to one character.

2. The result is lifted into the top 60% of the ramp (FLOOR), so the figure still
   reads as a solid shape. Using the full ramp gives depth but dissolves the
   silhouette into the background.
"""

import sys
import numpy as np
from PIL import Image, ImageFilter

COLS, ROWS = 44, 40          # grid; pairs with ASCII_FS/ASCII_LH in profile_card.py
RAMP = " .:-=+*oesc#%@"      # light -> dense
SKY_CUTOFF = 150             # grey level above which a pixel counts as background
FLOOR = 0.40                 # minimum ink density for subject pixels
HEAD_TO_BODY = 1.55          # crop height as a multiple of subject width
OUT = "ascii.txt"


def auto_crop(im):
    """Frame head-and-shoulders. Subject width sets the height, which keeps
    floors, railings and other low clutter out of the shot."""
    g = np.asarray(im, float)
    H, W = g.shape
    dark = g < SKY_CUTOFF

    tops = np.where(dark.sum(1) > W * 0.01)[0]
    if not len(tops):
        return im
    top = int(tops[0])

    # measure width a little below the head, where the torso is
    band = dark[top + int(0.25 * (H - top)): top + int(0.55 * (H - top))]
    cols = band.sum(0)
    xs = np.where(cols > band.shape[0] * 0.1)[0]
    if not len(xs):
        return im
    left, right = int(xs[0]), int(xs[-1])

    pad = int((right - left) * 0.05)
    x0, x1 = max(0, left - pad), min(W, right + pad)
    y0 = max(0, top - pad)
    y1 = min(H, y0 + int((x1 - x0) * HEAD_TO_BODY))
    print(f"auto-crop: ({x0}, {y0}, {x1}, {y1})")
    return im.crop((x0, y0, x1, y1))


def main(path, box=None):
    im = Image.open(path).convert("L")
    if im.size == (3219, 2280):                    # the original chat screenshot
        im = im.crop((60, 540, 815, 1300)).crop((165, 60, 565, 640))
    elif box:
        im = im.crop(box)
    else:
        im = auto_crop(im)

    # denoise first, or equalising near-uniform fabric amplifies sensor grain
    im = im.filter(ImageFilter.MedianFilter(5))
    im = im.filter(ImageFilter.UnsharpMask(radius=6, percent=120, threshold=3))

    a = np.asarray(im.resize((COLS, ROWS), Image.LANCZOS), dtype=float)
    subject = a <= SKY_CUTOFF
    if not subject.any():
        sys.exit("no subject found - adjust SKY_CUTOFF")

    vals = a[subject]
    rank = 1.0 - (vals.argsort().argsort() / max(1, len(vals) - 1))
    lum = 1.0 - (vals - vals.min()) / max(1.0, float(vals.max() - vals.min()))

    # pure ranking looks noisy on flat fabric, pure luminance goes flat again
    density = 0.35 * rank + 0.65 * (lum ** 0.75)
    density = FLOOR + (1.0 - FLOOR) * density

    out = np.zeros_like(a)
    out[subject] = density
    idx = np.clip((out * (len(RAMP) - 1)).round().astype(int), 0, len(RAMP) - 1)

    rows = ["".join(" " if not subject[r, c] else RAMP[idx[r, c]]
                    for c in range(COLS)).rstrip() for r in range(ROWS)]
    while rows and len(rows[0].strip()) < 4:
        rows.pop(0)
    while rows and len(rows[-1].strip()) < 4:
        rows.pop()

    open(OUT, "w", encoding="utf-8").write("\n".join(rows))
    print("\n".join(rows))
    print(f"\n-> {OUT}: {len(rows)} rows x {max(len(r) for r in rows)} cols")


if __name__ == "__main__":
    args = sys.argv[1:]
    src = args[0] if args else "portrait.jpg"
    crop = tuple(int(v) for v in args[1:5]) if len(args) >= 5 else None
    main(src, crop)
