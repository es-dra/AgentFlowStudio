from __future__ import annotations

from typing import Any, Callable


TextSanitizer = Callable[[Any, str, int], str]


def sanitize_human_gate_decisions(value: Any, *, text: TextSanitizer) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        decision = {
            "human_gate_id": text(item.get("human_gate_id"), "", 160),
            "target_type": text(item.get("target_type"), "", 80),
            "target_id": text(item.get("target_id"), "", 160),
            "decision": text(item.get("decision"), "", 80),
            "status": text(item.get("status"), "", 80),
            "recorded_at": text(item.get("recorded_at"), "", 80),
            "writes_long_term_memory": bool(item.get("writes_long_term_memory")),
        }
        if decision["human_gate_id"] or decision["target_id"]:
            decisions.append(decision)
        if len(decisions) >= 12:
            break
    return decisions


__all__ = ("sanitize_human_gate_decisions",)
