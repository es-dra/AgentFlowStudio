from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import ProxyHandler, Request, build_opener

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.company_secrets import SERVER_CODEX_SERVICE_ID
from agentflow_studio.model_gateway.provider_adapter import (
    ProviderDispatchRequest,
    load_provider_registry,
    structured_output_schema_digest,
)
from tools.studio_asset_context_browser_qa_support import free_port, stop_runtime, wait_for_http


DEFAULT_EVIDENCE_BASE = Path(
    "/home/afs-ops/.codex/afs-evidence/afs-m6-6-visible-creative-tasks-screenplay-graph-actions-20260723"
)
LLM_MODEL = "gpt-5.5"
LLM_REASONING_EFFORT = "medium"
LLM_GATE = "AFS_ALLOW_REMOTE_LLM"
NON_LLM_GATES = (
    "AFS_ALLOW_REMOTE_IMAGE",
    "AFS_ALLOW_REMOTE_VIDEO",
    "AFS_ALLOW_REMOTE_AUDIO",
    "AFS_ALLOW_REMOTE_ASR",
    "AFS_ALLOW_REMOTE_VISION",
    "AFS_ALLOW_EXTERNAL_DOWNLOAD",
)


@dataclass(frozen=True)
class CorpusCase:
    case_id: str
    title: str
    node_type: str
    source_text: str
    expected_focus: str


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    run_root = Path(args.evidence_root or default_run_root()).resolve()
    runtime_root = run_root / "runtime-root"
    run_root.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)
    browser_reports = load_browser_reports(args.browser_report)
    conversation_reports = load_conversation_reports(args.conversation_report)
    provider_config = run_root / "provider-config.no-secrets.json"
    provider_config.write_text(json.dumps(provider_config_payload(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    previous_env = apply_candidate_env(runtime_root, provider_config)
    server: subprocess.Popen[str] | None = None
    port = int(args.port or free_port())
    base_url = f"http://127.0.0.1:{port}/"
    try:
        tiny_probe = run_tiny_provider_probe(run_root)
        server = start_candidate_runtime(repo, runtime_root, port)
        wait_for_http(urljoin(base_url, "health"), timeout=60)
        health = http_json("GET", urljoin(base_url, "health"))
        assert_llm_only_health(health)
        runtime = run_runtime_visible_task_smoke(base_url, run_root)
        strict_review = run_codex_work_strict_review(run_root, runtime, browser_reports, conversation_reports)
        report = final_report(run_root, health, tiny_probe, runtime, strict_review, browser_reports, conversation_reports)
        write_json(run_root / "m6_6_real_llm_visible_tasks_report.json", report)
        print(json.dumps({
            "status": report["status"],
            "report": str(run_root / "m6_6_real_llm_visible_tasks_report.json"),
            "provider_request_count": report["provider_request_count"],
            "P0": report["P0"],
            "P1": report["P1"],
            "P2": report["P2"],
            "external_paid_cost_usd": report["external_paid_cost_usd"],
        }, ensure_ascii=False, sort_keys=True))
        return 0 if report["status"] == "passed" else 1
    except Exception as exc:
        failure = technical_fail(run_root, str(exc))
        write_json(run_root / "m6_6_real_llm_visible_tasks_fail.json", failure)
        print(json.dumps({
            "status": failure["status"],
            "report": str(run_root / "m6_6_real_llm_visible_tasks_fail.json"),
            "reason": failure["reason"],
        }, ensure_ascii=False, sort_keys=True))
        return 1
    finally:
        if server is not None:
            stop_runtime(server)
        restore_env(previous_env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.6 real server_codex visible creative task smoke")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--evidence-root", default="")
    parser.add_argument("--browser-report", action="append", default=[])
    parser.add_argument("--conversation-report", action="append", default=[])
    parser.add_argument("--port", type=int, default=0)
    return parser.parse_args()


def run_tiny_provider_probe(run_root: Path) -> dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["ok", "note"],
        "properties": {
            "ok": {"type": "boolean"},
            "note": {"type": "string", "minLength": 4},
        },
    }
    digest = structured_output_schema_digest(schema)
    started = time.perf_counter()
    result = load_provider_registry().dispatch(
        "llm",
        SERVER_CODEX_SERVICE_ID,
        ProviderDispatchRequest(
            prompt="返回 JSON：ok=true；note 用中文说明这是 M6.6 server_codex 极小结构化连通性验证。",
            output_dir=run_root / "tiny-provider-probe",
            task_type="m6_6_tiny_provider_probe",
            structured_output_contract_id="afs.m6_6.tiny_provider_probe.v0.1",
            structured_output_schema=schema,
            structured_output_schema_digest=digest,
            timeout_sec=90.0,
        ),
    )
    structured = result.get("structured_output") if isinstance(result, dict) else None
    if not isinstance(structured, dict) or structured.get("ok") is not True:
        raise AssertionError("tiny server_codex provider probe did not return structured ok=true")
    probe = {
        "status": "passed",
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "provider_request_count": 1,
        "provider": provider_summary(digest),
        "note": safe_text(structured.get("note"), 240),
    }
    write_json(run_root / "tiny_provider_probe.safe.json", probe)
    return probe


def run_runtime_visible_task_smoke(base_url: str, run_root: Path) -> dict[str, Any]:
    project_id = f"m6-6-real-visible-tasks-{int(time.time())}"
    create_project(base_url, project_id)
    before = graph(base_url, project_id)
    script_cases = [run_screenplay_case(base_url, project_id, case, run_root) for case in corpus_cases()]
    shot_case = run_shot_breakdown_case(base_url, project_id, corpus_cases()[-1], run_root)
    after = graph(base_url, project_id)
    issues = runtime_issues(script_cases, shot_case, before, after)
    report = {
        "status": "passed" if no_user_visible_issues(issues) else "failed",
        "project_id": project_id,
        "provider_request_count": len(script_cases) + 1,
        "provider": provider_summary("runtime_schema_digests_per_case"),
        "health_route": "candidate_runtime_embedded_creative_actions_preview",
        "graph_before": graph_summary(before),
        "graph_after": graph_summary(after),
        "graph_mutated_by_preview": graph_summary(before) != graph_summary(after),
        "screenplay_cases": script_cases,
        "shot_breakdown_case": shot_case,
        "issue_ledger": issues,
    }
    write_json(run_root / "runtime_visible_task_smoke.safe.json", report)
    if report["status"] != "passed":
        raise AssertionError(f"runtime visible task smoke failed: {issues}")
    return report


def run_screenplay_case(base_url: str, project_id: str, case: CorpusCase, run_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    response = http_json(
        "POST",
        urljoin(base_url, f"projects/{project_id}/embedded-creative-actions/preview"),
        embedded_payload(case, "script_revision", "professional_expansion"),
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    assert_embedded_llm_response(response, f"{case.case_id}.screenplay")
    preview = response["preview"]
    candidate = preview.get("screenplay_candidate") if isinstance(preview.get("screenplay_candidate"), dict) else {}
    structure = screenplay_structure(candidate)
    revised = str(preview.get("revised_text") or "")
    summary = {
        "case_id": case.case_id,
        "title": case.title,
        "source_characters": len(case.source_text),
        "revised_characters": len(revised),
        "expansion_ratio": round(len(revised) / max(1, len(case.source_text)), 2),
        "expected_focus": case.expected_focus,
        "change_summary": [safe_text(item, 200) for item in (preview.get("change_summary") or [])[:5]],
        "rationale_excerpt": safe_text(preview.get("rationale"), 360),
        "screenplay_structure": structure,
        "revised_excerpt": safe_screenplay_excerpt(revised, 2600),
        "latency_ms": latency_ms,
        "route_latency_ms": response.get("latency_ms"),
        "creative_task": safe_task(response.get("creative_task")),
        "provider_calls_started": response.get("provider_calls_started") is True,
        "provider_lineage": safe_lineage(response),
        "graph_mutation": response.get("graph_mutation"),
        "cost_usd": Number(response.get("cost_usd")),
    }
    write_json(run_root / f"runtime_screenplay_{case.case_id}.safe.json", summary)
    return summary


def run_shot_breakdown_case(base_url: str, project_id: str, case: CorpusCase, run_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    response = http_json(
        "POST",
        urljoin(base_url, f"projects/{project_id}/embedded-creative-actions/preview"),
        embedded_payload(case, "shot_breakdown", "dynamic_shot_breakdown"),
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    assert_embedded_llm_response(response, f"{case.case_id}.shot_breakdown")
    plan = response.get("preview", {}).get("shot_plan") or {}
    scenes = plan.get("scenes") if isinstance(plan, dict) else []
    first_scene = scenes[0] if scenes else {}
    first_shots = first_scene.get("shots") if isinstance(first_scene, dict) else []
    summary = {
        "case_id": case.case_id,
        "action_type": "shot_breakdown",
        "scene_count": len(scenes or []),
        "total_shots": int(plan.get("total_shots") or 0),
        "estimated_duration_sec": Number(plan.get("estimated_duration_sec")),
        "first_scene": safe_text(first_scene.get("title"), 160) if isinstance(first_scene, dict) else "",
        "first_shots": [
            {
                "title": safe_text(shot.get("title"), 120),
                "duration_sec": Number(shot.get("duration_sec")),
                "shot_size": safe_text(shot.get("shot_size"), 80),
                "camera_angle": safe_text(shot.get("camera_angle"), 80),
                "movement": safe_text(shot.get("movement"), 120),
                "blocking": safe_text(shot.get("blocking"), 160),
                "sound": safe_text(shot.get("sound"), 120),
                "transition": safe_text(shot.get("transition"), 80),
                "narrative_purpose": safe_text(shot.get("narrative_purpose"), 180),
            }
            for shot in (first_shots or [])[:5]
            if isinstance(shot, dict)
        ],
        "latency_ms": latency_ms,
        "route_latency_ms": response.get("latency_ms"),
        "creative_task": safe_task(response.get("creative_task")),
        "provider_calls_started": response.get("provider_calls_started") is True,
        "provider_lineage": safe_lineage(response),
        "graph_mutation": response.get("graph_mutation"),
        "cost_usd": Number(response.get("cost_usd")),
    }
    write_json(run_root / "runtime_shot_breakdown.safe.json", summary)
    return summary


def run_codex_work_strict_review(
    run_root: Path,
    runtime: dict[str, Any],
    browser_reports: list[dict[str, Any]],
    conversation_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    schema = strict_review_schema()
    digest = structured_output_schema_digest(schema)
    evidence = strict_review_evidence(runtime, browser_reports, conversation_reports)
    reviews = []
    total_latency_ms = 0.0
    for index, lens in enumerate(strict_review_lenses(), start=1):
        started = time.perf_counter()
        result = load_provider_registry().dispatch(
            "llm",
            SERVER_CODEX_SERVICE_ID,
            ProviderDispatchRequest(
                prompt=strict_review_prompt(lens, evidence, digest),
                output_dir=run_root / f"codex-work-review-{index:02d}-{lens['id']}",
                task_type=f"m6_6_codex_work_review_{lens['id']}",
                structured_output_contract_id="afs.m6_6.codex_work_strict_review.v0.1",
                structured_output_schema=schema,
                structured_output_schema_digest=digest,
                timeout_sec=90.0,
            ),
        )
        total_latency_ms += round((time.perf_counter() - started) * 1000, 2)
        structured = result.get("structured_output") if isinstance(result, dict) else None
        if not isinstance(structured, dict):
            raise AssertionError(f"strict review {lens['id']} returned no structured output")
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
                issues.append(issue(severity.upper(), f"{review['lens']}_{len(issues)+1}", safe_text(issue_text, 500)))
        if review.get("status") != "pass" or Number(review.get("score")) < 4:
            issues.append(issue("P1", f"{review['lens']}_score_or_status", f"status={review.get('status')} score={review.get('score')}"))
    report = {
        "status": "passed" if no_user_visible_issues(issues) else "failed",
        "provider_request_count": len(reviews),
        "provider": provider_summary(digest),
        "latency_ms": round(total_latency_ms, 2),
        "reviews": reviews,
        "issue_ledger": issues,
    }
    write_json(run_root / "codex_work_strict_review.safe.json", report)
    if report["status"] != "passed":
        raise AssertionError(f"Codex Work strict review failed: {issues}")
    return report


def strict_review_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["lens", "status", "score", "p0", "p1", "p2", "rationale"],
        "properties": {
            "lens": {"type": "string", "minLength": 3},
            "status": {"type": "string", "enum": ["pass", "fail"]},
            "score": {"type": "number"},
            "p0": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "p1": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "p2": {"type": "array", "maxItems": 4, "items": {"type": "string"}},
            "rationale": {"type": "string", "minLength": 20},
        },
    }


def strict_review_lenses() -> list[dict[str, str]]:
    return [
        {"id": "ux_task_visibility", "name": "UX/任务可见性", "focus": "150ms反馈、阶段诚实、取消/恢复、节点不被遮挡"},
        {"id": "screenplay_quality", "name": "专业剧本格式", "focus": "INT/EXT或中文等价、场景、动作、人物名、对白、转场、角色目标冲突变化"},
        {"id": "shot_graph", "name": "分镜候选图", "focus": "动态镜头数、景别机位运动声音转场目的、可见候选子图、Storyboard parity"},
        {"id": "graph_truth", "name": "ProductionGraph单一真相", "focus": "preview不变更、apply只改声明目标、同节点修订、显式fork、无第二truth"},
        {"id": "companion_actions", "name": "AI创作搭档动作", "focus": "真实context、问候/节点问题、命令卡、同一typed task路径、非罐头"},
        {"id": "security_cost", "name": "安全/费用/Provider诚实", "focus": "server_codex/codex_local、无secret/raw stdout、非LLM关闭、external_paid_cost_usd=0"},
    ]


def strict_review_prompt(lens: dict[str, str], evidence: dict[str, Any], schema_digest: str) -> str:
    return "\n".join([
        "你是 AFS M6.6 Gate 的独立 Codex Work 严格评审员。",
        "只根据给定安全证据评审；不要访问文件、网络、secret、图片或视频。",
        "必须尖锐：仍存在的用户可见 P0/P1/P2 填入数组；没有则空数组。",
        "status=pass 仅当该 lens 没有 P0/P1/P2 且 score>=4。",
        "不要把自动评审冒充 Owner 人工验收。",
        f"Lens: {lens['name']} / {lens['focus']}",
        f"Closed schema digest: {schema_digest}",
        "<safe_evidence>",
        json.dumps(evidence, ensure_ascii=False, sort_keys=True)[:9000],
        "</safe_evidence>",
        "返回严格 JSON。",
    ])


def strict_review_evidence(
    runtime: dict[str, Any],
    browser_reports: list[dict[str, Any]],
    conversation_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "runtime_status": runtime.get("status"),
        "provider": runtime.get("provider"),
        "graph_mutated_by_preview": runtime.get("graph_mutated_by_preview"),
        "screenplay_cases": [
            {
                "case_id": item.get("case_id"),
                "expansion_ratio": item.get("expansion_ratio"),
                "structure": item.get("screenplay_structure"),
                "task_phase": item.get("creative_task", {}).get("phase"),
                "provider_calls_started": item.get("provider_calls_started"),
                "graph_mutation": item.get("graph_mutation"),
                "excerpt": item.get("revised_excerpt"),
            }
            for item in runtime.get("screenplay_cases") or []
        ],
        "shot_breakdown_case": runtime.get("shot_breakdown_case"),
        "source_contracts": [
            "UI stores running CreativeTask before provider returns and node body keeps compact result.",
            "Right creative sidebar owns review/diff/apply/cancel; prompt bar hides while active task exists.",
            "Script revision apply preserves node id; shot breakdown apply creates candidate sequence/scene/shot subgraph.",
            "Image/video/audio/asr/vision/external_download are not authorized in this gate.",
        ],
        "browser_rounds": browser_reports,
        "real_runtime_conversation": conversation_reports,
    }


def load_browser_reports(paths: list[str]) -> list[dict[str, Any]]:
    reports = []
    for raw in paths or []:
        path = Path(raw).resolve()
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = data.get("cases") if isinstance(data.get("cases"), dict) else {}
        feedback = [Number(item.get("running_feedback_ms")) for item in cases.values()]
        node_heights = [Number(item.get("script_preview_geometry", {}).get("node_height")) for item in cases.values()]
        reports.append({
            "path": str(path),
            "status": data.get("status"),
            "round": data.get("round"),
            "P0": data.get("P0"),
            "P1": data.get("P1"),
            "P2": data.get("P2"),
            "case_count": len(cases),
            "viewports": [item.get("viewport") for item in cases.values()],
            "max_running_feedback_ms": max(feedback) if feedback else None,
            "max_node_height_px": max(node_heights) if node_heights else None,
            "checks": data.get("micro_experience_checks") or {},
            "role_matrix": data.get("role_task_completion_matrix") or {},
            "provider_dispatch_count": data.get("provider_dispatch_count"),
            "cost_usd": data.get("cost_usd"),
            "screenshot_count": len(data.get("screenshots") or {}),
        })
    return reports


def load_conversation_reports(paths: list[str]) -> list[dict[str, Any]]:
    reports = []
    for raw in paths or []:
        path = Path(raw).resolve()
        data = json.loads(path.read_text(encoding="utf-8"))
        browser = data.get("browser") if isinstance(data.get("browser"), dict) else {}
        responses = browser.get("responses") if isinstance(browser.get("responses"), list) else []
        reports.append({
            "path": str(path),
            "status": data.get("status"),
            "P0": data.get("P0"),
            "P1": data.get("P1"),
            "P2": data.get("P2"),
            "provider_request_count": data.get("provider_request_count"),
            "direct_http": {
                "message": data.get("direct_http", {}).get("message"),
                "mode": data.get("direct_http", {}).get("mode"),
                "provider_calls_started": data.get("direct_http", {}).get("provider_calls_started"),
                "latency_ms": data.get("direct_http", {}).get("latency_ms"),
                "reply_excerpt": safe_text(data.get("direct_http", {}).get("reply_excerpt"), 220),
                "provider_lineage": data.get("direct_http", {}).get("provider_lineage"),
            },
            "browser_messages": browser.get("messages") or [],
            "browser_response_count": len(responses),
            "browser_reply_excerpts": [safe_text(item.get("reply"), 220) for item in responses[:3]],
            "graph_mutated": data.get("graph_mutated"),
            "screenshots": browser.get("screenshots") or {},
            "external_paid_cost_usd": data.get("external_paid_cost_usd"),
        })
    return reports


def embedded_payload(case: CorpusCase, action_type: str, mode: str) -> dict[str, Any]:
    return {
        "action_type": action_type,
        "node_id": f"{case.case_id}_node",
        "node_type": case.node_type,
        "source_text": case.source_text,
        "mode": mode,
        "context_summary": {
            "project_name": "M6.6 可见创作任务验证",
            "selected_node_title": case.title,
            "selected_node_type": case.node_type,
            "selected_node_status": "draft",
            "section": "canvas",
            "counts": {"nodes": 1, "relations": 0},
        },
        "constraints": [
            "中文专业影视创作表达",
            "预览阶段不修改画布",
            "不要使用固定模板或空泛标题",
        ],
        "provider_service_id": SERVER_CODEX_SERVICE_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def corpus_cases() -> list[CorpusCase]:
    return [
        CorpusCase(
            case_id="short_idea_sun_wukong",
            title="很短想法：孙悟空大战猪八戒",
            node_type="text",
            source_text="孙悟空大战猪八戒。",
            expected_focus="从一句话扩写成专业剧本场景，补足目标、误会、动作和对白。",
        ),
        CorpusCase(
            case_id="dialogue_scene",
            title="对白场：棚内争执",
            node_type="script",
            source_text=(
                "内景，旧摄影棚，夜。导演林澈盯着停电后的监视器。制片人许岚拿着预算表说："
                "“再等十分钟，我们就赔不起了。”林澈回答：“不是机器坏了，是它不想让我们拍完。”"
            ),
            expected_focus="强化对白动作、角色目标冲突和旧摄影棚空间调度。",
        ),
        CorpusCase(
            case_id="multi_scene_draft",
            title="多场草稿：密闭科幻",
            node_type="script",
            source_text=(
                "第一场：飞船医务舱，冷白灯闪烁，机器人K-17发现自己的记忆模块被替换。"
                "第二场：红色警示走廊，工程师孟遥追踪一只带划痕的备用机械手。"
                "第三场：气闸外，队长要求放弃维修，孟遥坚持找出是谁伪造了事故记录。"
            ),
            expected_focus="保留三空间连续性，补足角色关系、悬念、镜头拆分依据。",
        ),
    ]


def runtime_issues(
    script_cases: list[dict[str, Any]],
    shot_case: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if graph_summary(before) != graph_summary(after):
        issues.append(issue("P0", "preview_mutated_graph", "runtime preview changed ProductionGraph"))
    for item in script_cases:
        structure = item.get("screenplay_structure") or {}
        if item.get("provider_calls_started") is not True:
            issues.append(issue("P0", f"{item['case_id']}_fake_provider", "provider call did not start"))
        if item.get("expansion_ratio", 0) < 1.25 or item.get("revised_characters", 0) < 160:
            issues.append(issue("P1", f"{item['case_id']}_weak_expansion", "screenplay revision was not materially expanded"))
        if int(structure.get("scene_count") or 0) < 1 or int(structure.get("action_blocks") or 0) < 1:
            issues.append(issue("P0", f"{item['case_id']}_not_screenplay", "typed screenplay structure is missing action scene blocks"))
        if structure.get("nonprofessional_heading_count"):
            issues.append(issue("P1", f"{item['case_id']}_nonprofessional_headings", "screenplay headings are not explicit interior/exterior scene headings"))
        if structure.get("missing_time_heading_count"):
            issues.append(issue("P1", f"{item['case_id']}_incomplete_headings", "screenplay headings must include space, location and time"))
        if structure.get("dangling_character_cue_count"):
            issues.append(issue("P1", f"{item['case_id']}_dangling_character_cues", "screenplay character cues must be followed by dialogue in the same scene"))
        if int(structure.get("character_count") or 0) >= 2 and int(structure.get("dialogue_blocks") or 0) < 1:
            issues.append(issue("P1", f"{item['case_id']}_dialogue_missing", "multi-character material lacks dialogue blocks"))
        if has_canned_marker(item.get("revised_excerpt")):
            issues.append(issue("P0", f"{item['case_id']}_canned_template", "canned optimization marker returned"))
        if item.get("graph_mutation", {}).get("mutated") is True:
            issues.append(issue("P0", f"{item['case_id']}_preview_mutated_graph", "script preview mutated graph"))
    if shot_case.get("provider_calls_started") is not True:
        issues.append(issue("P0", "shot_breakdown_fake_provider", "shot breakdown provider did not start"))
    if int(shot_case.get("total_shots") or 0) < 3:
        issues.append(issue("P1", "shot_breakdown_too_shallow", "shot breakdown produced fewer than three shots"))
    if shot_case.get("graph_mutation", {}).get("mutated") is True:
        issues.append(issue("P0", "shot_breakdown_preview_mutated_graph", "shot breakdown preview mutated graph"))
    if len(shot_case.get("first_shots") or []) < 2:
        issues.append(issue("P1", "shot_breakdown_not_inspectable", "shot breakdown has too few inspectable shot details"))
    return issues


def screenplay_structure(candidate: dict[str, Any]) -> dict[str, Any]:
    scenes = candidate.get("scenes") if isinstance(candidate.get("scenes"), list) else []
    characters = candidate.get("characters") if isinstance(candidate.get("characters"), list) else []
    action_blocks = 0
    dialogue_blocks = 0
    transition_blocks = 0
    nonprofessional_headings = 0
    missing_time_headings = 0
    dangling_character_cues = 0
    headings = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        heading = safe_text(scene.get("heading"), 120)
        headings.append(heading)
        if not (heading.startswith(("内景 -", "外景 -")) or heading.upper().startswith(("INT.", "EXT."))):
            nonprofessional_headings += 1
        if not complete_scene_heading(heading):
            missing_time_headings += 1
        scene_blocks = [block for block in (scene.get("blocks") or []) if isinstance(block, dict)]
        dangling_character_cues += count_dangling_character_cues(scene_blocks)
        for block in scene_blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "action":
                action_blocks += 1
            if block.get("type") == "dialogue":
                dialogue_blocks += 1
            if block.get("type") == "transition":
                transition_blocks += 1
    return {
        "title": safe_text(candidate.get("title"), 120),
        "version_label": safe_text(candidate.get("version_label"), 80),
        "scene_count": len(scenes),
        "character_count": len(characters),
        "action_blocks": action_blocks,
        "dialogue_blocks": dialogue_blocks,
        "transition_blocks": transition_blocks,
        "nonprofessional_heading_count": nonprofessional_headings,
        "missing_time_heading_count": missing_time_headings,
        "dangling_character_cue_count": dangling_character_cues,
        "first_headings": headings[:4],
        "logline_excerpt": safe_text(candidate.get("logline"), 240),
    }


def complete_scene_heading(heading: str) -> bool:
    text = safe_text(heading, 160).replace("—", "-").replace("－", "-")
    parts = [part.strip() for part in text.split("-") if part.strip()]
    if parts and parts[0] in {"内景", "外景"}:
        return len(parts) >= 3 and bool(parts[1]) and bool(parts[2])
    upper = text.upper()
    if upper.startswith(("INT.", "EXT.")):
        return len(parts) >= 2 and bool(parts[-1])
    return False


def count_dangling_character_cues(blocks: list[dict[str, Any]]) -> int:
    count = 0
    expecting_dialogue = False
    for block in blocks:
        block_type = str(block.get("type") or "")
        if block_type == "character":
            if expecting_dialogue:
                count += 1
            expecting_dialogue = True
        elif block_type == "parenthetical":
            if not expecting_dialogue:
                count += 1
        elif block_type == "dialogue":
            if not expecting_dialogue:
                count += 1
            expecting_dialogue = False
        elif block_type in {"action", "transition"}:
            if expecting_dialogue:
                count += 1
                expecting_dialogue = False
    if expecting_dialogue:
        count += 1
    return count


def assert_embedded_llm_response(response: dict[str, Any], label: str) -> None:
    if response.get("mode") != "llm":
        raise AssertionError(f"{label} did not return llm mode: {response.get('mode')} {response.get('safe_manifest')}")
    if response.get("provider_calls_started") is not True:
        raise AssertionError(f"{label} did not start provider")
    lineage = response.get("provider_lineage") or {}
    if lineage.get("service_id") != SERVER_CODEX_SERVICE_ID or lineage.get("provider") != "codex_local":
        raise AssertionError(f"{label} used unexpected provider lineage: {lineage}")
    if response.get("graph_mutation", {}).get("mutated") is True:
        raise AssertionError(f"{label} mutated graph during preview")
    task = response.get("creative_task") or {}
    if task.get("phase") != "preview_ready" or task.get("state") != "preview_ready":
        raise AssertionError(f"{label} did not expose preview_ready creative task: {task}")


def create_project(base_url: str, project_id: str) -> None:
    http_json(
        "POST",
        urljoin(base_url, "projects"),
        {
            "project_id": project_id,
            "project_type": "freeform_canvas_ai_copilot",
            "goal": "M6.6 real visible creative task LLM smoke",
            "status": "in_progress",
        },
    )


def graph(base_url: str, project_id: str) -> dict[str, Any]:
    return http_json("GET", urljoin(base_url, f"projects/{project_id}/m4/production-graph"))["graph"]


def http_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    opener = build_opener(ProxyHandler({}))
    data = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = Request(url, data=data, method=method, headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with opener.open(request, timeout=360) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"HTTP {method} {safe_url(url)} failed: {exc.code} {body[:600]}") from exc


def start_candidate_runtime(repo: Path, runtime_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["AFS_RUNTIME_SERVICE_ROOT"] = str(runtime_root)
    env["AFS_RUNTIME_ROOT"] = str(runtime_root)
    env["AFS_RUNTIME_SERVICE_HOST"] = "127.0.0.1"
    env["AFS_RUNTIME_SERVICE_PORT"] = str(port)
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
        cwd=repo,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )


def assert_llm_only_health(health: dict[str, Any]) -> None:
    gates = health.get("provider_gates") or {}
    if health.get("status") != "ready":
        raise AssertionError(f"candidate runtime not ready: {health.get('status')}")
    if gates.get("llm") is not True:
        raise AssertionError(f"candidate runtime LLM gate is not open: {gates}")
    for gate in ("image", "video", "audio", "asr", "vision", "external_download"):
        if gates.get(gate) is not False:
            raise AssertionError(f"candidate runtime non-LLM gate unexpectedly open: {gates}")


def final_report(
    run_root: Path,
    health: dict[str, Any],
    tiny_probe: dict[str, Any],
    runtime: dict[str, Any],
    strict_review: dict[str, Any],
    browser_reports: list[dict[str, Any]],
    conversation_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    issues = list(runtime.get("issue_ledger") or []) + list(strict_review.get("issue_ledger") or [])
    p0 = sum(1 for item in issues if item.get("severity") == "P0")
    p1 = sum(1 for item in issues if item.get("severity") == "P1")
    p2 = sum(1 for item in issues if item.get("severity") == "P2")
    request_count = int(tiny_probe.get("provider_request_count") or 0)
    request_count += int(runtime.get("provider_request_count") or 0)
    request_count += int(strict_review.get("provider_request_count") or 0)
    return {
        "artifact_type": "afs_m6_6_real_llm_visible_creative_tasks_smoke",
        "schema_version": "afs.m6_6.real_llm_visible_tasks_smoke.v0.1",
        "status": "passed" if p0 == p1 == p2 == 0 else "failed",
        "run_root": str(run_root),
        "provider": {
            "service_id": SERVER_CODEX_SERVICE_ID,
            "provider": "codex_local",
            "model_alias": LLM_MODEL,
            "reasoning_effort": LLM_REASONING_EFFORT,
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
        "runtime_visible_task_smoke": runtime,
        "browser_visible_task_rounds": browser_reports,
        "real_runtime_conversation_reports": conversation_reports,
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
        "artifact_type": "afs_m6_6_real_llm_visible_creative_tasks_smoke",
        "schema_version": "afs.m6_6.real_llm_visible_tasks_smoke.v0.1",
        "status": "technical_fail",
        "run_root": str(run_root),
        "reason": safe_text(reason, 1200),
        "provider": {
            "service_id": SERVER_CODEX_SERVICE_ID,
            "provider": "codex_local",
            "model_alias": LLM_MODEL,
            "reasoning_effort": LLM_REASONING_EFFORT,
            "external_paid_cost_usd": 0,
        },
        "non_claims": ["not_owner_acceptance", "not_business_validation"],
    }


def provider_config_payload() -> dict[str, Any]:
    descriptor = {
        "schema_version": "provider_descriptor.v0.1",
        "modality": "llm",
        "execution_mode": "sync",
        "capabilities": ["llm"],
        "account_pool_id": "server_codex_pool",
        "reference_image_slots": 0,
        "supported_aspect_ratios": ["1:1"],
        "prompt_char_limit": 18000,
        "seed_supported": False,
        "required_gate": LLM_GATE,
    }
    return {
        "schema_version": "company_provider_secrets.m6_6.local.v1",
        "accounts": {
            "server_codex_login": {
                "auth_type": "none",
                "execution_backend": "codex_exec",
                "default_models": {"llm": "server-codex-login"},
                "cli_model": LLM_MODEL,
                "cli_reasoning_effort": LLM_REASONING_EFFORT,
                "timeout_sec": 180,
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
                "required_gate": LLM_GATE,
                "cli_model": LLM_MODEL,
                "cli_reasoning_effort": LLM_REASONING_EFFORT,
                "timeout_sec": 180,
                "descriptor": descriptor,
            }
        },
    }


def apply_candidate_env(runtime_root: Path, provider_config: Path) -> dict[str, str | None]:
    keys = (
        "AFS_RUNTIME_SERVICE_ROOT",
        "AFS_RUNTIME_ROOT",
        "AFS_PROVIDER_CONFIG",
        "AFS_M6_SERVER_CODEX_OUTPUT_DIR",
        "AFS_ALLOW_REMOTE_LLM",
        "AFS_ALLOW_REMOTE_IMAGE",
        "AFS_ALLOW_REMOTE_VIDEO",
        "AFS_ALLOW_REMOTE_AUDIO",
        "AFS_ALLOW_REMOTE_ASR",
        "AFS_ALLOW_REMOTE_VISION",
        "AFS_ALLOW_EXTERNAL_DOWNLOAD",
        "AFS_EXTERNAL_DOWNLOAD",
        "AFS_AUTH_ENABLED",
        "NO_PROXY",
        "no_proxy",
    )
    previous = {key: os.environ.get(key) for key in keys}
    os.environ["AFS_RUNTIME_SERVICE_ROOT"] = str(runtime_root)
    os.environ["AFS_RUNTIME_ROOT"] = str(runtime_root)
    os.environ["AFS_PROVIDER_CONFIG"] = str(provider_config)
    os.environ["AFS_M6_SERVER_CODEX_OUTPUT_DIR"] = str(runtime_root / "provider-outputs")
    os.environ["AFS_AUTH_ENABLED"] = "false"
    os.environ[LLM_GATE] = "true"
    for key in NON_LLM_GATES:
        os.environ[key] = "false"
    os.environ["NO_PROXY"] = merge_no_proxy(os.environ.get("NO_PROXY"))
    os.environ["no_proxy"] = merge_no_proxy(os.environ.get("no_proxy"))
    return previous


def restore_env(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def merge_no_proxy(value: str | None) -> str:
    parts = [item.strip() for item in str(value or "").split(",") if item.strip()]
    for item in ("127.0.0.1", "localhost"):
        if item not in parts:
            parts.append(item)
    return ",".join(parts)


def provider_summary(schema_digest: str) -> dict[str, Any]:
    return {
        "service_id": SERVER_CODEX_SERVICE_ID,
        "provider": "codex_local",
        "model_alias": LLM_MODEL,
        "reasoning_effort": LLM_REASONING_EFFORT,
        "structured_output_schema_digest": schema_digest,
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "external_paid_cost_usd": 0,
    }


def graph_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": payload.get("version"),
        "graph_digest": payload.get("graph_digest"),
        "node_count": len(payload.get("nodes") or {}),
        "relation_count": len(payload.get("relations") or []),
    }


def safe_lineage(payload: dict[str, Any]) -> dict[str, Any]:
    lineage = payload.get("provider_lineage") if isinstance(payload.get("provider_lineage"), dict) else {}
    allowed = (
        "service_id",
        "provider",
        "model_surface",
        "request_id",
        "structured_output_contract_id",
        "structured_output_schema_digest",
        "provider_calls_started",
        "provider_raw_response_stored",
        "external_paid_cost_usd",
    )
    out = {key: lineage.get(key) for key in allowed if key in lineage}
    out["candidate_cli_model"] = LLM_MODEL
    out["candidate_reasoning_effort"] = LLM_REASONING_EFFORT
    return out


def safe_task(payload: Any) -> dict[str, Any]:
    task = payload if isinstance(payload, dict) else {}
    allowed = ("task_id", "state", "phase", "completed_phases", "action_type", "mode", "result_scope", "error_category")
    return {key: task.get(key) for key in allowed if key in task}


def safe_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def safe_screenplay_excerpt(value: Any, limit: int) -> str:
    lines = [line.rstrip() for line in str(value or "").replace("\r\n", "\n").split("\n")]
    text = "\n".join(lines).strip()
    return text[:limit]


def safe_url(value: str) -> str:
    return "/" + "/".join(Path(value).parts[-3:])


def has_canned_marker(value: Any) -> bool:
    text = str(value or "")
    return any(marker in text for marker in ("核心意图", "叙事推进", "制作优化"))


def issue(severity: str, issue_id: str, evidence: str) -> dict[str, str]:
    return {"severity": severity, "issue": issue_id, "evidence": evidence}


def no_user_visible_issues(issues: list[dict[str, str]]) -> bool:
    return not [item for item in issues if item.get("severity") in {"P0", "P1", "P2"}]


def Number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def default_run_root() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return str(DEFAULT_EVIDENCE_BASE / f"{stamp}-real-llm-visible-tasks")


if __name__ == "__main__":
    raise SystemExit(main())
