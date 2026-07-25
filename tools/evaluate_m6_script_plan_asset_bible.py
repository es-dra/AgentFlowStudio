"""Independent evaluator for the M6 script-plan-asset-Bible slice."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def evaluate(root: Path) -> dict:
    findings: list[dict[str, str]] = []
    runtime = root / "apps/api/runtime_m6_script_plan_asset_bible.py"
    server_codex = root / "apps/api/runtime_m6_server_codex_planner.py"
    adapter = root / "apps/api/runtime_film_production_graph.py"
    service = root / "apps/api/runtime_service.py"
    client = root / "apps/studio/src/runtime-client.js"
    lifecycle = root / "apps/studio/src/agent-chat-lifecycle.js"
    panel = root / "apps/studio/src/agent-chat-panel.js"
    shell = root / "apps/studio/src/product-shell.js"
    projection = root / "apps/studio/src/production-graph-workspace-projection.js"
    styles = root / "apps/studio/styles/product-shell.css"
    tests = root / "tests/test_runtime_m6_script_plan_asset_bible.py"
    for path in (runtime, server_codex, adapter, service, client, lifecycle, panel, shell, projection, styles, tests):
        if not path.exists():
            findings.append({"severity": "P0", "issue": f"missing required M6 file: {path.relative_to(root)}"})
    if findings:
        return _report(findings)

    runtime_text = runtime.read_text(encoding="utf-8")
    server_codex_text = server_codex.read_text(encoding="utf-8")
    adapter_text = adapter.read_text(encoding="utf-8")
    service_text = service.read_text(encoding="utf-8")
    client_text = client.read_text(encoding="utf-8")
    lifecycle_text = lifecycle.read_text(encoding="utf-8")
    panel_text = panel.read_text(encoding="utf-8")
    shell_text = shell.read_text(encoding="utf-8")
    projection_text = projection.read_text(encoding="utf-8")
    styles_text = styles.read_text(encoding="utf-8")
    tests_text = tests.read_text(encoding="utf-8")

    checks = [
        ("P0", "M6 routes not registered", "register_runtime_m6_script_plan_asset_bible_routes(app, store, auth)" in service_text),
        ("P0", "M6 confirm does not append through ProductionGraph", "graph_store.append" in runtime_text and "compile_film_candidate" in runtime_text),
        ("P0", "M6 preview missing professional contract schema", "afs.m6.script_plan_asset_bible.v0.1" in runtime_text),
        ("P0", "M6 candidate validation missing", "validate_m6_candidate" in runtime_text and "fixed equal durations" in runtime_text),
        ("P0", "knowledge layering missing rollback or promotion gate", all(token in runtime_text for token in ("promotion_state", "rollback_ref", "candidate_not_promoted", "KNOWLEDGE_LAYERS"))),
        ("P0", "six review roles missing", all(role in runtime_text for role in (
            "screenwriter", "director_storyboard", "cinematographer", "asset_continuity",
            "production_feasibility", "engineering_lineage_knowledge_safety",
        ))),
        ("P0", "asset Bible confirmation gate missing", "asset_bible" in runtime_text and "pending_confirmation" in runtime_text),
        ("P0", "canonical scope review missing", "M6_SCOPE_REVIEW_SCHEMA_VERSION" in runtime_text and "build_m6_scope_review" in runtime_text and "fail_closed" in runtime_text),
        ("P0", "production aids can still contaminate prop refs", "prop_refs must contain only canonical prop assets" in runtime_text and "production aids cannot appear in prop_refs" in runtime_text),
        ("P0", "server Codex adapter does not fail closed on canonical drift", "canonical scope drift failed closed" in server_codex_text and "m6_source_canonical_scope" in server_codex_text),
        ("P0", "film adapter drops M6 professional metadata", "_film_metadata" in adapter_text and "shot_size" not in adapter_text),
        ("P0", "film workspace still merges aids into props", "production_aids" in adapter_text and 'get("kind") == "prop"' in adapter_text),
        ("P0", "frontend M6 route client missing", "previewM6ScriptPlanAssetBible" in client_text and "confirmM6ScriptPlanAssetBible" in client_text),
        ("P0", "Agent Chat M6 command missing", "stageM6ScriptPlanCandidateCommand" in lifecycle_text and "m6_script_plan_asset_bible" in lifecycle_text),
        ("P0", "Agent Chat confirmation card lacks itemized scope impact", "scope_impact" in lifecycle_text and "agent-m6-scope-impact" in panel_text and "范围影响清单" in panel_text),
        ("P0", "M6 path bypasses fixed right Agent Chat", "buildAgentChat" in shell_text and "stageM6ScriptPlanCandidateCommand" in shell_text),
        ("P0", "M6 creates a second shell/card stack", not any(token in shell_text for token in ("m6-card-stack", "m6-sequence-layout", "return buildGraphSequenceWorkspace"))),
        ("P1", "M6 planning input lacks responsive CSS", "m6-script-plan-entry" in styles_text and "grid-template-columns: 1fr" in styles_text),
        ("P1", "M6 tests do not attack fixed profiles", "fixed equal durations" in tests_text and "4x15" in tests_text and "10x6" in tests_text),
        ("P1", "M6 tests do not attack canonical drift", "scope_drift_fails_closed" in tests_text and "prop_refs" in tests_text),
    ]
    for severity, issue, passed in checks:
        if not passed:
            findings.append({"severity": severity, "issue": issue})

    try:
        import sys

        sys.path.insert(0, str(root))
        from apps.api.runtime_m6_script_plan_asset_bible import build_m6_script_plan_asset_bible, m6_source_canonical_scope

        cases = [_case_one(), _case_two(), _case_three()]
        previews = [build_m6_script_plan_asset_bible(f"eval-{index}", {"source_kind": "script", "source_text": text}) for index, text in enumerate(cases, start=1)]
        shot_counts = [len(item["candidate"]["shots"]) for item in previews]
        if len(set(shot_counts)) < 2:
            findings.append({"severity": "P0", "issue": "controlled corpora do not produce content-varying shot counts"})
        for index, preview in enumerate(previews):
            candidate = preview["candidate"]
            source_scope = m6_source_canonical_scope(cases[index])
            if [row["display_name"] for row in candidate["characters"]] != source_scope["characters"]:
                findings.append({"severity": "P0", "issue": "controlled corpus changed canonical character names"})
            if [row["name"] for row in candidate["scenes"]] != source_scope["scenes"]:
                findings.append({"severity": "P0", "issue": "controlled corpus changed canonical scene names"})
            prop_assets = [row for row in candidate["assets"] if row.get("kind") == "prop"]
            aid_assets = [row for row in candidate["assets"] if row.get("kind") in {"closeup", "reference_set", "style"}]
            if [row["name"] for row in prop_assets] != source_scope["props"]:
                findings.append({"severity": "P0", "issue": "controlled corpus changed canonical prop names"})
            if set(candidate.get("asset_bible", {}).get("prop_refs", [])) != {row["asset_id"] for row in prop_assets}:
                findings.append({"severity": "P0", "issue": "controlled corpus prop refs include non-props or miss canonical props"})
            if set(candidate.get("asset_bible", {}).get("production_aid_refs", [])) != {row["asset_id"] for row in aid_assets}:
                findings.append({"severity": "P0", "issue": "controlled corpus production aid refs incomplete"})
            if candidate.get("m6_scope_review", {}).get("fail_closed", {}).get("status") != "pass":
                findings.append({"severity": "P0", "issue": "controlled corpus scope review did not pass"})
            durations = [float(shot["duration_seconds"]) for shot in candidate["shots"]]
            if len(set(durations)) == 1:
                findings.append({"severity": "P0", "issue": "controlled corpus produced fixed equal durations"})
            if not candidate.get("asset_bible", {}).get("reference_set_refs"):
                findings.append({"severity": "P1", "issue": "controlled corpus missing reference set refs"})
            if preview.get("provider_dispatch_count") != 0 or preview.get("cost_usd") != 0:
                findings.append({"severity": "P0", "issue": "M6 preview reports provider dispatch or cost"})
    except Exception as exc:  # pragma: no cover - evaluator output captures the failure.
        findings.append({"severity": "P0", "issue": f"M6 evaluator live preview failed: {exc}"})

    return _report(findings)


def _report(findings: list[dict[str, str]]) -> dict:
    p0 = sum(item["severity"] == "P0" for item in findings)
    p1 = sum(item["severity"] == "P1" for item in findings)
    return {
        "verdict": "PASS" if not findings else "FAIL",
        "P0": p0,
        "P1": p1,
        "findings": findings,
        "provider_dispatch_count": 0,
        "cost_usd": 0,
        "non_claims": [
            "not_provider_smoke",
            "not_generated_media_qa",
            "not_creative_qa",
            "not_owner_acceptance",
            "not_business_validation",
        ],
    }


def _case_one() -> str:
    return """
