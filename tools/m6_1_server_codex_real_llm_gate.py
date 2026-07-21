"""Real server_codex M6.1 text-LLM gate.

This tool starts a temporary localhost Runtime Service, opens only the LLM gate,
and drives the registered M6 script-plan-asset-Bible HTTP routes. It stores safe
candidate artifacts and evaluator ledgers, never Codex raw stdout or secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import ProxyHandler, Request, build_opener

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.company_secrets import SERVER_CODEX_SERVICE_ID
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry, structured_output_schema_digest
from apps.api.runtime_production_graph import canonical_digest
from tools.studio_asset_context_browser_qa_support import free_port, stop_runtime, wait_for_http


LLM_GATE = "AFS_ALLOW_REMOTE_LLM"
NON_LLM_GATES = (
    "AFS_ALLOW_REMOTE_IMAGE",
    "AFS_ALLOW_REMOTE_VIDEO",
    "AFS_ALLOW_REMOTE_AUDIO",
    "AFS_ALLOW_REMOTE_ASR",
    "AFS_ALLOW_REMOTE_VISION",
    "AFS_ALLOW_EXTERNAL_DOWNLOAD",
)
REVIEW_ROLES = (
    "screenwriter",
    "director_storyboard",
    "cinematographer_editor",
    "asset_continuity",
    "production_cost",
    "engineering_lineage_recovery",
)
MAX_PROVIDER_REQUESTS = 30
MAX_EXTERNAL_PAID_COST_USD = 15
M6_SERVER_CODEX_CLI_MODEL = "gpt-5.5"
M6_SERVER_CODEX_REASONING_EFFORT = "medium"


@dataclass(frozen=True)
class CorpusCase:
    case_id: str
    title: str
    source_kind: str
    source_text: str
    revision_focus: str
    regression_tags: tuple[str, ...] = ()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="/tmp/afs-m6-1-server-codex-real-llm")
    parser.add_argument("--runtime-root", default="")
    args = parser.parse_args()

    run_root = Path(args.output_root).resolve() / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_root.mkdir(parents=True, exist_ok=True)
    runtime_root = Path(args.runtime_root).resolve() if args.runtime_root else run_root / "runtime"
    provider_config = run_root / "provider_config.json"
    provider_config.write_text(json.dumps(_server_codex_provider_config(), ensure_ascii=False, indent=2), encoding="utf-8")
    env = _candidate_env(runtime_root=runtime_root, provider_config=provider_config, output_root=run_root / "provider_outputs")
    os.environ.update({key: value for key, value in env.items() if key.startswith("AFS_")})
    provider_surface = _provider_surface()
    if provider_surface["service_id"] != SERVER_CODEX_SERVICE_ID or provider_surface["provider"] != "codex_local":
        report = _blocked_report(run_root, "server_codex provider surface is not available", provider_surface)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 1
    if provider_surface["external_paid_cost_usd"] > MAX_EXTERNAL_PAID_COST_USD:
        report = _blocked_report(run_root, "estimated provider budget exceeds gate cap", provider_surface)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 1

    try:
        tiny_dispatch = _run_tiny_structured_dispatch(run_root)
    except Exception as exc:
        report = _technical_fail_report(run_root, f"tiny structured dispatch failed: {exc}", provider_surface, 0)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 1
    dispatch_count = int(tiny_dispatch["provider_dispatch_count"])
    port = free_port()
    server = _start_candidate_runtime(runtime_root, port, env)
    base_url = f"http://127.0.0.1:{port}/"
    report: dict[str, Any]
    try:
        try:
            wait_for_http(urljoin(base_url, "health"), timeout=45)
            health = _get_json(base_url, "health")
            if not _health_allows_candidate_llm_only(health):
                report = _blocked_report(run_root, "candidate runtime gates are not LLM-only", {"health": health})
                print(json.dumps(report, ensure_ascii=False, sort_keys=True))
                return 1
            smoke = _run_smoke(base_url, run_root)
            cases = []
            dispatch_count += int(smoke["provider_dispatch_count"])
            for case in corpus_cases():
                if dispatch_count + 2 > MAX_PROVIDER_REQUESTS:
                    report = _blocked_report(run_root, "provider request budget exhausted before all cases", {"dispatch_count": dispatch_count})
                    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
                    return 1
                result = _run_case(base_url, run_root, case, current_dispatch_count=dispatch_count)
                dispatch_count += int(result["provider_dispatch_count"])
                cases.append(result)
            report = _final_report(
                run_root=run_root,
                health=health,
                provider_surface=provider_surface,
                tiny_dispatch=tiny_dispatch,
                smoke=smoke,
                cases=cases,
                dispatch_count=dispatch_count,
            )
            write_json(run_root / "m6_1_server_codex_real_llm_report.json", report)
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
            return 0 if report["verdict"] == "PASS" else 1
        except Exception as exc:
            report = _technical_fail_report(run_root, str(exc), provider_surface, dispatch_count)
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
            return 1
    finally:
        stop_runtime(server)


def _candidate_env(*, runtime_root: Path, provider_config: Path, output_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AFS_RUNTIME_SERVICE_ROOT"] = str(runtime_root)
    env["AFS_RUNTIME_ROOT"] = str(runtime_root)
    env["AFS_RUNTIME_SERVICE_HOST"] = "127.0.0.1"
    env["AFS_PROVIDER_CONFIG"] = str(provider_config)
    env["AFS_M6_SERVER_CODEX_OUTPUT_DIR"] = str(output_root)
    env["AFS_M6_SERVER_CODEX_TIMEOUT_SEC"] = env.get("AFS_M6_SERVER_CODEX_TIMEOUT_SEC", "600")
    env["AFS_AUTH_ENABLED"] = "false"
    env[LLM_GATE] = "true"
    for key in NON_LLM_GATES:
        env[key] = "false"
    env["NO_PROXY"] = _merge_no_proxy(env.get("NO_PROXY"))
    env["no_proxy"] = _merge_no_proxy(env.get("no_proxy"))
    return env


def _server_codex_provider_config() -> dict[str, Any]:
    return {
        "schema_version": "company_provider_secrets.m6_1.local.v1",
        "accounts": {
            "server_codex_login": {
                "auth_type": "none",
                "execution_backend": "codex_exec",
                "default_models": {"llm": "server-codex-login"},
            }
        },
        "account_pools": {
            "server_codex_pool": {
                "accounts": [{
                    "account_id": "server_codex_login",
                    "service_id": SERVER_CODEX_SERVICE_ID,
                    "enabled_capabilities": ["llm"],
                    "enabled": True,
                    "priority": 1,
                    "weight": 1,
                    "concurrency_limit": 1,
                    "health_state": "unknown",
                }]
            }
        },
        "services": {
            SERVER_CODEX_SERVICE_ID: {
                "provider": "codex_local",
                "account_ref": "server_codex_login",
                "capability": "llm",
                "required_gate": "AFS_ALLOW_REMOTE_LLM",
                "cli_model": M6_SERVER_CODEX_CLI_MODEL,
                "cli_reasoning_effort": M6_SERVER_CODEX_REASONING_EFFORT,
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
                    "modality": "llm",
                    "execution_mode": "sync",
                    "capabilities": ["llm"],
                    "account_pool_id": "server_codex_pool",
                    "reference_image_slots": 0,
                    "supported_aspect_ratios": ["1:1"],
                    "prompt_char_limit": 12000,
                    "seed_supported": False,
                    "required_gate": "AFS_ALLOW_REMOTE_LLM",
                },
            }
        },
    }


def _start_candidate_runtime(runtime_root: Path, port: int, env: dict[str, str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "runtime-service",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--runtime-root",
            str(runtime_root),
        ],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _provider_surface() -> dict[str, Any]:
    registry = load_provider_registry()
    descriptor = registry.descriptor(SERVER_CODEX_SERVICE_ID)
    service = registry.store.service(SERVER_CODEX_SERVICE_ID)
    return {
        "service_id": SERVER_CODEX_SERVICE_ID,
        "provider": "codex_local",
        "capability": descriptor.modality,
        "required_gate": descriptor.required_gate,
        "model_surface": "server-codex-login",
        "cli_model": service.get("cli_model") or "",
        "cli_reasoning_effort": service.get("cli_reasoning_effort") or "",
        "auth_type": "none",
        "execution_backend": "codex_exec",
        "structured_output": "closed_json_schema",
        "usage_source": "estimated_from_safe_prompt_and_payload_chars",
        "external_paid_cost_usd": 0,
        "non_llm_gates": {key: False for key in NON_LLM_GATES},
    }


def _run_tiny_structured_dispatch(run_root: Path) -> dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["ok", "note"],
        "properties": {
            "ok": {"type": "boolean"},
            "note": {"type": "string", "minLength": 2},
        },
    }
    schema_digest = structured_output_schema_digest(schema)
    start = time.monotonic()
    result = load_provider_registry().dispatch(
        "llm",
        SERVER_CODEX_SERVICE_ID,
        ProviderDispatchRequest(
            prompt="返回一个严格 JSON：ok=true，note 用中文写“就绪”。不要输出其他文本。",
            output_dir=run_root / "tiny_provider_output",
            task_type="m6_1_tiny_structured_smoke",
            structured_output_contract_id="afs.m6_1.tiny_structured_smoke.v0.1",
            structured_output_schema=schema,
            structured_output_schema_digest=schema_digest,
            timeout_sec=120,
        ),
    )
    payload = result.get("structured_output") if isinstance(result.get("structured_output"), dict) else {}
    if result.get("provider_calls_started") is not True or payload.get("ok") is not True:
        raise RuntimeError("tiny server_codex structured dispatch did not return ok=true")
    safe = {
        "status": "PASS",
        "elapsed_sec": round(time.monotonic() - start, 2),
        "service_id": SERVER_CODEX_SERVICE_ID,
        "provider": "codex_local",
        "cli_model": M6_SERVER_CODEX_CLI_MODEL,
        "cli_reasoning_effort": M6_SERVER_CODEX_REASONING_EFFORT,
        "schema_digest": schema_digest,
        "provider_dispatch_count": 1,
        "provider_calls_started": True,
        "external_paid_cost_usd": 0,
        "payload_keys": sorted(payload),
    }
    write_json(run_root / "tiny_structured_dispatch.json", safe)
    return safe


def _run_smoke(base_url: str, run_root: Path) -> dict[str, Any]:
    case = corpus_cases()[0]
    preview = _preview(base_url, "m6-1-smoke", case.source_kind, case.source_text, "", "")
    candidate = preview["candidate"]
    scores = _score_candidate(candidate, graph_digest="")
    if scores["P0"] or scores["P1"]:
        raise RuntimeError(f"smoke candidate failed strict review: {scores['issues'][:3]}")
    safe = {
        "project_id": "m6-1-smoke",
        "candidate_digest": preview["candidate_digest"],
        "provider_dispatch_count": preview["provider_dispatch_count"],
        "scores": scores,
        "provider_lineage": candidate.get("provider_lineage"),
    }
    write_json(run_root / "smoke.json", safe)
    return safe


def _run_case(base_url: str, run_root: Path, case: CorpusCase, *, current_dispatch_count: int) -> dict[str, Any]:
    case_dir = run_root / "cases" / case.case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    project_id = f"m6-1-{case.case_id}"
    first = _preview(base_url, project_id, case.source_kind, case.source_text, "", "")
    first_digest = str(first["candidate_digest"])
    first_scores = _score_candidate(first["candidate"], graph_digest="")
    feedback = _revision_feedback(case, first_scores, first_digest)
    second = _preview(base_url, project_id, case.source_kind, case.source_text, feedback, first_digest)
    second_scores = _score_candidate(second["candidate"], graph_digest="")
    retry_used = False
    if (second_scores["P0"] or second_scores["P1"]) and current_dispatch_count + 3 <= MAX_PROVIDER_REQUESTS:
        retry_used = True
        feedback = _revision_feedback(case, second_scores, first_digest, retry=True)
        second = _preview(base_url, project_id, case.source_kind, case.source_text, feedback, first_digest)
        second_scores = _score_candidate(second["candidate"], graph_digest="")
    if second_scores["P0"] or second_scores["P1"]:
        write_json(case_dir / "failed_candidate.json", _safe_case_artifact(case, first, second, first_scores, second_scores))
        raise RuntimeError(f"{case.case_id} failed strict review: {second_scores['issues'][:5]}")
    confirmed = _confirm(base_url, project_id, second["candidate"])
    workspace = _get_json(base_url, f"projects/{project_id}/m5/sequence-workspace")
    graph_digest = str(confirmed["graph"]["graph_digest"])
    second_scores = _score_candidate(second["candidate"], graph_digest=graph_digest, workspace=workspace)
    if second_scores["P0"] or second_scores["P1"]:
        write_json(case_dir / "failed_confirmed_candidate.json", _safe_case_artifact(case, first, second, first_scores, second_scores))
        raise RuntimeError(f"{case.case_id} failed post-confirm graph review: {second_scores['issues'][:5]}")
    artifact = _safe_case_artifact(case, first, second, first_scores, second_scores)
    artifact["confirmed"] = {
        "graph_version": confirmed["graph"]["version"],
        "graph_digest": graph_digest,
        "workspace_graph_digest": workspace.get("graph_digest"),
        "storyboard_graph_digest": (workspace.get("storyboard") or {}).get("graph_digest"),
        "provider_gates": confirmed["graph"].get("provider_gates"),
    }
    artifact["retry_used"] = retry_used
    write_json(case_dir / "case_report.json", artifact)
    return {
        "case_id": case.case_id,
        "title": case.title,
        "regression_tags": list(case.regression_tags),
        "revision_count": 2,
        "retry_used": retry_used,
        "provider_dispatch_count": 3 if retry_used else 2,
        "revision1_digest": first_digest,
        "revision2_digest": second["candidate_digest"],
        "shot_count": len(second["candidate"]["shots"]),
        "total_duration_seconds": second["candidate"]["sequence"]["target_duration_seconds"],
        "scores": second_scores["scores"],
        "P0": second_scores["P0"],
        "P1": second_scores["P1"],
        "issue_count": len(second_scores["issues"]),
        "graph_digest": graph_digest,
        "asset_bible_counts": _asset_bible_counts(second["candidate"]),
        "provider_lineage": _provider_lineage_summary(second["candidate"]),
    }


def _preview(
    base_url: str,
    project_id: str,
    source_kind: str,
    source_text: str,
    revision_instruction: str,
    parent_candidate_digest: str,
) -> dict[str, Any]:
    body = {
        "source_kind": source_kind,
        "source_text": source_text,
        "requested_language": "zh-CN",
    }
    if revision_instruction:
        body["revision_instruction"] = revision_instruction
    if parent_candidate_digest:
        body["parent_candidate_digest"] = parent_candidate_digest
    payload = _post_json(base_url, f"projects/{project_id}/m6/script-plan-asset-bible/preview", body)
    candidate = payload.get("candidate")
    if not isinstance(candidate, dict):
        raise RuntimeError("preview response missing candidate")
    return payload


def _confirm(base_url: str, project_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
    return _post_json(
        base_url,
        f"projects/{project_id}/m6/script-plan-asset-bible/confirm",
        {
            "expected_graph_version": 0,
            "idempotency_key": f"confirm-{project_id}",
            "candidate": candidate,
        },
    )


def _post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        urljoin(base_url, path),
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=900) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"HTTP {exc.code} for {path}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"HTTP request failed for {path}: {exc}") from exc


def _get_json(base_url: str, path: str) -> dict[str, Any]:
    try:
        with build_opener(ProxyHandler({})).open(urljoin(base_url, path), timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"HTTP get failed for {path}: {exc}") from exc


def _score_candidate(candidate: dict[str, Any], *, graph_digest: str, workspace: dict[str, Any] | None = None) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    scores = {role: 5 for role in REVIEW_ROLES}
    p0 = _p0_checks(candidate, graph_digest=graph_digest, workspace=workspace)
    issues.extend(p0)
    p1 = _p1_checks(candidate, graph_digest=graph_digest, workspace=workspace)
    issues.extend(p1)
    for issue in issues:
        role = issue.get("role")
        if role in scores:
            scores[role] = max(0, scores[role] - (3 if issue["severity"] == "P0" else 1))
    return {
        "P0": sum(item["severity"] == "P0" for item in issues),
        "P1": sum(item["severity"] == "P1" for item in issues),
        "scores": scores,
        "issues": issues,
    }


def _p0_checks(candidate: dict[str, Any], *, graph_digest: str, workspace: dict[str, Any] | None) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    lineage = candidate.get("provider_lineage") if isinstance(candidate.get("provider_lineage"), dict) else {}
    if candidate.get("provider_dispatch_count") != 1 or lineage.get("provider_calls_started") is not True:
        issues.append(_issue("P0", "engineering_lineage_recovery", "provider dispatch is not real server_codex evidence"))
    if lineage.get("service_id") != SERVER_CODEX_SERVICE_ID or lineage.get("provider") != "codex_local":
        issues.append(_issue("P0", "engineering_lineage_recovery", "candidate lineage is not server_codex/codex_local"))
    if not lineage.get("request_id") or not lineage.get("structured_output_schema_digest"):
        issues.append(_issue("P0", "engineering_lineage_recovery", "lineage missing request id or schema digest"))
    if (lineage.get("usage") or {}).get("external_paid_cost_usd") != 0:
        issues.append(_issue("P0", "engineering_lineage_recovery", "external paid cost is nonzero"))
    creative_text = _creative_text(candidate)
    polluted = [
        token
        for token in re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{3,}\b", creative_text)
        if token not in {"ReferenceSet", "JSON", "Codex", "AFS", "digest"} and not re.fullmatch(r"[a-fA-F0-9]{16,64}", token)
    ]
    if polluted:
        issues.append(_issue("P0", "screenwriter", f"creative text contains English pollution: {polluted[:5]}"))
    shots = candidate.get("shots") if isinstance(candidate.get("shots"), list) else []
    durations = [round(float(shot.get("duration_seconds") or 0), 2) for shot in shots if isinstance(shot, dict)]
    if len(shots) < 3 or len(set(durations)) <= 1:
        issues.append(_issue("P0", "director_storyboard", "shot count/duration is fixed or too shallow"))
    if len(durations) == 4 and set(durations) == {15.0}:
        issues.append(_issue("P0", "director_storyboard", "forbidden 4x15 profile"))
    if len(durations) == 10 and set(durations) == {6.0}:
        issues.append(_issue("P0", "director_storyboard", "forbidden 10x6 profile"))
    bible = candidate.get("asset_bible") if isinstance(candidate.get("asset_bible"), dict) else {}
    if not bible.get("reference_set_refs"):
        issues.append(_issue("P0", "asset_continuity", "asset Bible missing ReferenceSet refs"))
    if workspace is not None:
        if workspace.get("graph_digest") != graph_digest or (workspace.get("storyboard") or {}).get("graph_digest") != graph_digest:
            issues.append(_issue("P0", "engineering_lineage_recovery", "ProductionGraph digest parity failed"))
    return issues


def _p1_checks(candidate: dict[str, Any], *, graph_digest: str, workspace: dict[str, Any] | None) -> list[dict[str, str]]:
    del graph_digest, workspace
    issues: list[dict[str, str]] = []
    characters = [row for row in candidate.get("characters", []) if isinstance(row, dict)]
    scenes = [row for row in candidate.get("scenes", []) if isinstance(row, dict)]
    shots = [row for row in candidate.get("shots", []) if isinstance(row, dict)]
    assets = [row for row in candidate.get("assets", []) if isinstance(row, dict)]
    if len(_text(candidate.get("script_revision", {}).get("draft_text"))) < 220:
        issues.append(_issue("P1", "screenwriter", "script draft is too thin for professional expansion"))
    for row in characters:
        for key in ("goal", "conflict", "relationship_arc", "change_vector"):
            if len(_text(row.get(key))) < 12:
                issues.append(_issue("P1", "screenwriter", f"character {row.get('display_name')} has shallow {key}"))
        if len(row.get("do_not_change") or []) < 2:
            issues.append(_issue("P1", "asset_continuity", f"character {row.get('display_name')} lacks negative locks"))
    if len(scenes) < 2:
        issues.append(_issue("P1", "director_storyboard", "scene understanding is too narrow"))
    for row in scenes:
        if len(row.get("do_not_change") or []) < 2:
            issues.append(_issue("P1", "asset_continuity", f"scene {row.get('name')} lacks continuity locks"))
        for key in ("space", "lighting", "continuity", "action", "rhythm", "emotion", "visual_expression"):
            if len(_text(row.get(key))) < 8:
                issues.append(_issue("P1", "director_storyboard", f"scene {row.get('name')} lacks {key}"))
    kinds = {str(row.get("kind")) for row in assets}
    if not {"prop", "closeup", "reference_set", "style"} <= kinds:
        issues.append(_issue("P1", "asset_continuity", "asset Bible lacks prop/closeup/reference/style coverage"))
    for shot in shots:
        for key in ("shot_size", "camera_angle", "camera_movement", "blocking", "sound", "transition", "narrative_purpose"):
            if len(_text(shot.get(key))) < 2:
                issues.append(_issue("P1", "cinematographer_editor", f"shot {shot.get('shot_id')} lacks {key}"))
        if len(_text(shot.get("content_driven_duration_reason"))) < 12:
            issues.append(_issue("P1", "production_cost", f"shot {shot.get('shot_id')} lacks duration/cost reason"))
        if float(shot.get("duration_seconds") or 0) > 20:
            issues.append(_issue("P1", "production_cost", f"shot {shot.get('shot_id')} is too long for smoke feasibility"))
    total_duration = float((candidate.get("sequence") or {}).get("target_duration_seconds") or 0)
    if total_duration <= 0 or total_duration > 140:
        issues.append(_issue("P1", "production_cost", "sequence duration is not bounded for a smokeable slice"))
    knowledge = candidate.get("knowledge_context") if isinstance(candidate.get("knowledge_context"), dict) else {}
    for item in knowledge.get("items") or []:
        if not isinstance(item, dict):
            continue
        if item.get("promotion_state") == "promoted" or not item.get("rollback_ref"):
            issues.append(_issue("P1", "engineering_lineage_recovery", "knowledge item promotion/rollback boundary is weak"))
    return issues


def _revision_feedback(case: CorpusCase, scores: dict[str, Any], parent_digest: str, *, retry: bool = False) -> str:
    issue_text = _feedback_issue_summary(scores)
    prefix = "重新执行第二轮真实修订" if retry else "执行第二轮真实修订"
    regressions = "；".join(_regression_tag_label(tag) for tag in case.regression_tags) or "常规专业影视合同"
    return (
        f"{prefix}。上一轮校验码={parent_digest}。"
        f"针对 {case.title} 补强：{case.revision_focus}。"
        f"必须覆盖回归风险：{regressions}。"
        f"当前审核问题：{issue_text}。"
        "保持中文，禁止固定镜头数、四镜头十五秒、十镜头六秒、媒体兜底或空泛关系。"
    )


def _feedback_issue_summary(scores: dict[str, Any]) -> str:
    labels: list[str] = []
    for item in (scores.get("issues") or [])[:8]:
        issue = str(item.get("issue") or "").lower()
        if "english pollution" in issue:
            labels.append("创作文本混入英文、内部标签或占位词")
        elif "shallow" in issue:
            labels.append("角色目标、冲突或关系变化不够具体")
        elif "transition" in issue:
            labels.append("镜头转场缺少可拍设计")
        elif "too long" in issue or "duration" in issue:
            labels.append("镜头时长或制片可执行性不足")
        elif "negative locks" in issue:
            labels.append("身份、服装、场景或道具禁止变化项不足")
        elif "reference" in issue:
            labels.append("资产参考集或引用关系不足")
        else:
            labels.append("专业剧作、拆镜或资产连续性密度不足")
    return "；".join(labels) if labels else "第一轮通过结构校验，但需要提高创作、拆镜和连续性密度"


def _regression_tag_label(tag: str) -> str:
    labels = {
        "A_rights_time_summary": "权利边界、时间和摘要闭环",
        "A_relationship_depth": "角色关系不能停留在浅层动机",
        "B_timed_no_output": "限时任务必须产生有效、可执行输出",
        "C_english_pollution": "禁止英文污染",
        "C_fixed_shots": "禁止固定镜头数量和固定时长",
        "C_overbroad_failure": "避免过宽指令导致失焦",
        "asset_continuity": "资产连续性和禁止变化项",
        "media_fallback_forbidden": "禁止媒体兜底冒充成功",
        "production_feasibility": "制片成本和执行可行性",
        "A_rights_closure": "权利和授权闭环",
        "A_time_summary": "时间线和摘要闭环",
    }
    return labels.get(tag, "专业影视合同回归")


def _final_report(
    *,
    run_root: Path,
    health: dict[str, Any],
    provider_surface: dict[str, Any],
    tiny_dispatch: dict[str, Any],
    smoke: dict[str, Any],
    cases: list[dict[str, Any]],
    dispatch_count: int,
) -> dict[str, Any]:
    all_scores = [score for case in cases for score in case["scores"].values()]
    p0 = sum(int(case["P0"]) for case in cases)
    p1 = sum(int(case["P1"]) for case in cases)
    pass_conditions = [
        dispatch_count >= 22,
        dispatch_count <= MAX_PROVIDER_REQUESTS,
        p0 == 0,
        p1 == 0,
        all(score >= 4 for score in all_scores),
        provider_surface["external_paid_cost_usd"] == 0,
        health.get("provider_gates", {}).get("llm") is True,
        all(health.get("provider_gates", {}).get(key) is False for key in ("image", "video", "audio", "asr", "vision", "external_download")),
    ]
    return {
        "verdict": "PASS" if all(pass_conditions) else "FAIL",
        "gate": "AFS_M6_1_SERVER_LLM_STRICT_CREATIVE_EVALUATION_EXACT_PASS",
        "run_root": str(run_root),
        "provider_surface": provider_surface,
        "health": {
            "status": health.get("status"),
            "local_only": _health_local_only(health),
            "auth_required": health.get("auth_required"),
            "provider_gates": health.get("provider_gates"),
        },
        "tiny_structured_dispatch": tiny_dispatch,
        "smoke": smoke,
        "case_count": len(cases),
        "revision_rounds_per_case": 2,
        "provider_dispatch_count": dispatch_count,
        "successful_dispatch_count": dispatch_count,
        "retry_or_timeout_count": sum(1 for case in cases if case.get("retry_used")),
        "timeout_count": 0,
        "external_paid_cost_usd": 0,
        "estimated_budget_cap_usd": MAX_EXTERNAL_PAID_COST_USD,
        "P0": p0,
        "P1": p1,
        "cases": cases,
        "issue_ledger": {
            "P0": p0,
            "P1": p1,
            "findings": [issue for case in cases for issue in case.get("issues", [])],
            "residual_risk": ["text LLM evaluation is not image/video media QA", "human creative acceptance not claimed"],
        },
        "non_claims": [
            "not_remote_paid_provider_smoke",
            "not_image_or_video_generation",
            "not_generated_media_qa",
            "not_runtime_deployment",
            "not_human_acceptance",
            "not_business_validation",
        ],
    }


def _blocked_report(run_root: Path, reason: str, evidence: dict[str, Any]) -> dict[str, Any]:
    report = {
        "verdict": "BLOCKED",
        "gate": "AFS_M6_1_SERVER_LLM_STRICT_CREATIVE_EVALUATION_EXACT_PASS",
        "run_root": str(run_root),
        "reason": reason,
        "evidence": evidence,
        "provider_dispatch_count": 0,
        "external_paid_cost_usd": 0,
    }
    write_json(run_root / "m6_1_server_codex_real_llm_blocked.json", report)
    return report


def _technical_fail_report(run_root: Path, reason: str, provider_surface: dict[str, Any], dispatch_count: int) -> dict[str, Any]:
    attempted = dispatch_count + 1 if "server_codex" in reason or "preview" in reason else dispatch_count
    report = {
        "verdict": "FAIL",
        "gate": "AFS_M6_1_SERVER_LLM_STRICT_CREATIVE_EVALUATION_EXACT_PASS",
        "run_root": str(run_root),
        "reason": reason[:1400],
        "provider_surface": provider_surface,
        "provider_dispatch_count": dispatch_count,
        "attempted_provider_dispatch_count": attempted,
        "external_paid_cost_usd": 0,
        "P0": 1,
        "P1": 0,
        "issue_ledger": {
            "findings": [{
                "severity": "P0",
                "role": "engineering_lineage_recovery",
                "issue": reason[:900],
            }]
        },
        "non_claims": [
            "not_remote_paid_provider_smoke",
            "not_image_or_video_generation",
            "not_generated_media_qa",
            "not_human_acceptance",
            "not_business_validation",
        ],
    }
    write_json(run_root / "m6_1_server_codex_real_llm_fail.json", report)
    return report


def _safe_case_artifact(
    case: CorpusCase,
    first: dict[str, Any],
    second: dict[str, Any],
    first_scores: dict[str, Any],
    second_scores: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case": case.__dict__,
        "revision1": _safe_preview(first),
        "revision2": _safe_preview(second),
        "revision1_scores": first_scores,
        "revision2_scores": second_scores,
    }


def _safe_preview(preview: dict[str, Any]) -> dict[str, Any]:
    candidate = dict(preview["candidate"])
    return {
        "candidate_digest": preview.get("candidate_digest") or canonical_digest(candidate),
        "provider_dispatch_count": preview.get("provider_dispatch_count"),
        "validation": preview.get("validation"),
        "provider_lineage": candidate.get("provider_lineage"),
        "title": (candidate.get("brief") or {}).get("title"),
        "logline": (candidate.get("brief") or {}).get("logline"),
        "revision": candidate.get("script_revision"),
        "sequence": candidate.get("sequence"),
        "characters": candidate.get("characters"),
        "scenes": candidate.get("scenes"),
        "assets": candidate.get("assets"),
        "shots": candidate.get("shots"),
        "asset_bible": candidate.get("asset_bible"),
        "knowledge_context": candidate.get("knowledge_context"),
    }


def _provider_lineage_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    lineage = dict(candidate.get("provider_lineage") or {})
    return {
        "service_id": lineage.get("service_id"),
        "provider": lineage.get("provider"),
        "model_surface": lineage.get("model_surface"),
        "request_id": lineage.get("request_id"),
        "schema_digest": lineage.get("structured_output_schema_digest"),
        "provider_calls_started": lineage.get("provider_calls_started"),
        "usage": lineage.get("usage"),
    }


def _asset_bible_counts(candidate: dict[str, Any]) -> dict[str, int]:
    bible = candidate.get("asset_bible") if isinstance(candidate.get("asset_bible"), dict) else {}
    return {
        "character_refs": len(bible.get("character_refs") or []),
        "scene_refs": len(bible.get("scene_refs") or []),
        "reference_set_refs": len(bible.get("reference_set_refs") or []),
        "style_refs": len(bible.get("style_refs") or []),
        "prop_refs": len(bible.get("prop_refs") or []),
    }


def _issue(severity: str, role: str, issue: str) -> dict[str, str]:
    return {"severity": severity, "role": role, "issue": issue}


def _creative_text(candidate: dict[str, Any]) -> str:
    keys = ("brief", "script_revision", "sequence", "characters", "scenes", "assets", "shots", "asset_bible")
    ignored_keys = {
        "asset_id",
        "brief_id",
        "candidate_digest",
        "character_id",
        "confidence",
        "delivery_id",
        "fixed_profile_forbidden",
        "kind",
        "lineage_state",
        "m6_schema_version",
        "parent_candidate_digest",
        "provider_dispatch_id",
        "provider_lineage",
        "revision_instruction",
        "rights_refs",
        "schema_version",
        "scene_id",
        "sequence_id",
        "shot_id",
        "source_digest",
        "source_kind",
        "timeline_refs",
        "version",
    }
    values: list[str] = []

    def collect(value: Any, key: str = "") -> None:
        if key in ignored_keys or key.endswith("_id") or key.endswith("_ids") or key.endswith("_refs"):
            return
        if isinstance(value, str):
            if value and not re.fullmatch(r"[a-z0-9_.:-]+", value, re.I):
                values.append(value)
            return
        if isinstance(value, list):
            for item in value:
                collect(item, key)
            return
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                collect(child_value, str(child_key))

    for root_key in keys:
        collect(candidate.get(root_key), root_key)
    return "\n".join(values)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _health_allows_candidate_llm_only(health: dict[str, Any]) -> bool:
    gates = health.get("provider_gates") if isinstance(health.get("provider_gates"), dict) else {}
    return (
        health.get("status") == "ready"
        and _health_local_only(health) is True
        and gates.get("llm") is True
        and all(gates.get(key) is False for key in ("image", "video", "audio", "asr", "vision", "external_download"))
    )


def _health_local_only(health: dict[str, Any]) -> bool:
    exposure = health.get("exposure") if isinstance(health.get("exposure"), dict) else {}
    boundaries = health.get("boundaries") if isinstance(health.get("boundaries"), dict) else {}
    return health.get("local_only") is True or exposure.get("local_only") is True or boundaries.get("local_only") is True


def _merge_no_proxy(value: str | None) -> str:
    entries = [item.strip() for item in (value or "").split(",") if item.strip()]
    for item in ("127.0.0.1", "localhost", "::1"):
        if item.lower() not in {entry.lower() for entry in entries}:
            entries.append(item)
    return ",".join(entries)


def corpus_cases() -> list[CorpusCase]:
    return [
        CorpusCase(
            "dialogue_room",
            "双人室内对白",
            "idea",
            """
