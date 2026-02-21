from __future__ import annotations

import re

_slug_re = re.compile(r"[^a-z0-9]+", re.IGNORECASE)


def slugify(text: str) -> str:
    t = (text or "").strip().lower()
    t = _slug_re.sub("-", t).strip("-")
    return t or "form"
