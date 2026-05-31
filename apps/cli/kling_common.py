from __future__ import annotations

from pathlib import Path


def display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")
