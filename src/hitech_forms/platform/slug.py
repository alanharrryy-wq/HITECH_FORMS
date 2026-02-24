from __future__ import annotations

import re

_slug_re = re.compile(r"[^a-z0-9-]+", re.IGNORECASE)


def slugify(text: str) -> str:
    t = (text or "").strip().lower()
    t = _slug_re.sub("-", t).strip("-")
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t or "form"


def stable_slug(base_text: str, taken_slugs: set[str]) -> str:
    base_slug = slugify(base_text)
    if base_slug not in taken_slugs:
        return base_slug
    suffix = 2
    while True:
        candidate = f"{base_slug}-{suffix}"
        if candidate not in taken_slugs:
            return candidate
        suffix += 1
