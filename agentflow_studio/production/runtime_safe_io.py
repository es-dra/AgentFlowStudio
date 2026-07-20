from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any


SAFE_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_.-]+")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{Path(path).name} must be a JSON object")
    return payload


def safe_id(value: str, *, max_length: int = 120) -> str:
    cleaned = SAFE_ID_PATTERN.sub("-", str(value).strip()).strip("-._")
    if not cleaned:
        cleaned = "item"
    if len(cleaned) <= max_length:
        return cleaned
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]
    prefix = cleaned[: max(1, max_length - len(digest) - 1)].rstrip("-._") or "item"
    return f"{prefix}-{digest}"
