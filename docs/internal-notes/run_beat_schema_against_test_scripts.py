#!/usr/bin/env python3
"""Local acceptance run for the design-stage Beat schema.

This script intentionally does not import ``apps/api``. It verifies that the
six current scripts fail closed when beat boundaries are not textually marked,
then uses one human-reviewed range to prove CandidateFact, confirmation,
promotion, and revision invalidation reuse without a Beat-specific state machine.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from draft_beat_schema_20260803 import (  # noqa: E402
    BeatConflict,
    BeatEmotionShift,
    BeatInfoRelease,
    BeatTurn,
    assess_beat_segmentation,
    beat_version_to_candidate_facts,
    build_beat_entity_from_reviewed_range,
    claimed_text_from_exact_quote,
)
from draft_candidate_confirmation_loop_20260802 import (  # noqa: E402
    FactLedger,
    ReviewAction,
    ReviewDecision,
    accept_candidate,
    candidate_fact_to_review_item,
    edit_and_confirm_candidate,
    list_current_authoritative,
    on_script_revision_changed,
)
from draft_candidate_fact_status_model_20260802 import (  # noqa: E402
    CandidateStatus,
    PromotionError,
    promote_candidate_fact,
)


SCRIPTS = _HERE / "test-scripts-character-scene"
SCRIPT_FILES = tuple(sorted(SCRIPTS.glob("[0-9][0-9]_*.txt")))


def _version(entity):
    return next(item for item in entity.versions if item.version_id == entity.head_version_id)


def evaluate_six_scripts() -> tuple[bool, list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    ok = len(SCRIPT_FILES) == 6
    for path in SCRIPT_FILES:
        source = path.read_text(encoding="utf-8")
        result = assess_beat_segmentation(source)
        passed = (
            result.status == "missing"
            and result.explicit_marker_count == 0
            and result.boundary_candidates == []
        )
        ok = ok and passed
        rows.append(
            {
                "file": path.name,
                "status": result.status,
                "beat_candidates_emitted": len(result.boundary_candidates),
                "explicit_marker_count": result.explicit_marker_count,
                "scene_heading_count": result.scene_heading_count,
                "paragraph_break_count": result.paragraph_break_count,
                "pass": passed,
            }
        )
    return ok, rows


def evaluate_explicit_marker_control() -> bool:
    source = "节拍1：进入\n角色推门。\n节拍2：变化\n灯亮了。"
    result = assess_beat_segmentation(source)
    return (
        result.status == "explicit_boundaries"
        and result.explicit_marker_count == 2
        and len(result.boundary_candidates) == 2
    )


def evaluate_schema_and_confirmation_reuse() -> dict[str, bool]:
    source = (SCRIPTS / "01_industry_standard_last_light.txt").read_text(encoding="utf-8")
    snippet = (
        "她转动一个老旧的开关。什么都没发生。然后，灯缓缓亮起，"
        "温暖的金色光芒洒向波涛汹涌的大海。"
    )
    start = source.index(snippet)
    end = start + len(snippet)

    conflict_claim = claimed_text_from_exact_quote(
        source,
        "什么都没发生",
        confidence=0.95,
        scope_start=start,
        scope_end=end,
    )
    turn_claim = claimed_text_from_exact_quote(
        source,
        "然后，灯缓缓亮起",
        confidence=0.95,
        scope_start=start,
        scope_end=end,
    )
    info_claim = claimed_text_from_exact_quote(
        source,
        "灯缓缓亮起",
        confidence=0.9,
        scope_start=start,
        scope_end=end,
    )
    entity = build_beat_entity_from_reviewed_range(
        source,
        project_id="proj_beat_design",
        source_revision_id="scrrev_beat_v1",
        scene_id="scene_lighthouse_1",
        order_index=0,
        source_start=start,
        source_end=end,
        boundary_determination="human_confirmed",
        boundary_uncertainty_note=(
            "the script has no beat label; this range is a human boundary decision"
        ),
        conflict=BeatConflict(status="present", tension=conflict_claim),
        turn=BeatTurn(status="present", change=turn_claim),
        info_release=BeatInfoRelease(status="present", information=info_claim),
        emotion_shift=BeatEmotionShift(
            status="missing",
            uncertainty_note="no explicit from/to emotion evidence inside this range",
        ),
    )
    version = _version(entity)
    facts = beat_version_to_candidate_facts(version)
    by_path = {fact.field_path: fact for fact in facts}

    missing_emotion = by_path["beat.emotion_shift"]
    missing_review = candidate_fact_to_review_item(
        missing_emotion,
        producer_method="reviewed_beat_range",
    )
    missing_promotion_blocked = False
    try:
        promote_candidate_fact(
            missing_emotion,
            authoritative_fact_id="auth_missing_must_not_promote",
        )
    except PromotionError:
        missing_promotion_blocked = True

    invalid_present_emotion_blocked = False
    try:
        BeatEmotionShift(status="present", change=turn_claim)
    except ValidationError:
        invalid_present_emotion_blocked = True

    outside_claim = claimed_text_from_exact_quote(
        source,
        "玛雅走到外面",
        confidence=0.9,
    )
    outside_evidence_blocked = False
    try:
        build_beat_entity_from_reviewed_range(
            source,
            project_id="proj_beat_design",
            source_revision_id="scrrev_beat_v1",
            scene_id="scene_lighthouse_1",
            order_index=0,
            source_start=start,
            source_end=end,
            boundary_determination="human_confirmed",
            conflict=BeatConflict(status="present", tension=outside_claim),
        )
    except ValidationError:
        outside_evidence_blocked = True

    ledger = FactLedger(
        project_id=version.project_id,
        current_revision_id=version.source_revision_id,
        current_revision_digest=version.source_revision_digest,
        candidates={fact.fact_id: fact for fact in facts},
        review_decisions={fact.fact_id: ReviewDecision.PENDING for fact in facts},
    )
    accepted = accept_candidate(
        ledger,
        by_path["beat.conflict.tension"].fact_id,
        human_id="beat_reviewer",
        reason="conflict claim matches reviewed source range",
    )
    corrected = edit_and_confirm_candidate(
        ledger,
        by_path["beat.turn.change"].fact_id,
        new_text="灯缓缓亮起",
        human_id="beat_reviewer",
        reason="remove connective from the confirmed turn text",
        source_text=source,
    )
    current = list_current_authoritative(ledger)
    invalidated = on_script_revision_changed(
        ledger,
        new_revision_id="scrrev_beat_v2",
        new_source_text=source + "\n",
        actor_id="beat_design_test",
    )

    return {
        "entity_kind_beat": all(fact.entity_kind == "beat" for fact in facts),
        "four_facet_candidates": len(facts) == 4,
        "emotion_is_explicit_missing": (
            missing_emotion.status == CandidateStatus.MISSING
            and missing_emotion.claim.evidence_spans == []
            and ReviewAction.ACCEPT not in missing_review.allowed_actions
        ),
        "missing_cannot_promote": missing_promotion_blocked,
        "emotion_present_requires_from_and_to": invalid_present_emotion_blocked,
        "out_of_boundary_evidence_rejected": outside_evidence_blocked,
        "existing_accept_promotes_beat": (
            accepted.fact.entity_kind == "beat"
            and accepted.fact.field_path == "beat.conflict.tension"
        ),
        "existing_edit_confirm_promotes_correction": (
            corrected.fact.entity_kind == "beat" and corrected.fact.text == "灯缓缓亮起"
        ),
        "current_authority_contains_only_confirmed": (
            len(current) == 2
            and all(fact.entity_kind == "beat" for fact in current)
            and all(fact.text != "(missing)" for fact in current)
        ),
        "revision_invalidation_reused": (
            len(invalidated) == 2 and list_current_authoritative(ledger) == []
        ),
    }


def main() -> int:
    scripts_ok, script_rows = evaluate_six_scripts()
    explicit_control_ok = evaluate_explicit_marker_control()
    reuse_checks = evaluate_schema_and_confirmation_reuse()
    result = {
        "scope": "design_and_local_validation_only",
        "six_script_segmentation": script_rows,
        "six_scripts_fail_closed": scripts_ok,
        "explicit_marker_control": explicit_control_ok,
        "schema_and_confirmation_reuse": reuse_checks,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    all_ok = scripts_ok and explicit_control_ok and all(reuse_checks.values())
    print("ALL PASS" if all_ok else "SOME FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
