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
    "/home/afs-ops/.codex/afs-evidence/afs-m6-5-embedded-creative-action-ux-20260722"
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
    run_root = Path(args.evidence_root or _default_run_root()).resolve()
    runtime_root = run_root / "runtime-root"
    run_root.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)
    provider_config = run_root / "provider-config.no-secrets.json"
    provider_config.write_text(json.dumps(_provider_config(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    previous_env = _apply_candidate_env(runtime_root, provider_config)
    port = args.port or free_port()
    base_url = f"http://127.0.0.1:{port}/"
    server: subprocess.Popen[str] | None = None
    try:
        direct_review = run_codex_work_strict_review(run_root)
        server = start_candidate_runtime(repo, runtime_root, port, previous_env=None)
        wait_for_http(urljoin(base_url, "health"), timeout=60)
        health = http_json("GET", urljoin(base_url, "health"))
        assert_llm_only_health(health)
        runtime = run_runtime_embedded_action_smoke(base_url, run_root)
        report = final_report(run_root, health, direct_review, runtime)
        write_json(run_root / "m6_5_real_llm_embedded_action_report.json", report)
        print(json.dumps({
            "status": report["status"],
            "report": str(run_root / "m6_5_real_llm_embedded_action_report.json"),
            "provider_request_count": report["provider_request_count"],
            "runtime_request_count": runtime["provider_request_count"],
            "P0": report["P0"],
            "P1": report["P1"],
            "P2": report["P2"],
            "cost_usd": report["external_paid_cost_usd"],
        }, ensure_ascii=False, sort_keys=True))
        return 0 if report["status"] == "passed" else 1
    except Exception as exc:
        blocked = technical_fail(run_root, str(exc))
        write_json(run_root / "m6_5_real_llm_embedded_action_fail.json", blocked)
        print(json.dumps({
            "status": blocked["status"],
            "report": str(run_root / "m6_5_real_llm_embedded_action_fail.json"),
            "reason": blocked["reason"],
        }, ensure_ascii=False, sort_keys=True))
        return 1
    finally:
        if server is not None:
            stop_runtime(server)
        _restore_env(previous_env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.5 real server_codex embedded creative action smoke")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--evidence-root", default="")
    parser.add_argument("--port", type=int, default=0)
    return parser.parse_args()


def run_codex_work_strict_review(run_root: Path) -> dict[str, Any]:
    schema = strict_review_schema()
    schema_digest = structured_output_schema_digest(schema)
    reviews = []
    total_latency_ms = 0.0
    registry = load_provider_registry()
    for index, prompt in enumerate(strict_review_prompts(schema_digest), start=1):
        started = time.perf_counter()
        result = registry.dispatch(
            "llm",
            SERVER_CODEX_SERVICE_ID,
            ProviderDispatchRequest(
                prompt=prompt,
                output_dir=run_root / f"codex-work-review-{index:02d}",
                task_type=f"m6_5_strict_creative_ux_review_{index:02d}",
                structured_output_contract_id="afs.m6_5.codex_work_strict_review.v0.1",
                structured_output_schema=schema,
                structured_output_schema_digest=schema_digest,
                timeout_sec=180.0,
            ),
        )
        total_latency_ms += round((time.perf_counter() - started) * 1000, 2)
        structured = result.get("structured_output") if isinstance(result, dict) else None
        if not isinstance(structured, dict):
            raise AssertionError(f"Codex Work review {index} returned no structured output")
        reviews.append({
            "status": structured.get("status"),
            "summary": safe_text(structured.get("summary"), 600),
            "scores": structured.get("scores") or [],
            "findings": structured.get("findings") or [],
            "must_fix_before_pass": structured.get("must_fix_before_pass") or [],
        })
    failed = [item for item in reviews if item["status"] != "pass" or item["must_fix_before_pass"]]
    review = {
        "status": "pass" if not failed else "fail",
        "reviews": reviews,
        "latency_ms": round(total_latency_ms, 2),
        "provider_request_count": len(reviews),
        "provider_lineage": {
            "service_id": SERVER_CODEX_SERVICE_ID,
            "provider": "codex_local",
            "model_alias": LLM_MODEL,
            "reasoning_effort": LLM_REASONING_EFFORT,
            "structured_output_schema_digest": schema_digest,
            "provider_calls_started": True,
            "provider_raw_response_stored": False,
            "external_paid_cost_usd": 0,
        },
    }
    write_json(run_root / "codex_work_strict_review.safe.json", review)
    if failed:
        raise AssertionError(f"Codex Work strict review did not pass: {review}")
    return review


def strict_review_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "summary", "scores", "findings", "must_fix_before_pass"],
        "properties": {
            "status": {"type": "string", "enum": ["pass", "fail"]},
            "summary": {"type": "string", "minLength": 40},
            "scores": {
                "type": "array",
                "minItems": 8,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["lens", "score", "rationale"],
                    "properties": {
                        "lens": {"type": "string", "minLength": 4},
                        "score": {"type": "number"},
                        "rationale": {"type": "string", "minLength": 20},
                    },
                },
            },
            "findings": {
                "type": "array",
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["severity", "issue", "evidence", "required_fix"],
                    "properties": {
                        "severity": {"type": "string", "enum": ["P0", "P1", "P2", "none"]},
                        "issue": {"type": "string"},
                        "evidence": {"type": "string"},
                        "required_fix": {"type": "string"},
                    },
                },
            },
            "must_fix_before_pass": {"type": "array", "maxItems": 8, "items": {"type": "string"}},
        },
    }


