"""Core generation logic: send a prompt to Gemini, save any returned images."""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field, asdict

from . import config
from .client import get_client
from .prompts import Prompt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Image-capable model header, mirrored from a working gemini.google.com
# StreamGenerate request (HAR). The capability array [4,5,6,8] is what unlocks
# image generation — the library default sends only [4] and the model then
# refuses ("can't create images"). model id 56fdd199312815e2 == gemini-3-flash.
IMAGE_MODEL = {
    "model_name": "gemini-3-flash-image",
    "model_header": {
        "x-goog-ext-525001261-jspb": '[1,null,null,null,"56fdd199312815e2",null,null,0,[4,5,6,8],null,null,6]',
        "x-goog-ext-73010989-jspb": "[0]",
        "x-goog-ext-73010990-jspb": "[0,0,0]",
    },
}


def _slug(s: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")
    return s[:maxlen] or "image"


def _ext_for(path: str) -> str:
    """Sniff magic bytes and return the correct image extension."""
    try:
        with open(path, "rb") as f:
            head = f.read(12)
    except OSError:
        return ".bin"
    if head[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return ".bin"


@dataclass
class GenResult:
    prompt_id: str
    ok: bool
    text: str = ""
    image_paths: list[str] = field(default_factory=list)
    error: str = ""
    seconds: float = 0.0
    preview: str = ""  # terminal preview of the first saved image (optional)

    def dict(self) -> dict:
        return asdict(self)


async def generate(prompt_text: str, prompt_id: str, out_dir: str,
                   model: dict | str | None = None,
                   max_retries: int = 2,
                   preview: bool = False, preview_color: bool = True,
                   preview_width: int = 64) -> GenResult:
    """Send one prompt, download every generated image into out_dir.

    Returns a GenResult with saved file paths (empty if the model returned no
    image — e.g. a text refusal, which is surfaced in `.text`). When `preview`
    is set, `.preview` holds a terminal preview of the first saved image
    (preview failures never fail the generation).
    """
    os.makedirs(out_dir, exist_ok=True)
    client = await get_client()
    if model is None:
        model = IMAGE_MODEL

    last_err = ""
    for attempt in range(1, max_retries + 1):
        t0 = time.monotonic()
        try:
            output = await client.generate_content(prompt_text, model=model)
        except Exception as e:  # noqa: BLE001 - surface any transport/auth error
            last_err = f"{type(e).__name__}: {e}"
            # brief backoff before retry
            continue

        elapsed = time.monotonic() - t0
        images = output.images or []
        saved: list[str] = []
        for i, img in enumerate(images):
            base = f"{_slug(prompt_id)}_{i:02d}"
            tmp = os.path.join(out_dir, base + ".download")
            try:
                await img.save(path=out_dir, filename=base + ".download", verbose=False)
                final = os.path.join(out_dir, base + _ext_for(tmp))
                os.replace(tmp, final)
                saved.append(final)
            except Exception as e:  # noqa: BLE001
                last_err = f"save failed: {type(e).__name__}: {e}"

        preview_str = ""
        if preview and saved:
            try:
                from .preview import render_preview
                preview_str = render_preview(saved[0], width=preview_width,
                                             color=preview_color)
            except Exception as e:  # noqa: BLE001 - preview is best-effort
                preview_str = f"(preview unavailable: {type(e).__name__}: {e})"

        return GenResult(
            prompt_id=prompt_id,
            ok=bool(saved),
            text=(output.text or "")[:2000],
            image_paths=saved,
            error="" if saved else (last_err or "no image returned by model"),
            seconds=round(elapsed, 1),
            preview=preview_str,
        )

    return GenResult(prompt_id=prompt_id, ok=False, error=last_err or "unknown error")


async def generate_prompt(p: Prompt, out_dir: str, **kw) -> GenResult:
    return await generate(p.to_text(), p.id, out_dir, **kw)
