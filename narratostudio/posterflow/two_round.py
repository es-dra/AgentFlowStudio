from __future__ import annotations

from typing import Any

from narratostudio.posterflow.schemas import (
    ContextBundle,
    NextRoundPrompt,
    PosterCandidatesManifest,
    PosterMemoryCandidates,
    PosterModelInvocations,
    PosterPreferenceProfile,
    PosterPromptPack,
)


def build_round_2_prompt_pack(
    previous_prompt: PosterPromptPack,
    next_prompt: NextRoundPrompt,
) -> PosterPromptPack:
    memory_refs = list(next_prompt.memory_context.get("memory_refs", []))
    promotion_decision_refs = list(next_prompt.memory_context.get("promotion_decision_refs", []))
    return PosterPromptPack(
        project_id=next_prompt.project_id,
        run_id=next_prompt.new_run_id,
        prompt_id=f"{next_prompt.new_run_id}_poster_prompt_001",
        target_model_family=previous_prompt.target_model_family,
        prompt_language=previous_prompt.prompt_language,
        positive_prompt=next_prompt.composed_positive_prompt,
        negative_prompt=next_prompt.composed_negative_prompt,
        prompt_sections={
            **previous_prompt.prompt_sections,
            "memory_context": ", ".join(memory_refs),
            "task_delta": str(next_prompt.task_delta),
        },
        model_params=dict(previous_prompt.model_params),
        context_usage={
            "project_prefix_used": True,
            "preference_profile_used": True,
            "context_bundle_used": bool(next_prompt.memory_context.get("context_bundle_path")),
            "memory_refs": memory_refs,
            "promotion_decision_refs": promotion_decision_refs,
            "context_bundle_path": next_prompt.memory_context.get("context_bundle_path"),
            "cache_key": next_prompt.memory_context.get("cache_key"),
        },
        source_refs={
            "previous_prompt_pack": "poster_prompt_pack.json",
            "next_round_prompt": "next_round_prompt.json",
            "preference_profile": "poster_preference_profile.json",
            "context_bundle": str(next_prompt.memory_context.get("context_bundle_path") or ""),
        },
    )


def prefix_candidate_paths(
    manifest: PosterCandidatesManifest,
    invocations: PosterModelInvocations,
    *,
    path_prefix: str,
) -> tuple[PosterCandidatesManifest, PosterModelInvocations]:
    prefix = path_prefix.strip("/\\")
    candidates = [
        candidate.model_copy(update={"image_path": f"{prefix}/{candidate.image_path}"})
        for candidate in manifest.candidates
    ]
    prefixed_invocations = [
        invocation.model_copy(
            update={"output_files": [f"{prefix}/{path}" for path in invocation.output_files]}
        )
        for invocation in invocations.invocations
    ]
    return (
        manifest.model_copy(
            update={
                "candidates": candidates,
                "source_refs": {
                    **manifest.source_refs,
                    "poster_prompt_pack": f"{prefix}/poster_prompt_pack.json",
                    "round_dir": prefix,
                    "next_round_prompt": "next_round_prompt.json",
                },
            }
        ),
        invocations.model_copy(update={"invocations": prefixed_invocations}),
    )


def build_round_comparison(
    *,
    round_1_manifest: PosterCandidatesManifest,
    round_2_manifest: PosterCandidatesManifest,
    memory: PosterMemoryCandidates,
    profile: PosterPreferenceProfile,
    next_prompt: NextRoundPrompt,
    context_bundle: ContextBundle | None,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "artifact_type": "poster_round_comparison",
        "project_id": profile.project_id,
        "round_1": _round_summary(round_1_manifest),
        "round_2": _round_summary(round_2_manifest),
        "memory_reuse": {
            "preference_profile_path": next_prompt.memory_context.get("preference_profile_path"),
            "context_bundle_path": next_prompt.memory_context.get("context_bundle_path"),
            "cache_key": next_prompt.memory_context.get("cache_key"),
            "memory_refs": list(profile.source_memory_candidates),
            "promotion_decision_refs": list(profile.source_promotion_decisions),
            "memory_candidate_count": len(memory.candidates),
            "writes_long_term_memory": False,
        },
        "prompt_diff": dict(next_prompt.diff_from_previous_prompt),
        "acceptance_evidence": [
            "round_2 prompt pack uses next_round_prompt composed prompt",
            "round_2 candidates were generated from the memory-aware prompt pack",
            "comparison records reused memory refs without durable long-term writes",
        ],
        "evidence_chain": _evidence_chain(profile, next_prompt, context_bundle),
        "validation_boundary": (
            "demo evidence only; passing artifacts prove workflow structure and memory reuse, "
            "not human acceptance or business validation"
        ),
        "context_bundle_id": context_bundle.bundle_id if context_bundle else None,
    }