角色：林澈、唐予。场景：夜晚旧剪辑室、清晨屋顶。道具：场记板、旧镜头。特写：手背伤痕。
风格：克制写实。时间：夜晚到清晨。光线：屏幕冷光与晨光。季节：初秋。连续性：旧镜头始终在唐予手边。
林澈盯着断帧说“这一秒还在，结尾就不是谎言”。唐予要求他给出能拍的重做方案。两人上到屋顶，林澈承认删错素材。唐予把红色标记改成新的拍摄任务。
"""


def _case_two() -> str:
    return """
角色：米拉、陶、阿衡。场景：傍晚观测台、雨后信号室、地下水泵间。道具：铜色罗盘、裂开的玻璃杯、备用电池。
外观：米拉短发银灰外套；陶黑色雨衣；阿衡戴旧耳机。时间：傍晚到深夜。光线：橙光、设备绿光、手电硬光。季节：雨季。连续性：铜色罗盘每场都有明确位置。
米拉校准镜头时信号突然偏移。陶在信号室打开备用电池。阿衡听见水泵间旧广播。三人沿水声进入地下。罗盘倒转。陶读出最后呼救。阿衡承认当年没有上报。米拉把镜头留在三人的沉默上。
"""


def _case_three() -> str:
    return """
角色：许静、卫南。场景：冬季美术馆长廊、封闭修复室。道具：白手套、破损画框。特写：画布边缘的蓝色颜料。
目标：许静要证明修复记录被伪造。冲突：卫南必须保护展览开幕。关系：师徒从回避到正面对话。变化：卫南承认自己曾经签过错误记录。
许静在长廊停下脚步，听见修复室里传来刮刀声。卫南拦住她，说“现在进去，展览就完了”。许静戴上白手套，指出画框背面的日期。卫南沉默后打开修复室灯，允许她拍下蓝色颜料的边缘。
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    report = evaluate(Path(args.root).resolve())
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