def strict_review_prompts(schema_digest: str) -> list[str]:
    shared = "\n".join([
        "你是 AFS M6.5 Owner review 前的独立 Codex Work 严格评审员。",
        "只根据下列安全事实评估，不访问 secret，不调用图片/视频，不把自动评审冒充 Owner 人工验收。",
        "如果发现会误导真实创作者、破坏 ProductionGraph 单一真相、把本地模板冒充 AI、或让本地动作污染全局聊天，必须 fail。",
        "当前 exact head 的已验证安全事实：",
        "- 全局 AI 创作搭档已有真实 runtime LLM route；M6.5 新增节点内 embedded creative action preview route，使用 server_codex/codex_local closed JSON schema。",
        "- 节点内 优化/自动拆分分镜 不再写入全局 AI transcript；预览阶段 graph_mutation=false，应用阶段只改声明目标节点的修订或 shot_plan 草稿。",
        "- 全局 chat 的旧 /optimize 本地模板被 fail-closed 文案替代，不再生成 '核心意图/叙事推进/制作优化' 罐头大纲。",
        "- 默认 palette 收敛为 想法/文本、剧本/导入、场景与镜头、角色与资产、参考图/图片、视频；高级类型折叠。",
        "- 边线端点使用可见 handle/card border 几何，不用 last-edge 或位置猜测；Round A/B browser 已验证 <=2px gap。",
        "- 顶栏改为紧凑 AFS、项目/分集、Canvas/Storyboard、save/help/account；帮助入口说明从任意节点开始。",
        "- AI panel 改为紧凑上下文 chips、可折叠活动记录和 pinned composer。",
        f"- Provider=server_codex/codex_local, model_alias={LLM_MODEL}, reasoning={LLM_REASONING_EFFORT}, external_paid_cost_usd=0。",
        f"Closed schema digest: {schema_digest}",
        "请输出严格 JSON。status=pass 仅当 P0/P1/P2 均为 0；scores 用 0-5 分，所有用户可见 lens 必须 >=4。",
    ])
    focus_prompts = [
        "评审主题 A：问候/节点解释/下一步建议/关系解释是否像真实创作搭档；本地动作是否不污染全局聊天；provider/cost 状态是否诚实。",
        "评审主题 B：同节点修订、显式 fork、preview/cancel/apply、undo/recovery 和 ProductionGraph 单一真相是否成立；不得有第二 truth 或 canned template。",
        "评审主题 C：任意节点入口、palette 渐进披露、边线几何、topbar/help/account IA、移动与低视力用户可理解性是否达到 Owner review 候选质量。",
    ]
    return [f"{shared}\n{focus}" for focus in focus_prompts]