def render_two_round_report(comparison: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PosterFlow Two-Round Memory Demo",
            "",
            "## Round 1",
            f"- Run ID: {comparison['round_1']['run_id']}",
            f"- Candidates: {comparison['round_1']['candidate_count']}",
            "",
            "## Round 2",
            f"- Run ID: {comparison['round_2']['run_id']}",
            f"- Candidates: {comparison['round_2']['candidate_count']}",
            "",
            "## Memory Reuse",
            *[f"- {item}" for item in comparison["memory_reuse"]["memory_refs"]],
            "",
            "## Evidence Chain",
            *[
                f"- {item['stage']}: {', '.join(item['artifact_refs'])}"
                for item in comparison.get("evidence_chain", [])
            ],
            "",
            "## Boundary",
            comparison["validation_boundary"],
            "",
        ]
    )


def _round_summary(manifest: PosterCandidatesManifest) -> dict[str, Any]:
    return {
        "run_id": manifest.run_id,
        "prompt_id": manifest.prompt_id,
        "candidate_count": len(manifest.candidates),
        "candidate_images": [candidate.image_path for candidate in manifest.candidates],
        "provider_mode": manifest.provider_mode,
    }


def _evidence_chain(
    profile: PosterPreferenceProfile,
    next_prompt: NextRoundPrompt,
    context_bundle: ContextBundle | None,
) -> list[dict[str, Any]]:
    return [
        {
            "stage": "round_1_evidence",
            "artifact_refs": [
                "poster_candidates_manifest.json",
                "poster_feedback.jsonl",
                "poster_feedback_signal_log.json",
            ],
            "source_refs": {},
            "summary": "Round 1 generated candidates plus raw feedback produce derived feedback signals.",
            "writes_long_term_memory": False,
        },
        {
            "stage": "candidate_memory",
            "artifact_refs": ["poster_memory_candidates.jsonl", "poster_memory_candidates.json"],
            "source_refs": {"feedback_signal_log": "poster_feedback_signal_log.json"},
            "summary": "Derived feedback signals become candidate-only project preference memory.",
            "writes_long_term_memory": False,
        },
        {
            "stage": "review_decision",
            "artifact_refs": ["poster_memory_decisions.json", "poster_memory_review.jsonl"],
            "source_refs": {"memory_candidates": "poster_memory_candidates.jsonl"},
            "summary": "Demo review gate accepts candidates for downstream profile use only.",
            "writes_long_term_memory": False,
        },
        {
            "stage": "context_bundle",
            "artifact_refs": ["poster_preference_profile.json", "project_prefix.md", "context_bundle.json"],
            "source_refs": {
                "memory_review": "poster_memory_review.jsonl",
                "promotion_decision_refs": _joined(profile.source_promotion_decisions),
                "profile_memory_refs": ", ".join(profile.source_memory_candidates),
            },
            "summary": "Reviewed candidates feed a demo-only profile and context bundle.",
            "writes_long_term_memory": False,
        },
        {
            "stage": "round_2_reuse",
            "artifact_refs": ["next_round_prompt.json", "round_2/poster_prompt_pack.json"],
            "source_refs": {
                "context_bundle": next_prompt.memory_context.get("context_bundle_path") or "",
                "promotion_decision_refs": _joined(profile.source_promotion_decisions),
                "cache_key": str(next_prompt.memory_context.get("cache_key") or ""),
            },
            "summary": "Round 2 prompt pack reuses context refs from the next-round prompt.",
            "writes_long_term_memory": False,
        },
        {
            "stage": "comparison_output",
            "artifact_refs": ["poster_round_comparison.json", "poster_two_round_report.md"],
            "source_refs": {"context_bundle_id": context_bundle.bundle_id if context_bundle else ""},
            "summary": "Comparison records reuse evidence without claiming acceptance or durable memory.",
            "writes_long_term_memory": False,
        },
    ]


def _joined(values: list[str]) -> str:
    return ", ".join(sorted(values))