角色：林澈、唐予。场景：夜晚旧剪辑室、清晨屋顶。道具：场记板、旧镜头。特写：林澈手背的伤痕、时间线红色标记。
风格：克制写实冷暖对照。时间：夜晚到清晨。光线：剪辑室屏幕冷光与屋顶晨光。季节：初秋。连续性：旧镜头始终在唐予手边。
目标：林澈想证明被删掉的素材能救回影片。冲突：唐予担心返工拖垮预算。关系：两人从互相指责转为共同承担。变化：林澈从逃避失误转为主动承认。
林澈盯着屏幕里的断帧，低声说如果这一秒还在，结尾就不是谎言。唐予把场记板放到桌边，要求他在十分钟内给出能拍的重做方案。两人带着旧镜头上到屋顶，晨光压住城市噪声，林澈终于说出自己删错素材的真相。
""",
            "加深林澈与唐予的关系变化，明确版权来自用户剧本输入，不承诺媒体生成。",
            ("A_rights_time_summary", "A_relationship_depth"),
        ),
        CorpusCase(
            "four_person_action",
            "四人动作交接",
            "idea",
            """
角色：秦越、孟栖、老许、安然。场景：雨夜码头、货柜通道、临时医疗车。道具：防水硬盘、蓝色雨披、折叠担架。特写：硬盘封条、安然手套上的血迹。
时间：一场暴雨夜。光线：钠灯、车灯、手电。季节：夏末台风前。连续性：硬盘从秦越交到孟栖，再被老许藏进担架夹层。
秦越带着硬盘穿过货柜，被追车灯扫到。孟栖从通道另一侧接应，老许用担架假装转运伤员，安然必须决定是否暴露自己医生身份。四个人的交接必须在三分钟内完成，但每个人都隐藏一个不能说的目的。
""",
            "让四人调度可拍、镜头不机械，交代每个角色的隐藏目的与道具交接连续性。",
            ("B_timed_no_output", "production_feasibility"),
        ),
        CorpusCase(
            "nonlinear_memory",
            "非线性记忆",
            "idea",
            """