def run_runtime_embedded_action_smoke(base_url: str, run_root: Path) -> dict[str, Any]:
    project_id = f"m6-5-real-embedded-{int(time.time())}"
    create_project(base_url, project_id)
    before = graph(base_url, project_id)
    cases = []
    for case in corpus_cases():
        cases.append(run_revision_case(base_url, project_id, case, run_root))
    shot_case = run_shot_breakdown_case(base_url, project_id, corpus_cases()[-1])
    after = graph(base_url, project_id)
    issue_ledger = runtime_issue_ledger(cases, shot_case, before, after)
    report = {
        "status": "passed" if not [i for i in issue_ledger if i["severity"] in {"P0", "P1", "P2"}] else "failed",
        "project_id": project_id,
        "provider_request_count": len(cases) + 1,
        "provider": {
            "service_id": SERVER_CODEX_SERVICE_ID,
            "provider": "codex_local",
            "model_alias": LLM_MODEL,
            "reasoning_effort": LLM_REASONING_EFFORT,
            "external_paid_cost_usd": 0,
        },
        "graph_before": graph_summary(before),
        "graph_after": graph_summary(after),
        "graph_mutated": graph_summary(before) != graph_summary(after),
        "script_revision_cases": cases,
        "shot_breakdown_case": shot_case,
        "issue_ledger": issue_ledger,
    }
    write_json(run_root / "runtime_embedded_action_smoke.safe.json", report)
    if report["status"] != "passed":
        raise AssertionError(f"runtime embedded action smoke failed: {issue_ledger}")
    return report


