"""Terminal image preview — hybrid engine.

render_preview(path) returns a string you can print to a terminal:
  1. if `chafa` (the most capable terminal image viewer) is on PATH, use it
     for truecolor/sixel-quality output;
  2. otherwise fall back to a pure-Python Pillow renderer using the `▄`
     half-block trick (two vertical pixels per character cell, 24-bit ANSI).

color=False returns a plain ASCII-ramp version (no ANSI) that renders anywhere,
including MCP tool transcripts. Pillow is auto-installed on first use.
"""
from __future__ import annotations

import shutil
import subprocess

from ._bootstrap import ensure_package

# dark -> light luminance ramp for the plain-ASCII mode
_RAMP = " .:-=+*#%@"
_HALF = "▄"  # ▄ lower half block


def _chafa(image_path: str, width: int) -> str | None:
    """Try chafa; return its output, or None if unavailable/failed."""
    if not shutil.which("chafa"):
        return None
    try:
        out = subprocess.run(
            ["chafa", "--format=symbols", f"--size={width}x{width}", image_path],
            capture_output=True, text=True, timeout=20,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.rstrip("\n")
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _load_rgb(image_path: str):
    Image = ensure_package("PIL.Image", "Pillow")
    img = Image.open(image_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img, Image


def _rows_for(width: int, iw: int, ih: int, pixels_per_cell: int) -> int:
    """Rows so the preview keeps the image aspect (cells are ~1 wide × N tall)."""
    rows = round(width * (ih / iw) / pixels_per_cell)
    return max(1, rows)


def _render_blocks(image_path: str, width: int) -> str:
    """Pure-Python truecolor preview using the ▄ half-block (2 px per cell)."""
    img, Image = _load_rgb(image_path)
    iw, ih = img.size
    rows = _rows_for(width, iw, ih, 2)
    img = img.resize((width, rows * 2), Image.LANCZOS)
    px = img.load()
    lines = []
    for r in range(rows):
        cell = []
        for c in range(width):
            tr, tg, tb = px[c, r * 2]        # top pixel -> background
            br, bg, bb = px[c, r * 2 + 1]    # bottom pixel -> foreground (▄)
            cell.append(
                f"\x1b[38;2;{br};{bg};{bb};48;2;{tr};{tg};{tb}m{_HALF}"
            )
        lines.append("".join(cell) + "\x1b[0m")
    return "\n".join(lines)


def _render_ascii(image_path: str, width: int) -> str:
    """Plain ASCII ramp (no ANSI) — renders in any context."""
    img, Image = _load_rgb(image_path)
    iw, ih = img.size
    rows = _rows_for(width, iw, ih, 2)  # ~2:1 char aspect
    img = img.resize((width, rows), Image.LANCZOS).convert("L")
    px = img.load()
    n = len(_RAMP) - 1
    lines = []
    for r in range(rows):
        lines.append("".join(_RAMP[int(px[c, r] / 255 * n)] for c in range(width)))
    return "\n".join(lines)


def render_preview(image_path: str, width: int = 64, color: bool = True) -> str:
    """Return a terminal-printable preview of an image file.

    color=True  -> chafa if present, else truecolor ▄ half-blocks.
    color=False -> plain ASCII ramp (safe for transcripts / no-ANSI sinks).
    """
    if color:
        out = _chafa(image_path, width)
        if out is not None:
            return out
        return _render_blocks(image_path, width)
    return _render_ascii(image_path, width)


def preview_to_png(ansi_or_text: str, out_path: str, width: int = 64,
                   title: str = "banana-mcp") -> str:
    """Render a (possibly ANSI-colored) preview string to a PNG via rich+cairosvg.

    Fully headless — used for the README hero. Returns out_path.
    """
    rich_console = ensure_package("rich.console", "rich")
    rich_text = ensure_package("rich.text", "rich")
    cairosvg = ensure_package("cairosvg", "cairosvg")

    text = rich_text.Text.from_ansi(ansi_or_text)
    console = rich_console.Console(record=True, width=width, legacy_windows=False)
    console.print(text)
    svg = console.export_svg(title=title)
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=out_path)
    return out_path
