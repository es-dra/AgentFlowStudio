from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessResult:
    job_id: str
    status: str
    job_dir: Path


__all__ = ("ProcessResult",)
