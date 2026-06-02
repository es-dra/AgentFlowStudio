from __future__ import annotations

from typing import Any


def render_asset_profile_promotion_decision_markdown(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Production Memory Asset Profile Promotion Decision",
            "",
            f"Decision: {decision.get('decision', 'unknown')}",
            f"Decision effect: {decision.get('decision_effect', 'unknown')}",
            f"Candidate: {decision.get('candidate_id', 'unknown')}",
            f"Profile: {decision.get('profile_id', 'unknown')}",
            f"Creates profile version: {str(decision.get('creates_profile_version') is True).lower()}",
            "Provider calls: not started",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            "",
            "## Rationale",
            str(decision.get("rationale", "")),
            "",
        ]
    )


def render_asset_profile_version_markdown(version: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Production Memory Asset Profile Version",
            "",
            f"Profile: {version.get('profile_id', 'unknown')}",
            f"Version: {version.get('profile_version', 'unknown')}",
            f"Supersedes: {version.get('source_profile_id', 'unknown')}",
            f"Source decision: {version.get('source_decision_id', 'unknown')}",
            f"Usable for next context: {str(version.get('usable_for_next_context') is True).lower()}",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            "",
        ]
    )


__all__ = (
    "render_asset_profile_promotion_decision_markdown",
    "render_asset_profile_version_markdown",
)
