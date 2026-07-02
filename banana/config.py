"""Configuration + cookie loading for the banana Gemini client."""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cookies that carry the auth. The rest of the jar is passed through as well so
# rotation / consistency checks on Google's side see a full, coherent session.
PRIMARY = "__Secure-1PSID"
ROTATING = "__Secure-1PSIDTS"


def _config_home() -> str:
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")


def user_cookies_path() -> str:
    """Canonical per-user cookie location (used by pip/uvx/plugin installs)."""
    return os.path.join(_config_home(), "banana-mcp", "cookies.json")


def _repo_cookies_path() -> str:
    return os.path.join(ROOT, "secrets", "cookies.json")


def resolve_cookies_path() -> str:
    """First existing cookie file, in priority order:
    $BANANA_COOKIES -> ~/.config/banana-mcp/cookies.json -> <repo>/secrets/cookies.json.
    Falls back to the user path (for a clear 'not found' message) if none exist.
    """
    env = os.environ.get("BANANA_COOKIES")
    if env:
        return env
    for p in (user_cookies_path(), _repo_cookies_path()):
        if os.path.isfile(p):
            return p
    return user_cookies_path()


# Where generated images land. $BANANA_OUTPUT wins; else a repo-local ./output
# when running from a clone; else ./output in the current working directory.
DEFAULT_OUTPUT = os.environ.get("BANANA_OUTPUT") or (
    os.path.join(ROOT, "output")
    if os.path.isdir(os.path.join(ROOT, "banana"))
    else os.path.join(os.getcwd(), "output")
)

# Back-compat alias.
SECRETS = user_cookies_path()


def load_cookies(path: str | None = None) -> dict[str, str]:
    path = path or resolve_cookies_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Cookie file not found: {path}\n"
            "Export a StorageDump from gemini.google.com, then run:\n"
            "  python scripts/extract_cookies.py <storagedump_folder>"
        )
    with open(path) as f:
        jar = json.load(f)
    if PRIMARY not in jar or not jar[PRIMARY]:
        raise ValueError(f"Cookie file missing required key: {PRIMARY}")
    return jar


def auth_pair(path: str | None = None) -> tuple[str, str | None]:
    """Return (secure_1psid, secure_1psidts|None) for GeminiClient.

    __Secure-1PSIDTS is optional; gemini_webapi rotates/derives it at runtime.
    """
    jar = load_cookies(path)
    return jar[PRIMARY], jar.get(ROTATING)
