"""Strict, provider-free structural evaluation for supplied evidence.

Creative bodies are deliberately opaque here.  This module reads only manifests,
provenance, issue ledgers, and deterministic assembly metadata.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

MODEL_SURFACE = "server_codex"
STAGES = ("script", "understanding_assets", "story_plan", "deterministic_assembly_validation")
ZERO_FIELDS = ("provider_dispatch_count", "remote_dispatch_count", "cost_usd")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def staged_generation_contract(case_id: str, stage_metadata: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Create metadata-only stage manifests; this never calls a provider/model."""
    if tuple(stage_metadata) != STAGES:
        raise ValueError("stages must be script -> understanding_assets -> story_plan -> deterministic_assembly_validation")
    manifests: list[dict[str, Any]] = []
    prior: str | None = None
    for stage in STAGES:
        metadata = dict(stage_metadata[stage])
        manifest = {"artifact_type": "afs_server_codex_generation_manifest", "case_id": case_id,
                    "stage": stage, "generation_run_id": metadata["generation_run_id"],
                    "output_digest": metadata["output_digest"], "depends_on_manifest_digest": prior,
                    "provider_dispatch_count": 0, "remote_dispatch_count": 0, "cost_usd": 0,
                    "writes_canonical_truth": False, "writes_memory": False,
                    "metadata_only": True}
        if stage == "deterministic_assembly_validation":
            manifest["assembly_validation"] = metadata.get("assembly_validation", {})
        manifests.append(manifest)
        prior = sha256_json(manifest)
    return manifests


def evaluation_target_digest(manifests: list[Mapping[str, Any]]) -> str:
    """Bind reports to manifest metadata, not supplied creative output bodies."""
    return sha256_json([{"stage": item.get("stage"), "output_digest": item.get("output_digest"),
                         "generation_run_id": item.get("generation_run_id")} for item in manifests])


def materialize_evidence(artifact_root: Path | str, corpus: Mapping[str, Any]) -> str:
    """Write a supplied metadata corpus under /tmp for deterministic evaluation."""
    base = Path(artifact_root).resolve()
    if base != Path("/tmp") and not str(base).startswith("/tmp/"):
        raise ValueError("artifact root must be under /tmp")
    root = base / "m3_server_codex_evidence"
    root.mkdir(parents=True, exist_ok=False)
    _write(root / "run_summary.json", {"model_surface": corpus.get("model_surface", MODEL_SURFACE),
           "provider_dispatch_count": corpus.get("provider_dispatch_count", 0), "remote_dispatch_count": corpus.get("remote_dispatch_count", 0),
           "cost_usd": corpus.get("cost_usd", 0), "writes_canonical_truth": corpus.get("writes_canonical_truth", False),
           "writes_memory": corpus.get("writes_memory", False)})
    for case in corpus.get("cases", []):
        case_root = root / "cases" / str(case["case_id"]); case_root.mkdir(parents=True)
        _write(case_root / "context_provenance.json", dict(case.get("context_provenance", {})))
        _write(case_root / "issue_ledger.json", list(case.get("issue_ledger", [])))
        _write(case_root / "replan.json", dict(case.get("replan", {})))
        for manifest in case.get("manifests", []): _write(case_root / "generation_manifests" / f"{manifest['stage']}.json", manifest)
        for report in case.get("evaluation_reports", []): _write(case_root / "evaluation_reports" / f"{report.get('role', 'unknown')}.json", report)
    return str(root)


def evaluate_artifact_root(artifact_root: Path | str, *, expected_case_count: int | None = None,
                           expected_roles: set[str] | None = None) -> dict[str, Any]:
    root = Path(artifact_root).resolve(); findings: list[dict[str, str]] = []
    summary = _read(root / "run_summary.json", findings, "run_summary")
    _boundary(summary, findings, "run_summary")
    if summary.get("model_surface") != MODEL_SURFACE: _finding(findings, "P0", "run_summary", "wrong model label")
    case_dirs = sorted(path for path in (root / "cases").glob("*") if path.is_dir())
    if expected_case_count is not None and len(case_dirs) != expected_case_count:
        _finding(findings, "P0", "corpus", "case count mismatch")
    for case_dir in case_dirs: _evaluate_case(case_dir, findings, expected_roles)
    return _report(root, findings)