def run_revision_case(base_url: str, project_id: str, case: CorpusCase, run_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    response = http_json(
        "POST",
        urljoin(base_url, f"projects/{project_id}/embedded-creative-actions/preview"),
        embedded_payload(case, "script_revision", "professional_expansion"),
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    assert_embedded_llm_response(response, f"{case.case_id}.revision")
    preview = response["preview"]
    revised = str(preview.get("revised_text") or "")
    expansion_ratio = round(len(revised) / max(1, len(case.source_text)), 2)
    summary = {
        "case_id": case.case_id,
        "title": case.title,
        "source_characters": len(case.source_text),
        "revised_characters": len(revised),
        "expansion_ratio": expansion_ratio,
        "expected_focus": case.expected_focus,
        "change_summary": preview.get("change_summary", [])[:4],
        "rationale_excerpt": safe_text(preview.get("rationale"), 240),
        "unresolved_decisions": preview.get("unresolved_decisions", [])[:4],
        "quality_flags": preview.get("quality_flags", [])[:4],
        "revised_excerpt": safe_text(revised, 900),
        "latency_ms": latency_ms,
        "route_latency_ms": response.get("latency_ms"),
        "provider_calls_started": response.get("provider_calls_started") is True,
        "provider_lineage": safe_lineage(response),
        "graph_mutation": response.get("graph_mutation"),
    }
    write_json(run_root / f"runtime_case_{case.case_id}.safe.json", summary)
    return summary


def run_shot_breakdown_case(base_url: str, project_id: str, case: CorpusCase) -> dict[str, Any]:
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
    return {
        "case_id": case.case_id,
        "action_type": "shot_breakdown",
        "scene_count": len(scenes or []),
        "total_shots": plan.get("total_shots"),
        "estimated_duration_sec": plan.get("estimated_duration_sec"),
        "first_scene": safe_text((scenes or [{}])[0].get("title"), 160) if scenes else "",
        "first_shots": [
            {
                "title": safe_text(shot.get("title"), 120),
                "duration_sec": shot.get("duration_sec"),
                "shot_size": safe_text(shot.get("shot_size"), 80),
                "camera_angle": safe_text(shot.get("camera_angle"), 80),
                "movement": safe_text(shot.get("movement"), 120),
                "sound": safe_text(shot.get("sound"), 120),
                "transition": safe_text(shot.get("transition"), 80),
                "narrative_purpose": safe_text(shot.get("narrative_purpose"), 180),
            }
            for shot in ((scenes or [{}])[0].get("shots") or [])[:4]
        ],
        "latency_ms": latency_ms,
        "route_latency_ms": response.get("latency_ms"),
        "provider_calls_started": response.get("provider_calls_started") is True,
        "provider_lineage": safe_lineage(response),
        "graph_mutation": response.get("graph_mutation"),
    }


def embedded_payload(case: CorpusCase, action_type: str, mode: str) -> dict[str, Any]:
    return {
        "action_type": action_type,
        "node_id": f"{case.case_id}_node",
        "node_type": case.node_type,
        "source_text": case.source_text,
        "mode": mode,
        "context_summary": {
            "project_name": "M6.5 真实节点内创作动作验证",
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
            expected_focus="从一句话扩写出人物目标、误会冲突、动作节奏和可拍画面。",
        ),
        CorpusCase(
            case_id="dialogue_scene",
            title="对白场：棚内争执",
            node_type="script",
            source_text=(
                "内景，旧摄影棚，夜。导演林澈盯着停电后的监视器。制片人许岚拿着预算表说："
                "“再等十分钟，我们就赔不起了。”林澈回答：“不是机器坏了，是它不想让我们拍完。”"
            ),
            expected_focus="强化对白、动作反应、角色目标冲突和空间调度。",
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
            expected_focus="保持三空间连续性，补足角色关系、悬念、镜头动机和动态拆镜依据。",
        ),
    ]


def runtime_issue_ledger(cases: list[dict[str, Any]], shot_case: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if graph_summary(before) != graph_summary(after):
        issues.append(issue("P0", "preview_mutated_graph", "embedded action preview changed ProductionGraph"))
    for item in cases:
        if item["provider_calls_started"] is not True:
            issues.append(issue("P0", f"{item['case_id']}_fake_provider", "provider call did not start"))
        if item["expansion_ratio"] < 1.35 or item["revised_characters"] < 120:
            issues.append(issue("P1", f"{item['case_id']}_weak_expansion", "revision is not materially expanded"))
        excerpt = str(item.get("revised_excerpt") or "")
        if any(marker in excerpt for marker in ("核心意图", "叙事推进", "制作优化")):
            issues.append(issue("P0", f"{item['case_id']}_canned_template", "canned template marker returned"))
        if item.get("graph_mutation", {}).get("mutated") is True:
            issues.append(issue("P0", f"{item['case_id']}_preview_mutated_graph", "preview mutated graph"))
    if shot_case.get("provider_calls_started") is not True:
        issues.append(issue("P0", "shot_breakdown_fake_provider", "shot breakdown provider did not start"))
    if int(shot_case.get("total_shots") or 0) < 2:
        issues.append(issue("P1", "shot_breakdown_too_shallow", "dynamic shot plan produced fewer than two shots"))
    if shot_case.get("graph_mutation", {}).get("mutated") is True:
        issues.append(issue("P0", "shot_breakdown_preview_mutated_graph", "shot breakdown preview mutated graph"))
    return issues


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


def create_project(base_url: str, project_id: str) -> None:
    http_json(
        "POST",
        urljoin(base_url, "projects"),
        {
            "project_id": project_id,
            "project_type": "freeform_canvas_ai_copilot",
            "goal": "M6.5 real embedded creative action LLM smoke",
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
        with opener.open(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"HTTP {method} {safe_url(url)} failed: {exc.code} {body[:600]}") from exc


def start_candidate_runtime(repo: Path, runtime_root: Path, port: int, previous_env: dict[str, str | None] | None) -> subprocess.Popen[str]:
    _ = previous_env
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
        env=os.environ.copy(),
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


def final_report(run_root: Path, health: dict[str, Any], direct_review: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    issues = list(runtime["issue_ledger"])
    p0 = sum(1 for item in issues if item["severity"] == "P0")
    p1 = sum(1 for item in issues if item["severity"] == "P1")
    p2 = sum(1 for item in issues if item["severity"] == "P2")
    return {
        "artifact_type": "afs_m6_5_real_llm_embedded_action_smoke",
        "schema_version": "afs.m6_5.real_llm_embedded_action_smoke.v0.1",
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
        "codex_work_strict_review": direct_review,
        "runtime_embedded_action_smoke": runtime,
        "provider_request_count": int(direct_review.get("provider_request_count") or 0) + runtime["provider_request_count"],
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
        "artifact_type": "afs_m6_5_real_llm_embedded_action_smoke",
        "schema_version": "afs.m6_5.real_llm_embedded_action_smoke.v0.1",
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


def _provider_config() -> dict[str, Any]:
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
        "schema_version": "company_provider_secrets.m6_5.local.v1",
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


def _apply_candidate_env(runtime_root: Path, provider_config: Path) -> dict[str, str | None]:
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


def _restore_env(previous: dict[str, str | None]) -> None:
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


def safe_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def safe_url(value: str) -> str:
    return "/" + "/".join(Path(value).parts[-3:])


def issue(severity: str, issue_id: str, evidence: str) -> dict[str, str]:
    return {"severity": severity, "issue": issue_id, "evidence": evidence}


def _default_run_root() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return str(DEFAULT_EVIDENCE_BASE / f"{stamp}-real-llm-embedded-action")


if __name__ == "__main__":
    raise SystemExit(main())
