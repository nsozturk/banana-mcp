#!/usr/bin/env python3
"""Regenerate the README hero: a real Istanbul landscape image.

  # generate a fresh Istanbul image via Gemini and copy it to assets/hero.png
  python scripts/make_hero.py

  # or use an existing image you already have
  python scripts/make_hero.py --image path/to/image.jpg

Output: assets/hero.png (committed to the repo and shown at the top of the README).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banana.generator import generate
from banana.client import close_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

ISTANBUL_PROMPT = (
    "A breathtaking photorealistic landscape of Istanbul at golden-hour sunset: "
    "the Bosphorus strait, silhouettes of mosque domes and minarets on the skyline, "
    "seagulls over the water, warm cinematic light, ferries crossing, ultra-detailed, 35mm."
)


async def _generate_istanbul() -> str:
    out_dir = os.path.join(ROOT, "output", "hero")
    res = await generate(ISTANBUL_PROMPT, "istanbul_hero", out_dir)
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
    ap = argparse.ArgumentParser(description="Build assets/hero.png (Istanbul landscape).")
    ap.add_argument("--image", help="Use an existing image instead of generating one")
    args = ap.parse_args()

    image = args.image if args.image else asyncio.run(_generate_istanbul())
    if not os.path.isfile(image):
        raise SystemExit(f"image not found: {image}")
    print(f"source image: {image}")

    os.makedirs(ASSETS, exist_ok=True)
    out = os.path.join(ASSETS, "hero.jpg")
    shutil.copyfile(image, out)
    print(f"hero written: {out}")


if __name__ == "__main__":
    main()
