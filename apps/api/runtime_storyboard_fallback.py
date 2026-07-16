from __future__ import annotations


def storyboard_fallback_message(reason: str | None, detail: str | None = None) -> str:
    if reason == "llm_gate_blocked":
        return "LLM gate is closed; deterministic local storyboard fallback was used."
    if reason == "provider_output_discarded":
        suffix = f" Reason: {detail}" if detail else ""
        return f"LLM output was not adopted; deterministic local storyboard fallback was used.{suffix}"
    if reason == "provider_call_failed":
        suffix = f" Reason: {detail}" if detail else ""
        return f"Provider call failed before usable storyboard output; deterministic local fallback was used.{suffix}"
    if reason == "provider_output_unavailable":
        return "Provider output was unavailable; deterministic local storyboard fallback was used."
    return ""


__all__ = ("storyboard_fallback_message",)
