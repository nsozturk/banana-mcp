#!/usr/bin/env python3
"""Banana MCP — generate images with your own Gemini (Nano Banana) session.

Exposes tools over MCP (stdio) that drive gemini.google.com's image generation
through the reverse-engineered StreamGenerate HTTP flow (no browser, headless by
nature). Auth comes from the cookie jar (see scripts/extract_cookies.py) resolved
by banana.config (BANANA_COOKIES -> ~/.config/banana-mcp/cookies.json -> repo).

Tools:
  - banana_account_status      : check that the Gemini session is authenticated
  - banana_generate_image      : generate from a free-form prompt string
  - banana_generate_from_file  : batch-generate from a *-image-prompts.json file
  - banana_list_prompts        : list prompt ids/titles inside a prompt file
"""
from __future__ import annotations

import json
import os

from mcp.server.fastmcp import FastMCP

from . import config
from .client import get_client
from .prompts import load_prompt_file, select
from .generator import generate, generate_prompt

mcp = FastMCP("banana-mcp")


def _resolve_out(out_dir: str | None, default_name: str) -> str:
    d = out_dir or os.path.join(config.DEFAULT_OUTPUT, default_name)
    os.makedirs(d, exist_ok=True)
    return d


@mcp.tool()
async def banana_account_status() -> str:
    """Verify the Gemini session is authenticated and image-capable.

    Returns a short JSON status. Run this first if generations fail — a
    'signed out' result means the cookie jar needs a fresh StorageDump export.
    """
    try:
        client = await get_client()
        status = await client.inspect_account_status()
        return json.dumps({"ok": True, "authenticated": True, "detail": str(status)[:800]})
    except Exception as e:  # noqa: BLE001
        return json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"})


@mcp.tool()
async def banana_generate_image(prompt: str, out_dir: str | None = None,
                                filename_stem: str = "image") -> str:
    """Generate an image from a free-form prompt and save it to disk.

    Args:
        prompt: The image prompt. May be plain text OR a serialized JSON
                "Nano Banana" prompt object.
        out_dir: Directory to save into (default: <output>/adhoc).
        filename_stem: Base name for the saved file(s).

    Returns JSON: {ok, image_paths, text, seconds}.
    """
    out = _resolve_out(out_dir, "adhoc")
    res = await generate(prompt, filename_stem, out)
    return json.dumps(res.dict(), ensure_ascii=False)


@mcp.tool()
async def banana_list_prompts(prompt_file: str) -> str:
    """List the prompt ids (and set title) inside a *-image-prompts.json file."""
    prompts, meta = load_prompt_file(prompt_file)
    return json.dumps({
        "title": meta.get("title"),
        "count": len(prompts),
        "ids": [p.id for p in prompts],
    }, ensure_ascii=False)


@mcp.tool()
async def banana_generate_from_file(prompt_file: str,
                                    ids: list[str] | None = None,
                                    indices: list[int] | None = None,
                                    limit: int | None = None,
                                    out_dir: str | None = None) -> str:
    """Batch-generate images from a structured prompt JSON file.

    Select prompts by `ids`, by 0-based `indices`, or take the first `limit`.
    If none are given, defaults to the first 3 (a safety cap — pass limit
    explicitly to run more).

    Returns JSON: {out_dir, total, ok, results:[{prompt_id, ok, image_paths, error, seconds}]}.
    """
    prompts, meta = load_prompt_file(prompt_file)
    if not any([ids, indices, limit]):
        limit = 3
    chosen = select(prompts, ids=ids, indices=indices, limit=limit)
    if not chosen:
        return json.dumps({"ok": False, "error": "no prompts selected"})

    name = os.path.splitext(os.path.basename(prompt_file))[0]
    out = _resolve_out(out_dir, name)

    results = []
    for p in chosen:
        res = await generate_prompt(p, out)
        results.append(res.dict())

    manifest = os.path.join(out, "results.json")
    with open(manifest, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["ok"])
    return json.dumps({
        "out_dir": out,
        "total": len(results),
        "ok": ok,
        "manifest": manifest,
        "results": results,
    }, ensure_ascii=False)


def main() -> None:
    """Console-script / module entry point."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
