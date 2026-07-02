#!/usr/bin/env python3
"""Standalone CLI: run image prompts from a JSON file through Gemini.

Examples:
    # first 3 prompts of a file into output/<timestamp>/
    python scripts/generate.py uskudar-adult-women-image-prompts.json --limit 3

    # specific ids
    python scripts/generate.py sariyer-adult-women-image-prompts.json \
        --ids sariyer_adult_woman_001_emirgan_seaside_promenade

    # by index, custom output dir
    python scripts/generate.py file.json --index 0 1 2 --out output/run1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banana import config
from banana.prompts import load_prompt_file, select
from banana.generator import generate_prompt
from banana.client import close_client


async def run(args):
    prompts, meta = load_prompt_file(args.file)
    chosen = select(prompts, ids=args.ids, indices=args.index, limit=args.limit)
    if not chosen:
        sys.exit("No prompts selected.")

    out_dir = args.out or os.path.join(config.DEFAULT_OUTPUT, _stamp_from(args.file))
    os.makedirs(out_dir, exist_ok=True)
    print(f"Prompt set : {meta.get('title', '?')}")
    print(f"Selected   : {len(chosen)} prompt(s)")
    print(f"Output dir : {out_dir}\n")

    results = []
    for i, p in enumerate(chosen, 1):
        print(f"[{i}/{len(chosen)}] {p.id} ... ", end="", flush=True)
        res = await generate_prompt(p, out_dir)
        results.append(res.dict())
        if res.ok:
            print(f"OK ({res.seconds}s) -> {len(res.image_paths)} image(s)")
        else:
            print(f"FAILED: {res.error}")

    with open(os.path.join(out_dir, "results.json"), "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    await close_client()

    ok = sum(1 for r in results if r["ok"])
    print(f"\nDone: {ok}/{len(results)} succeeded. Manifest -> {out_dir}/results.json")


def _stamp_from(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    return base


def main():
    ap = argparse.ArgumentParser(description="Generate Gemini images from a prompt JSON file.")
    ap.add_argument("file", help="Path to a *-image-prompts.json file")
    ap.add_argument("--ids", nargs="*", help="Specific prompt ids")
    ap.add_argument("--index", nargs="*", type=int, help="0-based indices")
    ap.add_argument("--limit", type=int, help="Take first N")
    ap.add_argument("--out", help="Output directory")
    args = ap.parse_args()
    if not any([args.ids, args.index, args.limit]):
        args.limit = 3  # safe default
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
