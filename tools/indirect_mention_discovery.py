"""Deterministic discovery of suspected indirect mention candidates.

Production implementation lives in
`apps.api.runtime_script_indirect_mention_discovery`. This module re-exports
it so exploratory tools and older imports stay aligned.

COST NOTE: discovery itself is free/deterministic. Semantic judgment is a
*paid* remote LLM path gated by AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS
(see apps.api.runtime_script_indirect_mention_proposals).
"""

from __future__ import annotations

from apps.api.runtime_script_indirect_mention_discovery import (
    context_window,
    discover_indirect_mention_candidates,
)

__all__ = (
    "context_window",
    "discover_indirect_mention_candidates",
)