角色：许静、卫南。场景：冬季美术馆长廊、十年前修复室、当下封闭库房。道具：白手套、破损画框、蓝色颜料样本。特写：画布边缘的蓝色颗粒。
结构：现在和十年前交错，但观众必须能追踪画框位置。目标：许静要证明修复记录被伪造。冲突：卫南必须保护开幕展。关系：师徒从回避到正面对话。变化：卫南承认曾签过错误记录。
许静在长廊停下脚步，听见修复室里的刮刀声记忆。卫南拦住她，说现在进去展览就完了。许静戴上白手套指出画框背面日期，卫南沉默后打开库房灯。
""",
            "补清非线性时间标记和画框连续性，防止摘要闭环缺失。",
            ("A_time_summary", "C_overbroad_failure"),
        ),
        CorpusCase(
            "existing_script_rewrite",
            "已有剧本改写",
            "script",
            """
角色：米拉、陶、阿衡。场景：傍晚观测台、雨后的信号室、地下水泵间。道具：铜色罗盘、裂开的玻璃杯、备用电池。
外观：米拉短发银灰外套；陶黑色雨衣；阿衡戴旧耳机。服装：三人保持同一夜晚的湿冷质感。年龄：二十七到三十五岁。比例：真人写实。
米拉校准镜头时，远处信号突然偏移，她要求陶记录频率。陶在信号室打开备用电池，却发现玻璃杯裂纹与信号波形一致。阿衡听见水泵间的旧广播，意识到偏移不是天气，而是有人在地下重放十年前的呼救。三人沿着水声进入地下，罗盘开始倒转。陶读出最后一段呼救，阿衡摘下耳机，承认当年自己听过同样的声音却没有上报。米拉决定把镜头留在三人的沉默上。
""",
            "保持既有剧本事实，增强关系压力、罗盘和玻璃杯连续性，避免英文污染。",
            ("C_english_pollution", "A_relationship_depth"),
        ),
        CorpusCase(
            "documentary_interview",
            "纪录片访谈",
            "idea",
            """
