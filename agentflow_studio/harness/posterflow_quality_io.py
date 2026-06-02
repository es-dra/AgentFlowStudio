from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from agentflow_studio.production.posterflow import (
    ContextAssemblyTrace,
    ContextBundle,
    NextRoundPrompt,
    PosterBrief,
    PosterCandidatesManifest,
    PosterFeedbackSignalLog,
    PosterMemoryCandidates,
    PosterPreferenceProfile,
    PosterPromptPack,
)
from agentflow_studio.production.posterflow.schemas import (
    PosterMemoryCandidate,
    PosterMemoryDecisions,
    PosterMemoryReviewEvent,
    PosterModelInvocations,
    PosterPlan,
    PosterRawFeedbackEvent,
)


REQUIRED_ARTIFACTS = [
    "poster_brief.json",
    "poster_plan.json",
    "poster_prompt_pack.json",
    "poster_model_invocations.json",
    "poster_candidates_manifest.json",
    "poster_feedback.jsonl",
    "poster_feedback_signal_log.json",
    "poster_memory_candidates.jsonl",
    "poster_memory_candidates.json",
    "poster_memory_decisions.json",
    "poster_memory_review.jsonl",
    "poster_preference_profile.json",
    "project_prefix.md",
    "context_bundle.json",
    "context_assembly_trace.json",
    "next_round_prompt.json",
    "round_2/poster_prompt_pack.json",
    "round_2/poster_model_invocations.json",
    "round_2/poster_candidates_manifest.json",
    "poster_round_comparison.json",
    "poster_two_round_report.md",
    "poster_report.md",
    "poster_preview.html",
    "trace.json",
    "manifest.json",
    "run_manifest.json",
]

SCHEMA_MODELS = {
    "poster_brief.json": PosterBrief,
    "poster_plan.json": PosterPlan,
    "poster_prompt_pack.json": PosterPromptPack,
    "poster_model_invocations.json": PosterModelInvocations,
    "poster_candidates_manifest.json": PosterCandidatesManifest,
    "poster_feedback_signal_log.json": PosterFeedbackSignalLog,
    "poster_memory_candidates.json": PosterMemoryCandidates,
    "poster_memory_decisions.json": PosterMemoryDecisions,
    "poster_preference_profile.json": PosterPreferenceProfile,
    "context_bundle.json": ContextBundle,
    "context_assembly_trace.json": ContextAssemblyTrace,
    "next_round_prompt.json": NextRoundPrompt,
    "round_2/poster_prompt_pack.json": PosterPromptPack,
    "round_2/poster_model_invocations.json": PosterModelInvocations,
    "round_2/poster_candidates_manifest.json": PosterCandidatesManifest,
}

JSONL_SCHEMA_MODELS = {
    "poster_feedback.jsonl": PosterRawFeedbackEvent,
    "poster_memory_candidates.jsonl": PosterMemoryCandidate,
    "poster_memory_review.jsonl": PosterMemoryReviewEvent,
}


def add_json_parse_checks(run_dir: Path, checks: list[dict[str, Any]]) -> None:
    for artifact in REQUIRED_ARTIFACTS:
        if not artifact.endswith(".json") and not artifact.endswith(".jsonl"):
            continue
        path = run_dir / artifact
        if not path.is_file():
            continue
        if artifact.endswith(".jsonl"):
            _add_check(
                checks,
                f"posterflow_{check_name(artifact)}_jsonl_valid",
                "pass" if read_jsonl(path) is not None else "fail",
            )
            continue
        _add_check(
            checks,
            f"posterflow_{check_name(artifact)}_json_valid",
            "pass" if read_json_object(path) is not None else "fail",
        )


def add_schema_checks(artifacts: dict[str, dict[str, Any] | None], checks: list[dict[str, Any]]) -> None:
    for name, payload in artifacts.items():
        if payload is None or name in {"manifest.json", "run_manifest.json", "trace.json"}:
            continue
        model = SCHEMA_MODELS.get(name)
        if model is None:
            continue
        try:
            model.model_validate(payload)
        except ValidationError as exc:
            _add_check(checks, f"posterflow_{check_name(name)}_schema_valid", "fail", {"error_count": len(exc.errors())})
            continue
        _add_check(checks, f"posterflow_{check_name(name)}_schema_valid", "pass")
        _add_check(
            checks,
            f"posterflow_{check_name(name)}_schema_version",
            "pass" if payload.get("schema_version") == "0.1.0" else "fail",
            {"schema_version": payload.get("schema_version")},
        )


def add_jsonl_schema_checks(
    jsonl_artifacts: dict[str, list[dict[str, Any]] | None],
    checks: list[dict[str, Any]],
) -> None:
    for name, rows in jsonl_artifacts.items():
        model = JSONL_SCHEMA_MODELS.get(name)
        if rows is None or model is None:
            continue
        failed = 0
        for row in rows:
            try:
                model.model_validate(row)
            except ValidationError:
                failed += 1
        _add_check(
            checks,
            f"posterflow_{check_name(name)}_schema_valid",
            "pass" if failed == 0 and bool(rows) else "fail",
            {"row_count": len(rows), "failed_rows": failed},
        )


def read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def read_jsonl(path: Path) -> list[dict[str, Any]] | None:
    if not path.is_file():
        return None
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                return None
            rows.append(payload)
    except json.JSONDecodeError:
        return None
    return rows


def check_name(filename: str) -> str:
    return (
        filename.replace("\\", "_")
        .replace("/", "_")
        .replace(".jsonl", "")
        .replace(".json", "")
        .replace(".md", "")
        .replace(".html", "")
    )


def _add_check(checks: list[dict[str, Any]], name: str, status: str, details: dict[str, Any] | None = None) -> None:
    check: dict[str, Any] = {"name": name, "status": status}
    if details is not None:
        check["details"] = details
    checks.append(check)
