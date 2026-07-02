"""Runtime dependency bootstrap — pip AND uv compatible.

The terminal-preview / hero-render helpers depend on a few packages (Pillow,
and rich + cairosvg for PNG export). They're declared in pyproject.toml so a
`pip`/`uvx` install already has them, but for a bare `git clone` — or a uv venv
where `pip` isn't present — we self-install on first use.

Installer selection:
  - if `uv` is on PATH  -> `uv pip install --python <this-python> <pkg>`
    (works in both uv-managed and standard venvs, and in envs with no pip)
  - else                -> `<this-python> -m pip install <pkg>`
"""
from __future__ import annotations

import importlib
import shutil
import subprocess
import sys

_installed: set[str] = set()


def _pip_install(pkg: str) -> None:
    if shutil.which("uv"):
        cmd = ["uv", "pip", "install", "--python", sys.executable, pkg]
    else:
        cmd = [sys.executable, "-m", "pip", "install", pkg]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def ensure_package(import_name: str, pip_name: str | None = None):
    """Import `import_name`, auto-installing `pip_name` (default: top-level of
    import_name) if it's missing. Returns the imported module.
    """
    try:
        return importlib.import_module(import_name)
    except ImportError:
        pass

    pkg = pip_name or import_name.split(".")[0]
    if pkg not in _installed:
        try:
            _pip_install(pkg)
            _installed.add(pkg)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            detail = getattr(e, "stderr", "") or str(e)
            raise RuntimeError(
                f"Could not auto-install '{pkg}'. Install it manually "
                f"(`pip install {pkg}` or `uv pip install {pkg}`).\n{detail}"
            ) from e
        importlib.invalidate_caches()
    return importlib.import_module(import_name)