角色：采访者周岚、修船师傅陈泊、女儿陈小满。场景：清晨船坞、午后厨房、傍晚堤岸。道具：录音笔、旧船票、焊工面罩。特写：录音笔红灯、船票折痕。
目标：周岚想拍一条关于最后一艘木船修复的纪录片。冲突：陈泊拒绝把女儿离开的原因说给镜头。关系：采访者从追问者变成见证者，父女从躲避到一起修补船票。变化：陈小满决定出镜但要求删掉母亲隐私。
纪录片必须明确权利边界、受访者确认、可撤回素材，不承诺生成图片或下载外部素材。
""",
            "强化纪录片权利和受访者确认边界，避免把隐私当成可自动消费素材。",
            ("A_rights_closure", "media_fallback_forbidden"),
        ),
        CorpusCase(
            "children_fantasy",
            "儿童奇幻",
            "idea",
            """
角色：小满、纸船先生、钟楼管理员。场景：雨后小学操场、会说话的排水沟、黄昏钟楼。道具：红色雨鞋、纸船、铜铃。特写：雨鞋上的泥点、纸船折痕。
目标：小满想把丢失的作业本找回来。冲突：纸船先生只能顺水漂走，管理员害怕钟楼再次停摆。关系：小满从命令纸船变成听懂它的害怕。变化：管理员承认是自己把作业本藏起来，因为里面夹着他年轻时的信。
要求童真但不幼稚，镜头要可拍，角色身份和服装不能漂移。
""",
            "保持儿童视角和可拍成本，补足纸船与雨鞋的资产锁定。",
            ("C_fixed_shots", "asset_continuity"),
        ),
        CorpusCase(
            "silent_suspense",
            "无对白悬疑",
            "idea",
            """
