from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class LLMProvider(Protocol):
    """Minimal text-generation contract for AgentFlow Studio providers."""

    def generate(self, prompt: str, *, task_type: str | None = None) -> str:
        """Return model output as text."""


class LLMResponse(BaseModel):
    """Structured response metadata for providers that can report it."""

    text: str
    provider: str
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
