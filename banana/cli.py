#!/usr/bin/env python3
"""CLI batch generator (exposed as the `banana-generate` console script).

Examples:
    banana-generate examples/example-image-prompts.json --limit 3
    banana-generate file.json --ids some_id --preview-width 80
    banana-generate file.json --index 0 1 2 --out output/run1 --no-preview
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from . import config
from .prompts import load_prompt_file, select
from .generator import generate_prompt
from .client import close_client


async def run(args):
    prompts, meta = load_prompt_file(args.file)
    chosen = select(prompts, ids=args.ids, indices=args.index, limit=args.limit)
    if not chosen:
        sys.exit("No prompts selected.")

    out_dir = args.out or os.path.join(config.DEFAULT_OUTPUT, _stem(args.file))
    os.makedirs(out_dir, exist_ok=True)
    print(f"Prompt set : {meta.get('title', '?')}")
    print(f"Selected   : {len(chosen)} prompt(s)")
    print(f"Output dir : {out_dir}\n")

    results = []
    for i, p in enumerate(chosen, 1):
        print(f"[{i}/{len(chosen)}] {p.id} ... ", end="", flush=True)
        res = await generate_prompt(
            p, out_dir,
            preview=not args.no_preview, preview_color=True,
            preview_width=args.preview_width,
        )
        results.append(res.dict())
        if res.ok:
            print(f"OK ({res.seconds}s) -> {len(res.image_paths)} image(s)")
            if res.preview:
                print(res.preview)
                print()
        else:
            print(f"FAILED: {res.error}")

    with open(os.path.join(out_dir, "results.json"), "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    await close_client()

    ok = sum(1 for r in results if r["ok"])
    print(f"\nDone: {ok}/{len(results)} succeeded. Manifest -> {out_dir}/results.json")


def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def main():
    ap = argparse.ArgumentParser(description="Generate Gemini images from a prompt JSON file.")
    ap.add_argument("file", help="Path to a *-image-prompts.json file")
    ap.add_argument("--ids", nargs="*", help="Specific prompt ids")
    ap.add_argument("--index", nargs="*", type=int, help="0-based indices")
    ap.add_argument("--limit", type=int, help="Take first N")
    ap.add_argument("--out", help="Output directory")
    ap.add_argument("--no-preview", action="store_true",
                    help="Don't print a terminal preview of each image")
    ap.add_argument("--preview-width", type=int, default=64,
                    help="Preview width in characters (default 64)")
    args = ap.parse_args()
    if not any([args.ids, args.index, args.limit]):
        args.limit = 3  # safe default
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
