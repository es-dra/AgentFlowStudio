from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Minimal text-generation contract for NarratoCut providers."""

    def generate(self, prompt: str, *, task_type: str | None = None) -> str:
        """Return model output as text."""
