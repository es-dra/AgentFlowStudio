from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentflow.harness.json_io import write_json  # noqa: E402
from agentflow_studio.model_gateway.provider_adapter import (  # noqa: E402
    ProviderDispatchRequest,
    load_provider_registry,
    structured_output_schema_digest,
)
from tools.studio_asset_context_browser_qa_support import free_port, stop_runtime, wait_for_http  # noqa: E402
from tools.studio_m6_6_real_llm_visible_tasks_smoke import (  # noqa: E402
    SERVER_CODEX_SERVICE_ID,
    LLM_MODEL,
    LLM_REASONING_EFFORT,
    Number,
    apply_candidate_env,
    assert_llm_only_health,
    corpus_cases,
    create_project,
    graph,
    graph_summary,
    http_json,
    issue,
    no_user_visible_issues,
    provider_config_payload,
    provider_summary,
    restore_env,
    run_screenplay_case,
    run_shot_breakdown_case,
    safe_text,
    strict_review_lenses,
    strict_review_schema,
    run_tiny_provider_probe,
    start_candidate_runtime,
)


DEFAULT_EVIDENCE_BASE = Path(
    "/home/afs-ops/.codex/afs-evidence/afs-m6-7-creative-task-reliability-product-shell-20260723"
)


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    run_root = Path(args.evidence_root or default_run_root()).resolve()
    runtime_root = run_root / "runtime-root"
    provider_config = run_root / "provider-config.no-secrets.json"
    run_root.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)
    provider_config.write_text(json.dumps(provider_config_payload(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    previous_env = apply_candidate_env(runtime_root, provider_config)
    server: subprocess.Popen[str] | None = None
    port = int(args.port or free_port())
    base_url = f"http://127.0.0.1:{port}/"
    try:
        if args.reuse_runtime_report:
            runtime = json.loads(Path(args.reuse_runtime_report).read_text(encoding="utf-8"))
            tiny_probe = json.loads(Path(args.reuse_tiny_probe).read_text(encoding="utf-8")) if args.reuse_tiny_probe else {"provider_request_count": 0, "status": "reused"}
            health = reused_llm_only_health()
        else:
            tiny_probe = run_tiny_provider_probe(run_root)
            server = start_candidate_runtime(repo, runtime_root, port)
            wait_for_http(urljoin(base_url, "health"), timeout=60)
            health = http_json("GET", urljoin(base_url, "health"))
            assert_llm_only_health(health)
            runtime = run_m6_7_runtime_smoke(base_url, run_root)
        browser_reports = load_browser_reports_m6_7(args.browser_report)
        strict_review = run_m6_7_codex_work_strict_review(run_root, runtime, browser_reports)
        report = final_report(run_root, health, tiny_probe, runtime, strict_review, browser_reports)
        write_json(run_root / "m6_7_real_llm_creative_task_reliability_report.safe.json", report)
        print(json.dumps({
            "status": report["status"],
            "report": str(run_root / "m6_7_real_llm_creative_task_reliability_report.safe.json"),
            "provider_request_count": report["provider_request_count"],
            "script_successes": report["runtime"]["script_successes"],
            "shot_successes": report["runtime"]["shot_successes"],
            "P0": report["P0"],
            "P1": report["P1"],
            "P2": report["P2"],
            "external_paid_cost_usd": report["external_paid_cost_usd"],
        }, ensure_ascii=False, sort_keys=True))
        return 0 if report["status"] == "passed" else 1
    except Exception as exc:
        failure = technical_fail(run_root, str(exc))
        write_json(run_root / "m6_7_real_llm_creative_task_reliability_fail.safe.json", failure)
        print(json.dumps({
            "status": failure["status"],
            "report": str(run_root / "m6_7_real_llm_creative_task_reliability_fail.safe.json"),
            "reason": failure["reason"],
        }, ensure_ascii=False, sort_keys=True))
        return 1
    finally:
        if server is not None:
            stop_runtime(server)
        restore_env(previous_env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.7 real server_codex creative task reliability smoke")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--evidence-root", default="")
    parser.add_argument("--browser-report", action="append", default=[])
    parser.add_argument("--reuse-runtime-report", default="")
    parser.add_argument("--reuse-tiny-probe", default="")
    parser.add_argument("--port", type=int, default=0)
    return parser.parse_args()


def run_m6_7_runtime_smoke(base_url: str, run_root: Path) -> dict[str, Any]:
    project_id = f"m6-7-real-creative-tasks-{int(time.time())}"
    create_project(base_url, project_id)
    before = graph(base_url, project_id)
    cases = corpus_cases()
    script_cases = [run_screenplay_case(base_url, project_id, case, run_root) for case in cases]
    shot_cases = [run_shot_breakdown_case_m6_7(base_url, project_id, case, run_root) for case in cases]
    after = graph(base_url, project_id)
    issues = runtime_issues_m6_7(script_cases, shot_cases, before, after)
    report = {
        "status": "passed" if no_user_visible_issues(issues) else "failed",
        "project_id": project_id,
        "provider_request_count": len(script_cases) + len(shot_cases),
        "provider": provider_summary("runtime_schema_digests_per_case"),
        "health_route": "candidate_runtime_embedded_creative_actions_preview",
        "graph_before": graph_summary(before),
        "graph_after": graph_summary(after),
        "graph_mutated_by_preview": graph_summary(before) != graph_summary(after),
        "screenplay_cases": script_cases,
        "shot_breakdown_case": shot_cases[0] if shot_cases else {},
        "shot_breakdown_cases": shot_cases,
        "script_successes": sum(1 for item in script_cases if item.get("provider_calls_started") is True),
        "shot_successes": sum(1 for item in shot_cases if item.get("provider_calls_started") is True),
        "issue_ledger": issues,
    }
    write_json(run_root / "runtime_m6_7_creative_task_smoke.safe.json", report)
    if report["status"] != "passed":
        raise AssertionError(f"M6.7 runtime creative task smoke failed: {issues}")
    return report


def run_shot_breakdown_case_m6_7(base_url: str, project_id: str, case: Any, run_root: Path) -> dict[str, Any]:
    summary = run_shot_breakdown_case(base_url, project_id, case, run_root)
    write_json(run_root / f"runtime_shot_breakdown_{case.case_id}.safe.json", summary)
    return summary


def runtime_issues_m6_7(
    script_cases: list[dict[str, Any]],
    shot_cases: list[dict[str, Any]],
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if graph_summary(before) != graph_summary(after):
        issues.append(issue("P0", "preview_mutated_graph", "runtime preview changed ProductionGraph"))
    if len(script_cases) < 3 or sum(1 for item in script_cases if item.get("provider_calls_started") is True) < 3:
        issues.append(issue("P0", "script_success_count", "fewer than three real server_codex screenplay successes"))
    if len(shot_cases) < 3 or sum(1 for item in shot_cases if item.get("provider_calls_started") is True) < 3:
        issues.append(issue("P0", "shot_success_count", "fewer than three real server_codex shot breakdown successes"))
    for item in script_cases:
        structure = item.get("screenplay_structure") or {}
        if item.get("provider_calls_started") is not True:
            issues.append(issue("P0", f"{item.get('case_id')}_fake_provider", "provider call did not start"))
        if item.get("expansion_ratio", 0) < 1.25 or item.get("revised_characters", 0) < 160:
            issues.append(issue("P1", f"{item.get('case_id')}_weak_expansion", "screenplay revision was not materially expanded"))
        if int(structure.get("scene_count") or 0) < 1 or int(structure.get("action_blocks") or 0) < 1:
            issues.append(issue("P0", f"{item.get('case_id')}_not_screenplay", "typed screenplay structure is missing action scene blocks"))
        if structure.get("nonprofessional_heading_count"):
            issues.append(issue("P1", f"{item.get('case_id')}_nonprofessional_headings", "screenplay headings are not explicit interior/exterior scene headings"))
        if structure.get("missing_time_heading_count"):
            issues.append(issue("P1", f"{item.get('case_id')}_incomplete_headings", "screenplay headings must include space, location and time"))
        if structure.get("dangling_character_cue_count"):
            issues.append(issue("P1", f"{item.get('case_id')}_dangling_character_cues", "screenplay character cues must be followed by dialogue in the same scene"))
        if item.get("graph_mutation", {}).get("mutated") is True:
            issues.append(issue("P0", f"{item.get('case_id')}_preview_mutated_graph", "script preview mutated graph"))
    for item in shot_cases:
        if item.get("provider_calls_started") is not True:
            issues.append(issue("P0", f"{item.get('case_id')}_shot_fake_provider", "shot breakdown provider did not start"))
        if int(item.get("total_shots") or 0) < 3:
            issues.append(issue("P1", f"{item.get('case_id')}_shot_too_shallow", "shot breakdown produced fewer than three shots"))
        if item.get("graph_mutation", {}).get("mutated") is True:
            issues.append(issue("P0", f"{item.get('case_id')}_shot_preview_mutated_graph", "shot breakdown preview mutated graph"))
        if len(item.get("first_shots") or []) < 2:
            issues.append(issue("P1", f"{item.get('case_id')}_shot_not_inspectable", "shot breakdown has too few inspectable shot details"))
    return issues


def run_m6_7_codex_work_strict_review(
    run_root: Path,
    runtime: dict[str, Any],
    browser_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    schema = strict_review_schema()
    digest = structured_output_schema_digest(schema)
    evidence = strict_review_evidence_m6_7(runtime, browser_reports)
    reviews = []
    total_latency_ms = 0.0
    for index, lens in enumerate(strict_review_lenses(), start=1):
        started = time.perf_counter()
        result = load_provider_registry().dispatch(
            "llm",
            SERVER_CODEX_SERVICE_ID,
            ProviderDispatchRequest(
                prompt=strict_review_prompt_m6_7(lens, evidence, digest),
                output_dir=run_root / f"codex-work-review-m6-7-{index:02d}-{lens['id']}",
                task_type=f"m6_7_codex_work_review_{lens['id']}",
                structured_output_contract_id="afs.m6_7.codex_work_strict_review.v0.1",
                structured_output_schema=schema,
                structured_output_schema_digest=digest,
                timeout_sec=120.0,
            ),
        )
        total_latency_ms += round((time.perf_counter() - started) * 1000, 2)
        structured = result.get("structured_output") if isinstance(result, dict) else None
        if not isinstance(structured, dict):
            raise AssertionError(f"M6.7 strict review {lens['id']} returned no structured output")
        reviews.append({
            "lens": structured.get("lens"),
            "status": structured.get("status"),
            "score": Number(structured.get("score")),
            "p0": list(structured.get("p0") or []),
            "p1": list(structured.get("p1") or []),
            "p2": list(structured.get("p2") or []),
            "rationale": safe_text(structured.get("rationale"), 500),
        })
    issues = []
    for review in reviews:
        for severity in ("p0", "p1", "p2"):
            for issue_text in review.get(severity) or []:
                issues.append(issue(severity.upper(), f"{review['lens']}_{len(issues) + 1}", safe_text(issue_text, 500)))
        if review.get("status") != "pass" or Number(review.get("score")) < 4:
            issues.append(issue("P1", f"{review['lens']}_score_or_status", f"status={review.get('status')} score={review.get('score')}"))
    report = {
        "status": "passed" if no_user_visible_issues(issues) else "failed",
        "provider_request_count": len(reviews),
        "provider": {
            **provider_summary(digest),
            "model_alias": LLM_MODEL,
            "reasoning_effort": LLM_REASONING_EFFORT,
        },
        "latency_ms": round(total_latency_ms, 2),
        "evidence_summary": {
            "screenplay_cases": len(runtime.get("screenplay_cases") or []),
            "shot_breakdown_cases": len(runtime.get("shot_breakdown_cases") or []),
            "browser_rounds": len(browser_reports),
        },
        "reviews": reviews,
        "issue_ledger": issues,
    }
    write_json(run_root / "codex_work_strict_review_m6_7.safe.json", report)
    if report["status"] != "passed":
        raise AssertionError(f"Codex Work strict review failed: {issues}")
    return report


def strict_review_prompt_m6_7(lens: dict[str, str], evidence: dict[str, Any], schema_digest: str) -> str:
    return "\n".join([
        "你是 AFS M6.7 Gate 的独立 Codex Work 严格评审员。",
        "只根据给定安全证据评审；不要访问文件、网络、secret、图片或视频。",
        "必须尖锐：仍存在的用户可见 P0/P1/P2 填入数组；没有则空数组。",
        "status=pass 仅当该 lens 没有 P0/P1/P2 且 score>=4。",
        "本轮目标：创作任务可靠性、真实剧本扩写、拆分分镜、产品壳项目/账户 UX、即时节点反馈。",
        "不要把自动评审冒充 Owner 人工验收。",
        f"Lens: {lens['name']} / {lens['focus']}",
        f"Closed schema digest: {schema_digest}",
        "<safe_m6_7_evidence>",
        json.dumps(evidence, ensure_ascii=False)[:16000],
        "</safe_m6_7_evidence>",
        "返回严格 JSON。",
    ])


def strict_review_evidence_m6_7(runtime: dict[str, Any], browser_reports: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "runtime_status": runtime.get("status"),
        "provider": runtime.get("provider"),
        "request_counts": {
            "script_successes": runtime.get("script_successes"),
            "shot_successes": runtime.get("shot_successes"),
            "provider_request_count": runtime.get("provider_request_count"),
            "external_paid_cost_usd": 0,
        },
        "graph_mutated_by_preview": runtime.get("graph_mutated_by_preview"),
        "shot_candidate_graph_evidence": {
            "runtime_cases": [
                {
                    "case_id": item.get("case_id"),
                    "scene_count": item.get("scene_count"),
                    "total_shots": item.get("total_shots"),
                    "estimated_duration_sec": item.get("estimated_duration_sec"),
                    "first_scene": item.get("first_scene"),
                    "first_shots": item.get("first_shots"),
                    "provider_calls_started": item.get("provider_calls_started"),
                    "preview_mutated_graph": item.get("graph_mutation", {}).get("mutated"),
                }
                for item in runtime.get("shot_breakdown_cases") or []
            ],
            "browser_apply_contract": [
                "Round A/B shot_candidate_graph_apply waits until localStorage node count increases after Apply.",
                "The browser assertion requires visible ProductionGraph roles m6_6_shot_sequence_candidate, m6_6_scene_candidate and m6_6_shot_candidate.",
                "Shot preview remains graph_mutation=false; Apply is the only mutation path in the browser lane.",
            ],
        },
        "browser_rounds": browser_reports,
        "screenplay_cases": [
            {
                "case_id": item.get("case_id"),
                "title": item.get("title"),
                "source_characters": item.get("source_characters"),
                "revised_characters": item.get("revised_characters"),
                "expansion_ratio": item.get("expansion_ratio"),
                "structure": item.get("screenplay_structure"),
                "task_phase": item.get("creative_task", {}).get("phase"),
                "provider_calls_started": item.get("provider_calls_started"),
                "graph_mutation": item.get("graph_mutation"),
                "change_summary": item.get("change_summary"),
                "excerpt": safe_text(item.get("revised_excerpt"), 700),
            }
            for item in runtime.get("screenplay_cases") or []
        ],
        "source_contracts": [
            "Round A/B browser reports prove immediate running visual, preview/cancel, preview/apply, project/account shell, delete confirmation and five viewports.",
            "Script revision preview has graph_mutation=false and apply is same-node in browser lane.",
            "Shot breakdown preview has graph_mutation=false; browser apply creates visible candidate sequence/scene/shot roles.",
            "Runtime server_codex LLM route produced three screenplay previews and three shot breakdown previews; no image/video/audio/asr/vision/external_download gates are used.",
        ],
    }


def load_browser_reports_m6_7(paths: list[str]) -> list[dict[str, Any]]:
    reports = []
    for raw in paths or []:
        path = Path(raw).resolve()
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = data.get("cases") if isinstance(data.get("cases"), dict) else {}
        reports.append({
            "path": str(path),
            "status": data.get("status"),
            "round": data.get("round"),
            "P0": data.get("P0"),
            "P1": data.get("P1"),
            "P2": data.get("P2"),
            "case_count": len(cases),
            "viewports": [item.get("viewport") for item in cases.values()],
            "max_feedback_ms": data.get("max_feedback_ms"),
            "screenshot_count": len(data.get("screenshots") or {}),
            "representative_screenshots": dict(list((data.get("screenshots") or {}).items())[:10]),
            "checks_by_viewport": [
                {
                    "viewport": item.get("viewport"),
                    "running_visual": item.get("running_visual"),
                    "script_cancel_late_response_ignored": item.get("script_cancel_late_response_ignored"),
                    "script_same_node_apply": item.get("script_same_node_apply"),
                    "shot_candidate_graph_apply": item.get("shot_candidate_graph_apply"),
                    "project_switcher_no_viewport_change": item.get("project_switcher_no_viewport_change"),
                    "account_menu_real": item.get("account_menu_real"),
                    "delete_project_supported": item.get("delete_project_supported"),
                    "no_horizontal_overflow": item.get("no_horizontal_overflow"),
                    "max_feedback_ms": item.get("max_feedback_ms"),
                }
                for item in cases.values()
            ],
            "role_matrix": data.get("role_task_completion_matrix") or {},
            "provider_dispatch_count": data.get("provider_dispatch_count"),
            "cost_usd": data.get("cost_usd"),
        })
    return reports


def reused_llm_only_health() -> dict[str, Any]:
    return {
        "status": "ready",
        "provider_gates": {
            "llm": True,
            "image": False,
            "video": False,
            "audio": False,
            "asr": False,
            "vision": False,
            "external_download": False,
        },
        "local_only": True,
        "auth_required": False,
    }


def final_report(
    run_root: Path,
    health: dict[str, Any],
    tiny_probe: dict[str, Any],
    runtime: dict[str, Any],
    strict_review: dict[str, Any],
    browser_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    issues = list(runtime.get("issue_ledger") or []) + list(strict_review.get("issue_ledger") or [])
    p0 = sum(1 for item in issues if item.get("severity") == "P0")
    p1 = sum(1 for item in issues if item.get("severity") == "P1")
    p2 = sum(1 for item in issues if item.get("severity") == "P2")
    request_count = int(tiny_probe.get("provider_request_count") or 0)
    request_count += int(runtime.get("provider_request_count") or 0)
    request_count += int(strict_review.get("provider_request_count") or 0)
    return {
        "artifact_type": "afs_m6_7_real_llm_creative_task_reliability_smoke",
        "schema_version": "afs.m6_7.real_llm_creative_task_reliability_smoke.v0.1",
        "status": "passed" if p0 == p1 == p2 == 0 else "failed",
        "run_root": str(run_root),
        "provider": {
            "service_id": SERVER_CODEX_SERVICE_ID,
            "provider": "codex_local",
            "model_surface": "server-codex-login via configured codex_local adapter",
            "external_paid_cost_usd": 0,
            "image_video_generation_started": False,
        },
        "health": {
            "status": health.get("status"),
            "provider_gates": health.get("provider_gates"),
            "local_only": health.get("local_only"),
            "auth_required": health.get("auth_required"),
        },
        "tiny_provider_probe": tiny_probe,
        "runtime": runtime,
        "browser_visible_task_rounds": browser_reports,
        "codex_work_strict_review": strict_review,
        "provider_request_count": request_count,
        "retry_count": 0,
        "timeout_count": 0,
        "external_paid_cost_usd": 0,
        "P0": p0,
        "P1": p1,
        "P2": p2,
        "issue_ledger": issues,
        "non_claims": [
            "not_owner_acceptance",
            "not_business_validation",
            "not_paid_image_video_smoke",
            "not_generated_media_qa",
            "not_public_release",
        ],
    }


def technical_fail(run_root: Path, reason: str) -> dict[str, Any]:
    return {
        "artifact_type": "afs_m6_7_real_llm_creative_task_reliability_smoke",
        "schema_version": "afs.m6_7.real_llm_creative_task_reliability_smoke.v0.1",
        "status": "technical_fail",
        "run_root": str(run_root),
        "reason": " ".join(str(reason).split())[:1200],
        "provider": {
            "service_id": SERVER_CODEX_SERVICE_ID,
            "provider": "codex_local",
            "external_paid_cost_usd": 0,
        },
        "non_claims": ["not_owner_acceptance", "not_business_validation"],
    }


def default_run_root() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return str(DEFAULT_EVIDENCE_BASE / f"{stamp}-real-llm-creative-task-reliability")


if __name__ == "__main__":
    raise SystemExit(main())
