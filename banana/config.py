"""Configuration + cookie loading for the banana Gemini client."""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS = os.path.join(ROOT, "secrets", "cookies.json")
DEFAULT_OUTPUT = os.path.join(ROOT, "output")

# Cookies that carry the auth. The rest of the jar is passed through as well so
# rotation / consistency checks on Google's side see a full, coherent session.
PRIMARY = "__Secure-1PSID"
ROTATING = "__Secure-1PSIDTS"


def load_cookies(path: str | None = None) -> dict[str, str]:
    path = path or os.environ.get("BANANA_COOKIES", SECRETS)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Cookie file not found: {path}\n"
            "Run: python scripts/extract_cookies.py <storagedump_folder>"
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