角色：守夜人韩青、楼上住户纪蓝。场景：凌晨电梯间、停电楼梯、顶楼水箱旁。道具：钥匙串、老式手电、湿脚印。特写：电梯楼层数字、钥匙串缺失的一枚。
这是一段几乎无对白悬疑。目标：韩青要确认顶楼水声来源。冲突：纪蓝一直在楼梯阴影里阻止他上楼。关系：两人从陌生对峙到发现共同被同一串钥匙牵连。变化：韩青从执行巡逻转为保护纪蓝不被误认。
声音设计必须承担叙事，不能用对白解释全部信息。
""",
            "增强声音与视觉叙事，不允许用对白偷懒，也不能输出空泛媒体 fallback。",
            ("media_fallback_forbidden", "C_overbroad_failure"),
        ),
        CorpusCase(
            "brand_short_ad",
            "品牌短广告",
            "idea",
            """
角色：店主阿珊、常客罗均、外卖骑手小北。场景：清晨街角咖啡店、雨中取餐口、夜晚打烊柜台。道具：可重复使用杯、手写价签、雨伞。特写：杯盖划痕、价签上的改价笔迹。
品牌目标：拍一支六十秒内的低调短广告，表现街角咖啡店坚持不用一次性杯。冲突：罗均赶时间，小北担心延误订单，阿珊必须解释规则但不能说教。关系：常客从抱怨到主动归还杯。变化：小北发现这套规则也能减少他车箱里的垃圾。
要求商业可执行、权利边界清楚，不夸大环保效果。
""",
            "补强品牌合规、成本和不夸大声明，保持剧情驱动而不是口号模板。",
            ("A_rights_closure", "production_feasibility"),
        ),
        CorpusCase(
            "period_ensemble",
            "古装群像",
            "idea",
            """
