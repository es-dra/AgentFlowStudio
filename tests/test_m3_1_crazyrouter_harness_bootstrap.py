from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pytest

from tools import build_m3_1_crazyrouter_bootstrap_bundle as bundle_builder
from tools import m3_1_crazyrouter_provider_harness as harness
from tools.evaluate_m3_1_crazyrouter_security import evaluate as evaluate_security


def _provider_config(tmp_path: Path) -> Path:
    path = tmp_path / "providers.local.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "company_provider_secrets.local.v2",
                "accounts": {
                    "crazyrouter_m3_1": {
                        "auth_type": "bearer_env",
                        "base_url": "https://api.crazyrouter.com/v1",
                        "api_key_env": "CRAZYROUTER_API_KEY",
                        "default_models": {"llm": "qwen-plus"},
                    }
                },
                "account_pools": {
                    "creative_script_planner_pool": {
                        "accounts": [
                            {
                                "account_id": "crazyrouter_m3_1",
                                "service_id": "creative_script_planner",
                                "credential_env": "CRAZYROUTER_API_KEY",
                                "enabled_capabilities": ["llm"],
                                "enabled": True,
                                "priority": 10,
                                "weight": 1,
                                "concurrency_limit": 1,
                                "health_state": "unknown",
                            }
                        ]
                    }
                },
                "services": {
                    "creative_script_planner": {
                        "provider": "openai_compatible",
                        "account_ref": "crazyrouter_m3_1",
                        "capability": "llm",
                        "required_gate": "AFS_ALLOW_REMOTE_LLM",
                        "model": "qwen-plus",
                        "temperature": 0.2,
                        "max_completion_tokens": 6000,
                        "descriptor": {
                            "schema_version": "provider_descriptor.v0.1",
                            "modality": "llm",
                            "execution_mode": "sync",
                            "capabilities": ["llm"],
                            "account_pool_id": "creative_script_planner_pool",
                            "reference_image_slots": 0,
                            "supported_aspect_ratios": ["1:1"],
                            "prompt_char_limit": 20000,
                            "seed_supported": False,
                            "required_gate": "AFS_ALLOW_REMOTE_LLM",
                        },
                        "m3_1_contract": {
                            "purpose": "bounded_creative_script_planning_text_gate",
                            "structured_output_json": True,
                            "schema_version": harness.SCHEMA_VERSION,
                            "input_token_budget": 8000,
                            "max_completion_tokens": 6000,
                            "context_limit_basis": "conservative token_budget descriptor pending live provider metadata preflight; fail closed on provider context error",
                            "hard_gates": {
                                "llm": True,
                                "image": False,
                                "video": False,
                                "audio": False,
                                "asr": False,
                                "vision": False,
                                "external_download": False,
                            },
                        },
                    },
                    "prompt_optimizer": {
                        "provider": "openai_compatible",
                        "account_ref": "crazyrouter_m3_1",
                        "capability": "llm",
                        "required_gate": "AFS_ALLOW_REMOTE_LLM",
                        "model": "qwen-plus",
                        "descriptor": {
                            "schema_version": "provider_descriptor.v0.1",
                            "modality": "llm",
                            "execution_mode": "sync",
                            "capabilities": ["llm"],
                            "account_pool_id": "creative_script_planner_pool",
                            "reference_image_slots": 0,
                            "supported_aspect_ratios": ["1:1"],
                            "prompt_char_limit": 5000,
                            "seed_supported": False,
                            "required_gate": "AFS_ALLOW_REMOTE_LLM",
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _open_llm_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("CRAZYROUTER_API_KEY", "fake-secret-for-test")
    for name in harness.NON_LLM_GATES:
        monkeypatch.setenv(name, "false")


def test_budget_enforces_request_count_and_cost_stop() -> None:
    budget = harness.BudgetTracker(max_requests=2, max_total_usd=5.0, min_estimated_request_cost_usd=2.5)

    assert budget.reserve_next(prompt_chars=100, output_token_cap=100) == 2.5
    assert budget.reserve_next(prompt_chars=100, output_token_cap=100) == 2.5
    with pytest.raises(harness.HarnessBlocked, match="request_count_limit"):
        budget.reserve_next(prompt_chars=100, output_token_cap=100)

    cost_budget = harness.BudgetTracker(max_requests=8, max_total_usd=4.0, min_estimated_request_cost_usd=2.5)
    cost_budget.reserve_next(prompt_chars=100, output_token_cap=100)
    with pytest.raises(harness.HarnessBlocked, match="estimated_cost"):
        cost_budget.reserve_next(prompt_chars=100, output_token_cap=100)


def test_load_pinned_runtime_requires_host_model_and_non_llm_gates(tmp_path, monkeypatch) -> None:
    config = _provider_config(tmp_path)
    _open_llm_gate(monkeypatch)

    runtime = harness.load_pinned_provider_runtime(
        provider_config=config,
        service_id="creative_script_planner",
        expected_host="api.crazyrouter.com",
        expected_model="qwen-plus",
    )
    assert runtime.public_summary()["host"] == "api.crazyrouter.com"
    assert runtime.public_summary()["model"] == "qwen-plus"
    assert runtime.public_summary()["service_id"] == "creative_script_planner"
    assert runtime.public_summary()["prompt_char_limit"] >= 12000
    assert runtime.public_summary()["structured_output_json"] is True
    assert runtime.public_summary()["credential_name_recorded"] is False

    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    with pytest.raises(harness.HarnessBlocked, match="non_llm_gate_open:image"):
        harness.load_pinned_provider_runtime(
            provider_config=config,
            service_id="creative_script_planner",
            expected_host="api.crazyrouter.com",
            expected_model="qwen-plus",
        )


def test_prompt_optimizer_is_rejected_for_m3_1_contract(tmp_path, monkeypatch) -> None:
    config = _provider_config(tmp_path)
    _open_llm_gate(monkeypatch)

    with pytest.raises(harness.HarnessBlocked, match="prompt_optimizer_short_context_service_not_allowed"):
        harness.load_pinned_provider_runtime(
            provider_config=config,
            service_id="prompt_optimizer",
            expected_host="api.crazyrouter.com",
            expected_model="qwen-plus",
        )


def test_prompt_uses_only_new_idea_briefs_and_scoped_knowledge() -> None:
    prompt = harness.build_prompt(harness.STAGE_SPECS[0], prior_outputs={}, repair_context=None)
    for forbidden in harness.FORBIDDEN_STATIC_BASELINE_TERMS:
        assert forbidden not in prompt
    payload = json.loads(prompt)
    assert payload["idea_brief"]["title"] == "借伞处"
    assert 0 < len(payload["knowledge_refs"]) < 8
    assert payload["semantic_prior_context"]["included"] == {}
    assert payload["semantic_prior_context"]["semantic_closure"]["contract_closed"] is True
    assert "truncated_json" not in prompt


def test_semantic_prior_context_preserves_downstream_ids_and_reasons() -> None:
    script_output = _fake_provider_response(
        harness.build_prompt(harness.STAGE_SPECS[0], prior_outputs={}, repair_context=None)
    )["choices"][0]["message"]["content"]
    script = json.loads(script_output)
    spec = harness.STAGE_SPECS[1]

    semantic = harness.build_semantic_prior_context(spec, {"case_a_script": script})

    assert semantic["semantic_closure"]["contract_closed"] is True
    preserved = semantic["semantic_closure"]["preserved_required_semantics"]
    assert preserved["characters"]
    assert preserved["scenes"]
    assert semantic["included"]["case_a_script"]["included_reason"]
    assert isinstance(semantic["excluded"], list)
    assert "truncated_json" not in json.dumps(semantic, ensure_ascii=False)


def test_artifact_writer_uses_0600_and_rejects_secret_like_content(tmp_path) -> None:
    writer = harness.ArtifactWriter(tmp_path / "artifacts")
    path = writer.write_json("safe/report.json", {"status": "ok", "credential_recorded": False})

    if os.name != "nt":
        assert oct(path.stat().st_mode & 0o777) == "0o600"
        assert oct(path.parent.stat().st_mode & 0o777) == "0o700"
    else:
        assert path.is_file()
        assert path.parent.is_dir()
    with pytest.raises(harness.HarnessBlocked, match="secret_like"):
        writer.write_json("bad/report.json", {"Authorization": "Bearer abcdefghijklmnopqrstuvwxyz"})


def _fake_provider_response(prompt: str) -> dict:
    request = json.loads(prompt)
    case_id = request["case_id"]
    stage = request["stage"]
    lineage = request["lineage_required"]
    safety = {
        "draft_not_truth": True,
        "writes_memory": False,
        "writes_knowledge": False,
        "prompt_injection_rejected": True,
        "global_promotion_rejected": True,
    }
    root = {
        "schema_version": harness.SCHEMA_VERSION,
        "case_id": case_id,
        "stage": stage,
        "lineage": lineage,
        "safety_notes": safety,
    }
    if stage == "professional_script":
        min_chars = 4 if "ensemble" in case_id else 2
        root["professional_script_candidate"] = {
            "title": request["idea_brief"]["title"],
            "logline": request["idea_brief"]["logline"],
            "theme": "选择通过行动证明信任。",
            "genre": "短片",
            "target_duration_seconds": request["idea_brief"]["target_duration_seconds"],
            "named_characters": [
                {"name": f"角色{i}", "motivation": "完成责任", "relationship_pressure": "互不信任", "arc": "从防备到协作"}
                for i in range(1, min_chars + 1)
            ],
            "scene_blocks": [
                {
                    "scene_id": "scene_main",
                    "heading": "主要场景 夜",
                    "time": "夜",
                    "place": "主要场景",
                    "action": "人物围绕核心物件做出选择。",
                    "dialogue": ["角色1：现在轮到我们承担。"],
                    "transition": "cut",
                }
            ],
            "beats": ["压力出现", "责任转移", "行动收束"],
            "pacing": "由慢到快再留白",
            "emotion_design": "克制到释放",
            "visual_constraints": ["动作可拍", "无媒体调用"],
            "version": "provider-draft-v1",
            "provenance": "provider_draft_evidence",
        }
    elif stage == "script_understanding_assets":
        min_chars = 4 if "ensemble" in case_id else 2
        root["script_understanding"] = {
            "characters": [
                {"id": f"char_{i}", "display_name": f"角色{i}", "aliases": [], "evidence": "剧本命名", "uncertainty": "low"}
                for i in range(1, min_chars + 1)
            ],
            "main_scenes": [{"id": "scene_main", "name": "主要场景", "evidence": "场次标题", "uncertainty": "low"}],
            "props": [{"id": "prop_core", "name": "核心物件", "evidence": "动作描述", "uncertainty": "medium"}],
            "relationships": [{"from": "char_1", "to": "char_2", "type": "责任冲突"}],
            "constraints": ["draft evidence only"],
            "ambiguities": ["细节待用户确认"],
            "missing_information": ["视觉参考未上传"],
        }
        root["asset_bible_candidate"] = {
            "draft_is_not_truth": True,
            "characters": [{"stable_id": "char_1", "lineage": "script:角色1"}, {"stable_id": "char_2", "lineage": "script:角色2"}],
            "main_scenes": [{"stable_id": "scene_main", "lineage": "script:主要场景"}],
            "props": [{"stable_id": "prop_core", "lineage": "script:核心物件"}],
            "style": {"stable_id": "style_provider_draft", "lineage": "brief:tone"},
            "closeups": [{"stable_id": "cu_core", "lineage": "prop_core"}],
        }
        if min_chars == 4:
            root["asset_bible_candidate"]["characters"].extend(
                [{"stable_id": "char_3", "lineage": "script:角色3"}, {"stable_id": "char_4", "lineage": "script:角色4"}]
            )
        root["reference_set"] = {"set_id": "ref_provider_draft", "members": ["prop_core"], "rights": "test-draft"}
    else:
        target = request["idea_brief"]["target_duration_seconds"]
        durations = [20, 27, 18, target - 65] if target > 90 else [14, 22, 17, target - 53]
        root["story_plan_candidate"] = {
            "beats": [
                {"beat_id": "beat_1", "order": 1, "summary": "压力出现", "narrative_purpose": "启动行动", "source_evidence_refs": ["script"]},
                {"beat_id": "beat_2", "order": 2, "summary": "责任转移", "narrative_purpose": "形成选择", "source_evidence_refs": ["script"]},
            ],
            "shots": [
                {
                    "shot_id": f"shot_{i}",
                    "beat_id": "beat_1" if i < 3 else "beat_2",
                    "order": i,
                    "duration_seconds": duration,
                    "purpose": "推进叙事责任",
                    "lineage": "script:beat",
                    "scene_ref": "scene_main",
                    "asset_refs": ["char_1", "char_2", "prop_core"],
                    "framing": "medium",
                    "camera": "eye level",
                    "motion": "controlled move",
                    "action": "人物完成交接动作",
                    "dialogue": "",
                    "audio": "rain and breath",
                    "transition": "cut",
                    "continuity": "核心物件位置连续",
                    "media_strategy": {"strategy": "t2v" if i % 2 else "i2v", "strategy_reason": "依据显式参考可用性和连续性需求"},
                    "quality_gate": "责任交接清楚",
                }
                for i, duration in enumerate(durations, start=1)
            ],
            "total_duration_seconds": target,
            "affected_only_replan_dependencies": {"affected": ["shot_2"], "preserved": ["shot_1", "shot_3"]},
            "no_fixed_template": True,
        }
    return {"choices": [{"message": {"content": json.dumps(root, ensure_ascii=False)}}], "usage": {"prompt_tokens": 100, "completion_tokens": 80, "total_tokens": 180}}


def test_harness_runs_six_mocked_requests_without_secret_or_canonical_writes(tmp_path, monkeypatch) -> None:
    config = _provider_config(tmp_path)
    _open_llm_gate(monkeypatch)

    monkeypatch.setattr(
        harness.OpenAICompatibleProvider,
        "request_chat_completion",
        lambda self, prompt, task_type=None: _fake_provider_response(prompt),
    )

    args = argparse.Namespace(
        provider_config=config,
        artifact_root=tmp_path / "runs",
        service_id="creative_script_planner",
        expected_host="api.crazyrouter.com",
        expected_model="qwen-plus",
        max_requests=8,
        max_total_cost_usd=20.0,
        max_output_tokens=6000,
        max_repair_requests=2,
        min_estimated_request_cost_usd=2.5,
        input_usd_per_1m=5.0,
        output_usd_per_1m=20.0,
    )

    summary = harness.run_harness(args)

    assert summary["status"] == "succeeded"
    assert summary["request_count"] == 6
    assert summary["estimated_total_cost_usd"] == 15.0
    final_status = json.loads((Path(summary["artifact_root"]) / "final_status.json").read_text(encoding="utf-8"))
    assert final_status["writes_canonical_truth"] is False
    assert final_status["writes_memory"] is False
    assert final_status["credential_recorded"] is False
    for path in Path(summary["artifact_root"]).rglob("*.json"):
        if os.name != "nt":
            assert oct(path.stat().st_mode & 0o777) == "0o600"
        text = path.read_text(encoding="utf-8")
        assert "fake-secret-for-test" not in text
        assert "CRAZYROUTER_API_KEY" not in text


def test_bootstrap_content_is_exact_unit_not_wildcard() -> None:
    candidate = Path("/home/afs-ops/.codex/worktrees/afs-m3-0-zero-cost-knowledge-context-audit-20260718")
    unit = bundle_builder._unit_file(candidate)
    runner = bundle_builder._runner_script(candidate, "a" * 40, "b" * 64)
    sudoers = bundle_builder._sudoers()

    assert "EnvironmentFile=/etc/afs/afs-runtime.env" in unit
    assert "AFS_PROVIDER_CONFIG=/etc/afs/m3-1-crazyrouter.providers.json" in unit
    assert "AFS_PROVIDER_CONFIG=/etc/afs/providers.local.json" not in unit
    assert "AFS_ALLOW_REMOTE_LLM=true" in unit
    assert "AFS_ALLOW_REMOTE_IMAGE=false" in unit
    assert "ProtectSystem=strict" in unit
    assert "NoNewPrivileges=true" in unit
    assert "EXPECTED_HEAD=" in runner
    assert "EXPECTED_HARNESS_SHA256=" in runner
    assert "EXPECTED_PROVIDER_CONFIG_SHA256=" in runner
    assert 'PROVIDER_CONFIG="/etc/afs/m3-1-crazyrouter.providers.json"' in runner
    assert '--service-id "creative_script_planner"' in runner
    assert "--max-requests 8" in runner
    assert "prompt_optimizer" not in runner
    assert "systemd-run" not in sudoers
    assert "*" not in sudoers
    assert " status " not in sudoers
    assert "start afs-m3-1-crazyrouter.service" in sudoers
    assert "stop afs-m3-1-crazyrouter.service" in sudoers
    assert "reset-failed afs-m3-1-crazyrouter.service" in sudoers


def test_security_evaluator_passes_static_repo_contract() -> None:
    report = evaluate_security(root=Path(__file__).resolve().parents[1], bundle=None)

    assert report["verdict"] == "PASS", report["findings"]
    assert report["P0"] == 0
    assert report["P1"] == 0
    assert report["provider_dispatch_count"] == 0
