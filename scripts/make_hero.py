#!/usr/bin/env python3
"""Regenerate the README hero: an Istanbul landscape rendered as a terminal preview.

Two modes:
  # generate a fresh Istanbul image via Gemini, then render its terminal preview to PNG
  python scripts/make_hero.py

  # skip generation, render an existing image you already have
  python scripts/make_hero.py --image path/to/image.jpg

Output: assets/hero.png (committed to the repo and shown at the top of the README).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banana.preview import render_preview, preview_to_png
from banana.generator import generate
from banana.client import close_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

ISTANBUL_PROMPT = (
    "A breathtaking photorealistic landscape of Istanbul at golden-hour sunset: "
    "the Bosphorus strait, silhouettes of mosque domes and minarets on the skyline, "
    "seagulls over the water, warm cinematic light, ferries crossing, ultra-detailed, 35mm."
)


async def _generate_istanbul(width: int) -> str:
    out_dir = os.path.join(ROOT, "output", "hero")
    res = await generate(ISTANBUL_PROMPT, "istanbul_hero", out_dir, preview=False)
    await close_client()
    if not res.ok or not res.image_paths:
        raise SystemExit(
            f"Istanbul generation failed: {res.error}\n"
            f"model said: {res.text[:160]}\n"
            "If it says 'signed out', re-export a fresh StorageDump and re-run "
            "scripts/extract_cookies.py, then try again — or pass --image <file>."
        )
    return res.image_paths[0]


def main():
    ap = argparse.ArgumentParser(description="Build assets/hero.png from a terminal preview.")
    ap.add_argument("--image", help="Use an existing image instead of generating one")
    ap.add_argument("--width", type=int, default=72, help="Preview width (default 72)")
    args = ap.parse_args()

    if args.image:
        image = args.image
        if not os.path.isfile(image):
            raise SystemExit(f"image not found: {image}")
    else:
        image = asyncio.run(_generate_istanbul(args.width))
    print(f"source image: {image}")

    ansi = render_preview(image, width=args.width, color=True)
    os.makedirs(ASSETS, exist_ok=True)
    out = os.path.join(ASSETS, "hero.png")
    preview_to_png(ansi, out, width=args.width, title="banana-mcp — gemini image preview")
    print(f"hero written: {out}")


if __name__ == "__main__":
    main()