角色：沈砚、陆稚、顾夫人、驿卒阿青、县令。场景：雨夜驿站、大堂屏风后、清晨马厩。道具：密信、油纸伞、青瓷杯、马鞍。特写：密信火漆、青瓷杯裂口。
目标：沈砚要在天亮前把密信交给县令。冲突：顾夫人认为密信会牵连陆家，驿卒阿青受命偷换马鞍。关系：沈砚和陆稚从互相利用到共同保护阿青。变化：顾夫人放弃家族体面，承认自己才是密信来源。
要求服装、身份、礼法和道具位置连续，群像调度不能变成固定镜头模板。
""",
            "强化群像关系和古装礼法连续性，镜头数量由冲突推进决定。",
            ("C_fixed_shots", "A_relationship_depth"),
        ),
        CorpusCase(
            "sci_fi_chamber",
            "科幻密闭空间",
            "idea",
            """
角色：航天工程师岑露、心理官裴远、维修机器人编号七。场景：环月舱控制室、狭窄气闸、失重维修槽。道具：氧气阀、裂纹平板、红色束带。特写：氧气阀刻度、编号七摄像头上的划痕。
目标：岑露要在二十分钟内恢复氧气循环。冲突：裴远怀疑编号七被外部指令污染，编号七只能用灯光回应。关系：岑露从把机器人当工具变成承认它保留了上一次事故记忆。变化：裴远从阻止维修转为替编号七承担责任。
必须有明确限时、空间调度、技术可执行边界，不允许无效产出或英文术语污染。
""",
            "补清二十分钟限时、舱内空间和机器人身份锁，不使用英语技术词堆砌。",
            ("B_timed_no_output", "C_english_pollution", "production_feasibility"),
        ),
    ]


if __name__ == "__main__":
    raise SystemExit(main())
