#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow", "scipy"]
# ///
"""
Turns a drawing on white paper (a scan or photo of line art) into a PNG with a
transparent background.

How: each pixel's opacity comes from how much darker than the paper it is, so
the paper disappears and pencil lines keep their soft, anti-aliased edges, with
no white fringe or jagged cut-out. It's "colour to alpha" against white:

  1. Levels: anything at least as light as --white counts as paper (fully
     transparent), and anything at least as dark as --black is fully opaque.
     This also absorbs paper texture and JPEG noise.
  2. Each pixel becomes the colour that, laid over white at that opacity,
     gives back the original, so the result looks the same as the original
     on a white page, and coloured ink (pink, blue, ...) keeps its colour.

Usage, from the repo root:
    uv run scripts/transparent_line_art.py drawing.jpg drawing.png

Options for small sizes (icons) and dark backgrounds:
    --color 373737   draw every line in one colour instead of the original's
    --thicken 9      fatten lines by this many pixels, so thin pencil strokes
                     survive being shrunk to icon size
    --fill           keep the inside of a closed outline white, so only the
                     surroundings are transparent and it still reads on dark
                     backgrounds (works best for a single closed outline)
    --square         crop to a square around the drawing

The site's favicons were made from frontend/public/images/placeholder.jpg with:
    uv run scripts/transparent_line_art.py \\
        frontend/public/images/placeholder.jpg \\
        --color 373737 --thicken 9 --favicons frontend/public
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def parse_color(text):
    text = text.lstrip('#')
    if len(text) != 6:
        raise argparse.ArgumentTypeError(f'expected a hex colour like 373737, got {text!r}')
    return np.array([int(text[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def make_transparent(rgb, white, black, color=None, thicken=0, fill=False):
    """rgb: HxWx3 floats 0-255. Returns HxWx4 floats 0-255."""
    # 1. Levels: --black and darker -> 0, --white and lighter -> 255.
    levelled = np.clip((rgb - black) / (white - black), 0, 1) * 255

    # 2. Colour to alpha against white.
    alpha = (255 - levelled).max(axis=2) / 255
    safe = np.maximum(alpha, 1e-6)[..., None]
    ink = np.clip(255 - (255 - levelled) / safe, 0, 255)
    ink[alpha == 0] = 255

    if color is not None:
        ink[:] = color

    if thicken:
        size = (thicken, thicken)
        alpha = ndimage.grey_dilation(alpha, size=size)
        # Spread each line's colour into the pixels it grew into: darker
        # colours win where lines meet.
        ink = np.dstack([ndimage.grey_erosion(ink[..., c], size=size) for c in range(3)])

    if fill:
        # Find the inside of the outline: close small gaps in the strokes,
        # fill the enclosed area, then shrink it back inside the outer line
        # so the white doesn't show past it.
        lines = alpha > 0.4
        closed = ndimage.binary_closing(lines, structure=np.ones((3, 3)), iterations=10)
        inside = ndimage.binary_fill_holes(closed)
        inside = ndimage.binary_opening(inside, iterations=4)  # drop thin bits (feet, stray marks)
        inside = ndimage.binary_erosion(inside, iterations=3)
        inside = ndimage.gaussian_filter(inside.astype(np.float32), 1.0)
        # Lines over white inside; lines over transparency outside.
        filled = 255 * (1 - alpha[..., None]) + ink * alpha[..., None]
        new_alpha = np.maximum(alpha, inside)
        w = np.where(new_alpha > 0, inside / np.maximum(new_alpha, 1e-6), 0)[..., None]
        ink = w * filled + (1 - w) * ink
        alpha = new_alpha

    return np.dstack([ink, alpha * 255])


def crop_square(img, margin):
    """Crop to a square around the visible drawing, plus `margin` pixels."""
    a = np.asarray(img)[..., 3]
    ys, xs = np.nonzero(a > 25)
    if len(xs) == 0:
        return img
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    half = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2 + margin
    box = tuple(int(round(v)) for v in (cx - half, cy - half, cx + half, cy + half))
    return img.crop(box)


def write_favicons(img, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    big = img.resize((512, 512), Image.LANCZOS)
    big.save(out_dir / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
    big.resize((192, 192), Image.LANCZOS).save(out_dir / 'favicon-192.png')
    # iOS shows transparency on home-screen icons as black, so this one sits
    # on white.
    touch = Image.new('RGBA', (180, 180), (255, 255, 255, 255))
    touch.alpha_composite(big.resize((160, 160), Image.LANCZOS), (10, 10))
    touch.convert('RGB').save(out_dir / 'apple-touch-icon.png')
    for name in ('favicon.ico', 'favicon-192.png', 'apple-touch-icon.png'):
        print(out_dir / name)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split('\n\n')[0].strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, nargs='?',
                        help='PNG to write (default: the input, with a .png extension)')
    parser.add_argument('--white', type=float, default=235,
                        help='this light (0-255) or lighter is paper, made fully transparent (default: 235)')
    parser.add_argument('--black', type=float, default=95,
                        help='this dark (0-255) or darker is fully opaque (default: 95)')
    parser.add_argument('--color', type=parse_color,
                        help='draw all lines in this hex colour, e.g. 373737 (default: keep the original colours)')
    parser.add_argument('--thicken', type=int, default=0, metavar='PIXELS',
                        help='fatten lines by this many pixels (of the input image)')
    parser.add_argument('--fill', action='store_true',
                        help='keep the inside of a closed outline white')
    parser.add_argument('--square', action='store_true',
                        help='crop to a square around the drawing')
    parser.add_argument('--margin', type=int, default=12,
                        help='pixels to leave around the drawing with --square or --favicons (default: 12)')
    parser.add_argument('--size', type=int,
                        help='resize the output to this many pixels wide')
    parser.add_argument('--favicons', type=Path, metavar='DIR',
                        help='instead of one PNG, write favicon.ico, favicon-192.png and '
                             'apple-touch-icon.png to DIR (implies --square)')
    args = parser.parse_args()
    if not 0 <= args.black < args.white <= 255:
        parser.error('need 0 <= --black < --white <= 255')

    rgb = np.asarray(Image.open(args.input).convert('RGB'), dtype=np.float32)
    rgba = make_transparent(rgb, args.white, args.black, args.color, args.thicken, args.fill)
    img = Image.fromarray(rgba.clip(0, 255).astype(np.uint8))

    if args.favicons:
        write_favicons(crop_square(img, args.margin), args.favicons)
        return

    if args.square:
        img = crop_square(img, args.margin)
    if args.size:
        img = img.resize((args.size, round(img.height * args.size / img.width)), Image.LANCZOS)
    output = args.output or args.input.with_suffix('.png')
    img.save(output)
    print(output)


if __name__ == '__main__':
    main()
