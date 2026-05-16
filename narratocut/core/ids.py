from __future__ import annotations

from uuid import uuid4


def new_id(prefix: str) -> str:
    safe_prefix = prefix.strip().lower().replace(" ", "_")
    if not safe_prefix:
        raise ValueError("prefix must not be empty")
    return f"{safe_prefix}_{uuid4().hex[:12]}"