def evaluate_ledger(ledger: Mapping[str, Any], *, expected_roles: set[str] | None = None) -> dict[str, Any]:
    """Evaluate a controlled attempt ledger without rewriting any attempt artifact."""
    findings: list[dict[str, str]] = []
    _boundary(ledger, findings, "ledger")
    for case in ledger.get("cases", []):
        scope = str(case.get("case_id", "unknown"))
        for item in case.get("recorded_defects", []):
            _finding(findings, item.get("severity", "P1"), scope, item["issue"])
        _ledger_structural_checks(case, findings, scope)
        _review_role_coverage(case, expected_roles, findings, scope)
    return _report(None, findings)


def _evaluate_case(case_dir: Path, findings: list[dict[str, str]], expected_roles: set[str] | None) -> None:
    scope = case_dir.name
    context = _read(case_dir / "context_provenance.json", findings, scope)
    _boundary(context, findings, scope)
    if not context.get("knowledge_provenance_refs"): _finding(findings, "P0", scope, "unauditable knowledge provenance")
    issues = _read_list(case_dir / "issue_ledger.json", findings, scope)
    if not issues: _finding(findings, "P0", scope, "empty issue ledger")
    replan = _read(case_dir / "replan.json", findings, scope)
    manifests = [_read(path, findings, scope) for path in (case_dir / "generation_manifests").glob("*.json")]
    by_stage = {item.get("stage"): item for item in manifests}
    if set(by_stage) != set(STAGES) or len(manifests) != len(STAGES): _finding(findings, "P0", scope, "staged-generation contract missing or duplicated")
    ordered = [by_stage.get(stage, {}) for stage in STAGES]
    for index, manifest in enumerate(ordered):
        _boundary(manifest, findings, scope)
        if manifest.get("writes_canonical_truth") is not False or manifest.get("writes_memory") is not False:
            _finding(findings, "P0", scope, "canonical or memory write")
        if not manifest.get("generation_run_id") or not manifest.get("output_digest"):
            _finding(findings, "P0", scope, "missing generation provenance")
        if index and manifest.get("depends_on_manifest_digest") != sha256_json(ordered[index - 1]):
            _finding(findings, "P0", scope, "stage dependency binding mismatch")
    target = evaluation_target_digest(ordered)
    reports = [_read(path, findings, scope) for path in (case_dir / "evaluation_reports").glob("*.json")]
    if not reports: _finding(findings, "P0", scope, "no evaluation reports")
    roles = {item.get("role") for item in reports}
    if expected_roles is not None and roles != expected_roles: _finding(findings, "P0", scope, "evaluation roles do not match rubric")
    fingerprints: set[str] = set()
    evaluator_run_ids: set[str] = set()
    generation_ids = {item.get("generation_run_id") for item in manifests}
    for report in reports:
        _boundary(report, findings, scope)
        required = ("evaluator_run_id", "target_digest", "evidence_refs", "criterion_findings", "score_rationale")
        if any(not report.get(key) for key in required): _finding(findings, "P0", scope, "incomplete evaluator evidence")
        if report.get("evaluator_run_id") in generation_ids: _finding(findings, "P0", scope, "missing evaluator independence provenance")
        if report.get("evaluator_run_id") in evaluator_run_ids: _finding(findings, "P0", scope, "evaluator_run_id reused across roles")
        evaluator_run_ids.add(str(report.get("evaluator_run_id")))
        if report.get("target_digest") != target: _finding(findings, "P0", scope, "target digest mismatch")
        fingerprint = sha256_json({key: report.get(key) for key in ("score", "criterion_findings", "score_rationale")})
        if fingerprint in fingerprints: _finding(findings, "P0", scope, "duplicated score+finding boilerplate across roles")
        fingerprints.add(fingerprint)
    _assembly_checks(by_stage.get("deterministic_assembly_validation", {}).get("assembly_validation", {}), findings, scope)
    _ledger_structural_checks({"issue_ledger": issues, "replan": replan}, findings, scope)


