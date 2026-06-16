from __future__ import annotations


ALGORITHM_ID = "afs.skill_action_selection.v0.1"
INPUT_CONTRACT = "task intent, asset type, provider gates, allowed actions"
OUTPUT_CONTRACT = "whitelisted action mode with reason"
FAILURE_MODES = ("unknown_intent", "capability_not_allowed", "unsafe_action_rejected")
EVIDENCE_BOUNDARY = "selection emits a safe action label, not arbitrary tool execution"

ALLOWED_ACTIONS = {
    "asset_card_draft": {"vision"},
    "keyframe_generation": {"image"},
    "video_generation": {"video"},
    "prompt_optimization": {"llm"},
}


def select_action(intent: str, allowed_actions: set[str] | None = None) -> dict[str, str]:
    allowed = allowed_actions or set(ALLOWED_ACTIONS)
    action = intent if intent in allowed else "manual_review"
    return {
        "action": action,
        "mode": "allowed" if action != "manual_review" else "blocked",
        "reason": "whitelisted_action" if action != "manual_review" else "intent_not_whitelisted",
    }


__all__ = (
    "ALGORITHM_ID",
    "ALLOWED_ACTIONS",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "select_action",
)
