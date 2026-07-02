"""Load and serialize the structured image-prompt JSON files.

Each prompt file looks like:
    { "prompt_set": {...}, "prompts": [ {"id": "...", "subject": {...}}, ... ] }

The whole prompt object (or just its `subject`) is serialized to a JSON string
and sent to Gemini as the message text — the "Nano Banana JSON workflow" style.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class Prompt:
    id: str
    obj: dict
    source: str  # file it came from

    def to_text(self, include_global_constraints: list | None = None) -> str:
        """Serialize this prompt to the text sent to Gemini."""
        payload = dict(self.obj)
        if include_global_constraints:
            payload = {
                "global_constraints": include_global_constraints,
                **payload,
            }
        return json.dumps(payload, ensure_ascii=False, indent=2)


def load_prompt_file(path: str) -> tuple[list[Prompt], dict]:
    """Return (prompts, prompt_set_meta)."""
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    with open(path) as f:
        data = json.load(f)
    meta = data.get("prompt_set", {})
    out = []
    for p in data.get("prompts", []):
        pid = p.get("id") or f"prompt_{len(out)+1:03d}"
        out.append(Prompt(id=pid, obj=p, source=os.path.basename(path)))
    return out, meta


def select(prompts: list[Prompt], ids: list[str] | None = None,
           indices: list[int] | None = None, limit: int | None = None) -> list[Prompt]:
    """Pick a subset by id, by 0-based index, or just the first `limit`."""
    if ids:
        idset = set(ids)
        chosen = [p for p in prompts if p.id in idset]
    elif indices is not None:
        chosen = [prompts[i] for i in indices if 0 <= i < len(prompts)]
    else:
        chosen = prompts
    if limit is not None:
        chosen = chosen[:limit]
    return chosen