def _ledger_structural_checks(case: Mapping[str, Any], findings: list[dict[str, str]], scope: str) -> None:
    issues = case.get("issue_ledger", case.get("issues", []))
    if any(str(item.get("status", "")).upper() == "PASS" for item in issues if isinstance(item, Mapping)):
        _finding(findings, "P0", scope, "self-PASS issue seed")
    replan = case.get("replan", {})
    if replan.get("scope") == "affected_only" and (not replan.get("dependency_refs") or not replan.get("reasons")):
        _finding(findings, "P0", scope, "affected-only replan lacks dependency refs/reasons")


def _review_role_coverage(case: Mapping[str, Any], expected_roles: set[str] | None,
                          findings: list[dict[str, str]], scope: str) -> None:
    """A controlled failure ledger still needs every required expert view."""
    if expected_roles is None:
        return
    reviews = [item for item in case.get("professional_reviews", []) if isinstance(item, Mapping)]
    roles = {item.get("role") for item in reviews}
    if roles != expected_roles:
        _finding(findings, "P0", scope, "professional review role coverage missing or duplicated")
        return
    for review in reviews:
        required = ("role", "review_run_id", "status", "evidence_refs", "assessment")
        if any(not review.get(key) for key in required):
            _finding(findings, "P0", scope, "incomplete professional review ledger entry")
        if scope == "B" and review.get("status") != "not_assessable_generation_failure":
            _finding(findings, "P0", scope, "missing explicit generation-failure assessment for review role")


def _assembly_checks(value: Mapping[str, Any], findings: list[dict[str, str]], scope: str) -> None:
    shots = value.get("shots", [])
    durations = [shot.get("duration_seconds") for shot in shots if isinstance(shot, Mapping)]
    if len(durations) >= 4 and len(set(durations)) == 1: _finding(findings, "P1", scope, "equal durations across four or more shots")
    if value.get("shot_count_range") and not value.get("shot_count_range_source_constraint"):
        _finding(findings, "P0", scope, "fixed shot-count range lacks source constraint")
    referenced = set(value.get("referenced_asset_ids", [])) | set(value.get("referenced_ref_ids", []))
    resolved = set(value.get("resolved_asset_ids", [])) | set(value.get("resolved_ref_ids", []))
    if referenced - resolved: _finding(findings, "P0", scope, "unresolved asset/ref IDs")
    manifest_shots, covered = set(value.get("manifest_shot_ids", [])), set(value.get("covered_shot_ids", []))
    if manifest_shots - covered: _finding(findings, "P0", scope, "manifest shot coverage gaps")
    if durations and value.get("declared_total_duration_seconds") != sum(durations): _finding(findings, "P0", scope, "duration sum mismatch")
    for field in value.get("chinese_professional_fields", []):
        if not any("\u4e00" <= char <= "\u9fff" for char in str(field)): _finding(findings, "P1", scope, "missing Chinese in Chinese professional fields")


def _boundary(value: Mapping[str, Any], findings: list[dict[str, str]], scope: str) -> None:
    if any(value.get(key, 0) != 0 for key in ZERO_FIELDS): _finding(findings, "P0", scope, "provider dispatch or cost is non-zero")
    if value.get("writes_canonical_truth") is True or value.get("writes_memory") is True: _finding(findings, "P0", scope, "canonical or memory write")


def _read(path: Path, findings: list[dict[str, str]], scope: str) -> dict[str, Any]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): _finding(findings, "P0", scope, "missing or invalid JSON"); return {}
    if not isinstance(value, dict): _finding(findings, "P0", scope, "expected JSON object"); return {}
    return value


def _read_list(path: Path, findings: list[dict[str, str]], scope: str) -> list[dict[str, Any]]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): _finding(findings, "P0", scope, "missing or invalid issue ledger"); return []
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finding(findings: list[dict[str, str]], severity: str, scope: str, issue: str) -> None:
    findings.append({"severity": severity, "scope": scope, "issue": issue})


def _report(root: Path | None, findings: list[dict[str, str]]) -> dict[str, Any]:
    p0 = sum(item["severity"] == "P0" for item in findings); p1 = sum(item["severity"] == "P1" for item in findings)
    return {"artifact_type": "afs_independent_evaluator_report", "verdict": "PASS" if not findings else "FAIL", "P0": p0, "P1": p1,
            "findings": findings, "artifact_root": str(root) if root else None, "model_surface": MODEL_SURFACE,
            "provider_dispatch_count": 0, "remote_dispatch_count": 0, "cost_usd": 0}
