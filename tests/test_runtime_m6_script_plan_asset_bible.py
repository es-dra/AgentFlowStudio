from __future__ import annotations

from copy import deepcopy
import hashlib
import time

from fastapi.testclient import TestClient
import pytest

from apps.api.runtime_film_production_graph import compile_film_candidate
from apps.api.runtime_m6_script_plan_asset_bible import (
    M6PlanningError,
    M6ScriptPlanPreviewRequest,
    REVIEW_ROLES,
    build_m6_script_plan_asset_bible,
    validate_m6_candidate,
)
from apps.api import runtime_m6_server_codex_planner
from apps.api.runtime_service import create_runtime_app


IDEA_TEXT = """
角色：林澈、唐予。场景：夜晚旧剪辑室、清晨屋顶。道具：场记板、旧镜头。特写：林澈手背的伤痕、时间线上的红色标记。
风格：克制写实冷暖对照。时间：夜晚到清晨。光线：剪辑室屏幕冷光与屋顶晨光。季节：初秋。连续性：旧镜头始终在唐予手边。
目标：林澈想证明被删掉的素材能救回影片。冲突：唐予担心返工会拖垮拍摄预算。关系：两人从互相指责转为共同承担。变化：林澈从逃避失误转为主动承认。
林澈盯着屏幕里的断帧，低声说“如果这一秒还在，结尾就不是谎言”。
唐予把场记板放到桌边，要求他在十分钟内给出能拍的重做方案。
两人带着旧镜头上到屋顶，晨光压住城市噪声，林澈终于说出自己删错素材的真相。
唐予没有责备，只把红色标记改成新的拍摄任务，让林澈先拍自己的手和那支旧镜头。
"""

SCRIPT_TEXT = """
角色：米拉、陶、阿衡。场景：傍晚观测台、雨后的信号室、地下水泵间。道具：铜色罗盘、裂开的玻璃杯、备用电池。
外观：米拉短发银灰外套；陶黑色雨衣；阿衡戴旧耳机。服装：三人保持同一夜晚的湿冷质感。年龄：二十七到三十五岁。比例：真人写实。
空间：观测台有环形轨道，信号室狭窄，水泵间低顶。光线：傍晚橙光、绿色设备灯、手电硬光。季节：雨季。连续性：铜色罗盘每场都必须在画面内有明确位置。
米拉校准镜头时，远处信号突然偏移，她要求陶记录频率。
陶在信号室打开备用电池，却发现玻璃杯裂纹与信号波形完全一致。
阿衡听见水泵间的旧广播，意识到偏移不是天气，而是有人在地下重放十年前的呼救。
三人沿着水声进入地下，罗盘开始倒转，米拉用镜头对准墙面反光。
陶读出最后一段呼救，阿衡摘下耳机，承认当年自己听过同样的声音却没有上报。
米拉决定不再追逐信号源，而是把镜头留在三人的沉默上，让真相成为下一场戏的压力。
"""

EXPLICIT_NAME_BRIEF = (
    "夏岚在海边档案馆整理一支银色录音笔。"
    "保持角色名称“夏岚”、场景名称“海边档案馆”、道具名称“银色录音笔”不变；"
    "规划3个连续镜头，总时长约25秒。"
    "不要新增其他人物、场景或道具；制作参考必须明确标为辅助内容。"
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("灯亮", "灯亮"),
        ("  一句话，带标点！  ", "一句话，带标点！"),
        ("第一行。\n第二行？", "第一行。\n第二行？"),
        ("🌧️ 雨夜", "🌧️ 雨夜"),
    ],
)
def test_m6_preview_request_accepts_bound_applied_scripts_of_any_length(raw: str, expected: str) -> None:
    clean = _clean_source_text_for_assertion(raw)
    request = M6ScriptPlanPreviewRequest(
        source_kind="script",
        source_text=raw,
        source_revision_id="revision-test",
        source_revision_digest=hashlib.sha256(clean.encode("utf-8")).hexdigest(),
    )
    assert _clean_source_text_for_assertion(request.source_text) == expected
    assert request.source_text == raw
    assert request.provider_dispatch_count == 0


@pytest.mark.parametrize("raw", ["", " ", "\n\t"])
def test_m6_preview_request_rejects_empty_creator_input(raw: str) -> None:
    with pytest.raises(ValueError):
        M6ScriptPlanPreviewRequest(
            source_kind="script",
            source_text=raw,
            source_revision_id="revision-test",
            source_revision_digest="0" * 64,
        )


def test_m6_preview_request_rejects_unbound_or_non_script_sources() -> None:
    digest = hashlib.sha256(b"bound script").hexdigest()
    with pytest.raises(ValueError):
        M6ScriptPlanPreviewRequest(source_kind="script", source_text="bound script")
    with pytest.raises(ValueError):
        M6ScriptPlanPreviewRequest(
            source_kind="idea",
            source_text="bound script",
            source_revision_id="revision-test",
            source_revision_digest=digest,
        )


def _clean_source_text_for_assertion(value: str) -> str:
    return value.strip()


def test_m6_preview_builds_varied_professional_candidates_without_fixed_profiles() -> None:
    idea = build_m6_script_plan_asset_bible("m6-idea", {"source_kind": "idea", "source_text": IDEA_TEXT})
    script = build_m6_script_plan_asset_bible("m6-script", {"source_kind": "script", "source_text": SCRIPT_TEXT})

    idea_candidate = idea["candidate"]
    script_candidate = script["candidate"]
    assert idea["validation"]["verdict"] == "PASS"
    assert script["validation"]["verdict"] == "PASS"
    assert len(idea_candidate["shots"]) != len(script_candidate["shots"])
    for candidate in (idea_candidate, script_candidate):
        durations = [shot["duration_seconds"] for shot in candidate["shots"]]
        assert len(set(durations)) > 1
        assert not (len(durations) == 4 and set(durations) == {15.0})
        assert not (len(durations) == 10 and set(durations) == {6.0})
        assert candidate["asset_bible"]["status"] == "pending_confirmation"
        assert {"4x15", "10x6"} <= set(candidate["sequence"]["dynamic_policy"]["fixed_profile_forbidden"])
        assert {row["role"] for row in candidate["review_requirements"]} == set(REVIEW_ROLES)
        assert candidate["provider_dispatch_count"] == 0
        assert candidate["cost_usd"] == 0
        assert candidate["brief"]["title"] in candidate["sequence"]["name"]
        assert "M6" not in candidate["sequence"]["name"]
        assert all(item["promotion_state"] != "promoted" for item in candidate["knowledge_context"]["items"])
        assert all(shot["shot_size"] and shot["camera_movement"] and shot["narrative_purpose"] for shot in candidate["shots"])
        prop_assets = [row for row in candidate["assets"] if row["kind"] == "prop"]
        production_aids = [row for row in candidate["assets"] if row["kind"] in {"closeup", "reference_set", "style"}]
        assert {row["asset_id"] for row in prop_assets} == set(candidate["asset_bible"]["prop_refs"])
        assert {row["asset_id"] for row in production_aids} == set(candidate["asset_bible"]["production_aid_refs"])
        assert not set(candidate["asset_bible"]["prop_refs"]) & {row["asset_id"] for row in production_aids}
        assert all(row["classification"] == "canonical_prop" for row in prop_assets)
        assert all(row["classification"] == "production_aid" for row in production_aids)
        scope = candidate["m6_scope_review"]
        assert scope["fail_closed"]["status"] == "pass"
        assert scope["proposed_additions"]
        assert scope["proposed_expansions"]
        assert scope["proposed_classifications"]
        assert any(item["association_type"] == "asset_bible.prop_refs" for item in scope["affected_associations"])
        assert any(item["association_type"] == "asset_bible.production_aid_refs" for item in scope["affected_associations"])


def test_m6_canonical_names_preserve_conjunction_characters_and_line_boundaries() -> None:
    source = """
角色：和也、Anderson
场景：和平广场、Andromeda Hall
道具：红与蓝徽章、Anderson钥匙
风格：清晰写实
和也在和平广场举起红与蓝徽章，等待远处的回应。
Anderson走进Andromeda Hall，把钥匙放在桌面上。
"""

    candidate = build_m6_script_plan_asset_bible(
        "m6-adversarial-names",
        {"source_kind": "script", "source_text": source},
    )["candidate"]

    scope = candidate["m6_scope_review"]["canonical"]
    assert scope["characters"] == ["和也", "Anderson"]
    assert scope["scenes"] == ["和平广场", "Andromeda Hall"]
    assert scope["props"] == ["红与蓝徽章", "Anderson钥匙"]
    assert [row["display_name"] for row in candidate["characters"]] == scope["characters"]
    assert [row["name"] for row in candidate["scenes"]] == scope["scenes"]
    assert [row["name"] for row in candidate["assets"] if row["kind"] == "prop"] == scope["props"]
    assert candidate["m6_scope_review"]["fail_closed"]["status"] == "pass"


def test_m6_explicit_name_declarations_are_canonical_authority() -> None:
    candidate = build_m6_script_plan_asset_bible(
        "m6-explicit-name-authority",
        {"source_kind": "idea", "source_text": EXPLICIT_NAME_BRIEF},
    )["candidate"]

    scope = candidate["m6_scope_review"]
    assert scope["canonical"] == {
        "characters": ["夏岚"],
        "scenes": ["海边档案馆"],
        "props": ["银色录音笔"],
    }
    assert scope["candidate_canonical"] == scope["canonical"]
    assert scope["fail_closed"]["status"] == "pass"


def test_m6_explicit_name_declarations_preserve_adversarial_names_and_ignore_forbidden_examples() -> None:
    source = (
        "保持角色名称“和也”和“Anderson”、场景名称“Andromeda Hall”、"
        "道具名称“红与蓝徽章”不变。"
        "不要新增角色名称“路人”，不得添加场景名称“备用房间”，禁止使用道具名称“样例钥匙”。"
    )

    scope = runtime_m6_server_codex_planner.m6_source_canonical_scope(source)

    assert scope["characters"] == ["和也", "Anderson"]
    assert scope["scenes"] == ["Andromeda Hall"]
    assert scope["props"] == ["红与蓝徽章"]


def test_m6_server_codex_prompt_preserves_non_chinese_canonical_names() -> None:
    source = """
角色：和也、Anderson
场景：和平广场、Andromeda Hall
道具：红与蓝徽章
和也在和平广场等待，Anderson随后进入。
两人在Andromeda Hall交接红与蓝徽章。
"""

    prompt = runtime_m6_server_codex_planner._server_codex_prompt(
        project_id="m6-multilingual-canonical",
        source_kind="script",
        source_text=source,
        requested_language="zh-CN",
        revision_instruction="",
        parent_candidate_digest="",
        schema_digest="a" * 64,
        dispatch_id="m6_multilingual_test",
    )

    assert "canonical characters（必须逐字保留且不得增删）: 和也、Anderson" in prompt
    assert "canonical scenes（必须逐字保留且不得改名）: 和平广场、Andromeda Hall" in prompt
    assert "用户 canonical 名称保留原始字符和语言" in prompt
    assert "不得翻译、音译或改写 canonical 名称" in prompt
    assert "按需 production aid" in prompt
    assert "可以为空" in prompt
    assert "角色、场景、镜头和资产名称必须是中文专名" not in prompt
    assert "禁止英文污染" not in prompt


def test_m6_server_codex_accepts_explicit_name_brief_with_exact_canonical_scope(monkeypatch) -> None:
    payload = _single_scope_server_codex_payload("夏岚", "海边档案馆", "银色录音笔")
    calls: list[str] = []

    def fake_dispatch(*, prompt, output_dir, schema, schema_digest):
        calls.append(prompt)
        return {"provider_calls_started": True, "structured_output": payload}

    monkeypatch.setattr(runtime_m6_server_codex_planner, "_dispatch_server_codex_structured_plan", fake_dispatch)
    preview = runtime_m6_server_codex_planner.build_m6_server_codex_script_plan_asset_bible(
        "m6-explicit-server-codex",
        {"source_kind": "idea", "source_text": EXPLICIT_NAME_BRIEF},
    )

    candidate = preview["candidate"]
    assert preview["validation"]["verdict"] == "PASS"
    assert candidate["m6_scope_review"]["canonical"] == {
        "characters": ["夏岚"],
        "scenes": ["海边档案馆"],
        "props": ["银色录音笔"],
    }
    assert candidate["m6_scope_review"]["fail_closed"]["status"] == "pass"
    assert "夏岚" in calls[0] and "海边档案馆" in calls[0] and "银色录音笔" in calls[0]


def test_m6_server_codex_accepts_content_distinct_equal_durations_with_source_timing_contract() -> None:
    source = (
        "程遥在山顶气象站校准一枚黑色风向标。"
        "保持角色名称“程遥”、场景名称“山顶气象站”、道具名称“黑色风向标”不变；"
        "规划3个连续镜头，总时长约21秒。不要新增其他人物、场景或道具。"
    )
    payload = _single_scope_server_codex_payload("程遥", "山顶气象站", "黑色风向标")
    timing_semantics = [
        ("建立气象站工作台与风向标的初始方位。", "交代空间、人物和待修道具的起始状态。", "需要完整看清方位读数与人物检查动作。"),
        ("程遥拆开轴承并清除阻塞的砂粒。", "呈现修复难点以及道具状态的可见变化。", "拆解、清理和复查必须在一个连续动作内完成。"),
        ("重新安装风向标并确认指针恢复转动。", "以修复结果收束行动并建立后续连续性。", "需要保留指针启动和人物确认反应的时间。"),
    ]
    for shot, (intent, purpose, reason) in zip(payload["shots"], timing_semantics, strict=True):
        shot["duration_seconds"] = 7
        shot["intent"] = intent
        shot["narrative_purpose"] = purpose
        shot["content_driven_duration_reason"] = reason

    candidate = runtime_m6_server_codex_planner._candidate_from_provider_payload(
        project_id="m6-equal-content-driven",
        body={"source_kind": "idea", "source_text": source},
        payload=payload,
        source_digest="a" * 64,
        dispatch_id="m6_equal_content_driven",
        schema_digest="b" * 64,
        prompt_chars=1000,
        parent_candidate_digest="",
        revision_instruction="",
    )

    assert validate_m6_candidate(candidate)["verdict"] == "PASS"
    assert [shot["duration_seconds"] for shot in candidate["shots"]] == [7, 7, 7]
    assert candidate["sequence"]["dynamic_policy"]["source_timing_contract"] == {
        "source_authority": "user_supplied_timing_scope",
        "requested_shot_count": 3,
        "requested_total_duration_seconds": 21.0,
        "duration_tolerance_seconds": 2.1,
        "approximate_total_duration": True,
    }


def test_m6_server_codex_accepts_no_optional_production_aids_without_synthesizing_them() -> None:
    source = (
        "顾言在城市天文台修复一枚白铜星盘。"
        "保持角色名称“顾言”、场景名称“城市天文台”、道具名称“白铜星盘”不变；"
        "规划3个连续镜头，总时长约25秒。不要新增其他人物、场景或道具。"
    )
    payload = _single_scope_server_codex_payload("顾言", "城市天文台", "白铜星盘")
    payload["assets"] = [row for row in payload["assets"] if row["kind"] == "prop"]
    for shot in payload["shots"]:
        shot["asset_indexes"] = [1]

    candidate = runtime_m6_server_codex_planner._candidate_from_provider_payload(
        project_id="m6-no-optional-production-aids",
        body={"source_kind": "idea", "source_text": source},
        payload=payload,
        source_digest="c" * 64,
        dispatch_id="m6_no_optional_production_aids",
        schema_digest="d" * 64,
        prompt_chars=1000,
        parent_candidate_digest="",
        revision_instruction="",
    )

    assert validate_m6_candidate(candidate)["verdict"] == "PASS"
    assert [row["name"] for row in candidate["assets"]] == ["白铜星盘"]
    assert candidate["asset_bible"]["prop_refs"]
    assert candidate["asset_bible"]["closeup_refs"] == []
    assert candidate["asset_bible"]["reference_set_refs"] == []
    assert candidate["asset_bible"]["style_refs"] == []
    assert candidate["asset_bible"]["production_aid_refs"] == []
    assert candidate["m6_scope_review"]["production_aids"] == []
    assert compile_film_candidate("m6-no-optional-production-aids", candidate)


@pytest.mark.parametrize(
    ("source", "message", "validator_code"),
    [
        (
            "规划4个连续镜头，总时长约21秒。",
            "shot count does not match source",
            "source_shot_count_mismatch",
        ),
        (
            "规划3个连续镜头，总时长约36秒。",
            "total duration does not match source",
            "source_total_duration_mismatch",
        ),
    ],
)
def test_m6_server_codex_timing_contract_fails_closed_on_wrong_count_or_total(
    source: str,
    message: str,
    validator_code: str,
) -> None:
    brief = (
        "程遥在山顶气象站校准一枚黑色风向标。"
        "保持角色名称“程遥”、场景名称“山顶气象站”、道具名称“黑色风向标”不变；"
        f"{source}不要新增其他人物、场景或道具。"
    )
    payload = _single_scope_server_codex_payload("程遥", "山顶气象站", "黑色风向标")
    timing_semantics = [
        ("建立风向标初始方位。", "交代起始状态。", "需要看清方位读数。"),
        ("拆开轴承清除砂粒。", "呈现修复难点。", "需要保留拆解过程。"),
        ("重新安装并确认转动。", "收束修复行动。", "需要看到启动反应。"),
    ]
    for shot, (intent, purpose, reason) in zip(payload["shots"], timing_semantics, strict=True):
        shot["duration_seconds"] = 7
        shot["intent"] = intent
        shot["narrative_purpose"] = purpose
        shot["content_driven_duration_reason"] = reason

    with pytest.raises(M6PlanningError, match=message) as captured:
        runtime_m6_server_codex_planner._candidate_from_provider_payload(
            project_id="m6-source-timing-drift",
            body={"source_kind": "idea", "source_text": brief},
            payload=payload,
            source_digest="a" * 64,
            dispatch_id="m6_source_timing_drift",
            schema_digest="b" * 64,
            prompt_chars=1000,
            parent_candidate_digest="",
            revision_instruction="",
        )
    assert captured.value.validator_code == validator_code


def test_m6_source_timing_contract_is_general_and_ignores_ordinal_shot_mentions() -> None:
    english = runtime_m6_server_codex_planner._source_timing_contract(
        "Plan 5 continuous shots with a total duration of about 42 seconds."
    )
    chinese = runtime_m6_server_codex_planner._source_timing_contract(
        "安排7个分镜，总时长70秒；第3镜头与第 4 镜头都需要保留动作反应。"
    )

    assert english["requested_shot_count"] == 5
    assert english["requested_total_duration_seconds"] == 42.0
    assert english["approximate_total_duration"] is True
    assert chinese["requested_shot_count"] == 7
    assert chinese["requested_total_duration_seconds"] == 70.0
    assert chinese["approximate_total_duration"] is False


def test_m6_explicit_name_brief_still_fails_closed_on_addition_rename_and_omission() -> None:
    mutations = []

    extra_character = _single_scope_server_codex_payload("夏岚", "海边档案馆", "银色录音笔")
    extra_character["characters"].append(
        {**deepcopy(extra_character["characters"][0]), "display_name": "未授权访客"}
    )
    mutations.append(extra_character)

    renamed_scene = _single_scope_server_codex_payload("夏岚", "海边档案馆", "银色录音笔")
    renamed_scene["scenes"][0]["name"] = "模型改名场景"
    mutations.append(renamed_scene)

    missing_prop = _single_scope_server_codex_payload("夏岚", "海边档案馆", "银色录音笔")
    missing_prop["assets"] = [row for row in missing_prop["assets"] if row["kind"] != "prop"]
    for shot in missing_prop["shots"]:
        shot["asset_indexes"] = [1]
    mutations.append(missing_prop)

    for payload in mutations:
        with pytest.raises(M6PlanningError, match="canonical scope drift failed closed"):
            runtime_m6_server_codex_planner._candidate_from_provider_payload(
                project_id="m6-explicit-drift",
                body={"source_kind": "idea", "source_text": EXPLICIT_NAME_BRIEF},
                payload=payload,
                source_digest="a" * 64,
                dispatch_id="m6_explicit_drift",
                schema_digest="b" * 64,
                prompt_chars=1000,
                parent_candidate_digest="",
                revision_instruction="",
            )


def test_m6_confirm_writes_the_same_production_graph_consumed_by_m5_workspace(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    run = _start_and_wait(client, "m6-graph", IDEA_TEXT, "m6-graph-preview")
    preview = run["preview"]

    confirmed = client.post("/projects/m6-graph/m6/script-plan-asset-bible/confirm", json={
        "expected_graph_version": 0,
        "run_id": run["run_id"],
        "candidate_digest": run["candidate_digest"],
    })
    assert confirmed.status_code == 200, confirmed.text
    graph = confirmed.json()["graph"]
    assert graph["version"] == 1
    assert graph["provider_gates"] == {key: False for key in graph["provider_gates"]}
    assert any(node["category"] == "entity" and node["metadata"].get("goal") for node in graph["nodes"].values())
    assert any(node["category"] == "location" and node["metadata"].get("lighting") for node in graph["nodes"].values())
    assert any(node["category"] == "unit" and node["metadata"].get("shot_size") for node in graph["nodes"].values())

    workspace = client.get("/projects/m6-graph/m5/sequence-workspace").json()
    assert workspace["status"] == "ready"
    assert workspace["graph_digest"] == graph["graph_digest"] == workspace["storyboard"]["graph_digest"]
    assert workspace["sequence"]["characters"]
    assert workspace["sequence"]["reference_sets"]
    assert len(workspace["sequence"]["props"]) == 2
    assert all(item["metadata"]["kind"] == "prop" for item in workspace["sequence"]["props"])
    assert all(item["metadata"]["classification"] == "canonical_prop" for item in workspace["sequence"]["props"])
    assert len(workspace["sequence"]["production_aids"]) >= 3
    assert workspace["provider_dispatch_count"] == 0
    assert workspace["cost_usd"] == 0
    assert not (tmp_path / "runtime" / "projects" / "m6-graph" / "studio_state.json").exists()


def test_m6_server_codex_preview_uses_real_provider_contract_and_same_graph(tmp_path, monkeypatch) -> None:
    provider_config = tmp_path / "provider_config.json"
    provider_config.write_text('{"schema_version":"company_provider_secrets.v0.1","accounts":{},"account_pools":{},"services":{}}', encoding="utf-8")
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(provider_config))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    for gate in (
        "AFS_ALLOW_REMOTE_IMAGE",
        "AFS_ALLOW_REMOTE_VIDEO",
        "AFS_ALLOW_REMOTE_AUDIO",
        "AFS_ALLOW_REMOTE_ASR",
        "AFS_ALLOW_REMOTE_VISION",
        "AFS_ALLOW_EXTERNAL_DOWNLOAD",
    ):
        monkeypatch.setenv(gate, "false")

    calls: list[dict[str, object]] = []

    def fake_dispatch(*, prompt, output_dir, schema, schema_digest):
        calls.append({"prompt": prompt, "output_dir": output_dir, "schema_digest": schema_digest})
        return {
            "provider_calls_started": True,
            "structured_output": _server_codex_payload(),
        }

    monkeypatch.setattr(runtime_m6_server_codex_planner, "_dispatch_server_codex_structured_plan", fake_dispatch)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))

    first_run = _start_and_wait(client, "m6-codex", SCRIPT_TEXT, "m6-codex-preview-1", source_kind="script")
    first_payload = first_run["preview"]
    first_candidate = first_payload["candidate"]
    first_digest = first_payload["candidate_digest"]
    assert first_payload["provider_dispatch_count"] == 1
    assert first_candidate["provider_lineage"]["service_id"] == "server_codex"
    assert first_candidate["provider_lineage"]["provider"] == "codex_local"
    assert first_candidate["provider_lineage"]["provider_calls_started"] is True
    assert first_candidate["provider_lineage"]["provider_raw_response_stored"] is False
    assert first_candidate["brief"]["title"] in first_candidate["sequence"]["name"]
    assert "M6" not in first_candidate["sequence"]["name"]
    assert first_payload["validation"]["provider_dispatch_count"] == 1
    assert first_candidate["m6_scope_review"]["canonical"]["characters"] == ["米拉", "陶", "阿衡"]
    assert first_candidate["m6_scope_review"]["canonical"]["scenes"] == ["傍晚观测台", "雨后的信号室", "地下水泵间"]
    assert first_candidate["m6_scope_review"]["canonical"]["props"] == ["铜色罗盘", "裂开的玻璃杯", "备用电池"]
    assert [row["display_name"] for row in first_candidate["characters"]] == ["米拉", "陶", "阿衡"]
    assert [row["name"] for row in first_candidate["scenes"]] == ["傍晚观测台", "雨后的信号室", "地下水泵间"]
    assert [row["name"] for row in first_candidate["assets"] if row["kind"] == "prop"] == ["铜色罗盘", "裂开的玻璃杯", "备用电池"]
    assert {row["asset_id"] for row in first_candidate["assets"] if row["kind"] == "prop"} == set(first_candidate["asset_bible"]["prop_refs"])
    assert all(row["classification"] == "production_aid" for row in first_candidate["assets"] if row["kind"] in {"closeup", "reference_set", "style"})
    assert len(calls) == 1
    assert "固定 4x15" in str(calls[0]["prompt"])
    assert "canonical characters" in str(calls[0]["prompt"])
    assert "米拉、陶、阿衡" in str(calls[0]["prompt"])
    assert "铜色罗盘、裂开的玻璃杯、备用电池" in str(calls[0]["prompt"])

    second_run = _start_and_wait(
        client,
        "m6-codex",
        SCRIPT_TEXT,
        "m6-codex-preview-2",
        source_kind="script",
        parent_candidate_digest=first_digest,
        revision_instruction="第二轮请加深米拉和阿衡的关系压力，并补强罗盘和玻璃杯的连续性锁定。",
    )
    second_candidate = second_run["preview"]["candidate"]
    assert second_candidate["script_revision"]["revision_number"] == 2
    assert second_candidate["brief"]["lineage"]["parent_candidate_digest"] == first_digest
    assert len(calls) == 2
    assert first_digest in str(calls[1]["prompt"])

    confirmed = client.post("/projects/m6-codex/m6/script-plan-asset-bible/confirm", json={
        "expected_graph_version": 0,
        "run_id": second_run["run_id"],
        "candidate_digest": second_run["candidate_digest"],
    })
    assert confirmed.status_code == 200, confirmed.text
    graph = confirmed.json()["graph"]
    assert confirmed.json()["provider_dispatch_count"] == 1
    assert graph["provider_gates"] == {key: False for key in graph["provider_gates"]}
    workspace = client.get("/projects/m6-codex/m5/sequence-workspace").json()
    assert workspace["graph_digest"] == graph["graph_digest"]
    assert workspace["sequence"]["reference_sets"]
    assert len(workspace["sequence"]["props"]) == 3
    assert all(item["metadata"]["classification"] == "canonical_prop" for item in workspace["sequence"]["props"])
    assert len(workspace["sequence"]["production_aids"]) >= 3
    assert not (tmp_path / "runtime" / "projects" / "m6-codex" / "studio_state.json").exists()


def test_m6_server_codex_scope_drift_fails_closed_before_candidate_or_graph_write(tmp_path, monkeypatch) -> None:
    provider_config = tmp_path / "provider_config.json"
    provider_config.write_text('{"schema_version":"company_provider_secrets.v0.1","accounts":{},"account_pools":{},"services":{}}', encoding="utf-8")
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(provider_config))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    for gate in (
        "AFS_ALLOW_REMOTE_IMAGE",
        "AFS_ALLOW_REMOTE_VIDEO",
        "AFS_ALLOW_REMOTE_AUDIO",
        "AFS_ALLOW_REMOTE_ASR",
        "AFS_ALLOW_REMOTE_VISION",
        "AFS_ALLOW_EXTERNAL_DOWNLOAD",
    ):
        monkeypatch.setenv(gate, "false")

    drift_payload = _server_codex_payload()
    drift_payload["characters"] = drift_payload["characters"] + [
        {
            "display_name": "额外角色",
            "goal": "试图把模型自创人物加入制作图。",
            "conflict": "该人物没有来自用户文本的 canonical 授权。",
            "relationship_arc": "不应进入确认卡。",
            "change_vector": "不应被写入。",
            "appearance": "不应被写入。",
            "wardrobe": "不应被写入。",
            "age_range": "成人",
            "proportion": "真人写实比例",
            "signature_features": ["未授权轮廓", "未授权动作"],
            "do_not_change": ["未授权身份", "未授权造型"],
        }
    ]
    drift_payload["scenes"][0] = {**drift_payload["scenes"][0], "name": "改名观测台"}
    drift_payload["assets"] = drift_payload["assets"] + [
        {
            "name": "未授权新道具",
            "kind": "prop",
            "source": "模型自创道具",
            "version": "candidate.v1",
            "applicable_scope": "project",
            "confidence": 0.4,
            "rights_boundary": "未授权道具不得进入候选",
            "style": "不应使用",
            "do_not_change": ["不应写入", "不应确认"],
        }
    ]

    def fake_dispatch(*, prompt, output_dir, schema, schema_digest):
        return {
            "provider_calls_started": True,
            "structured_output": drift_payload,
        }

    monkeypatch.setattr(runtime_m6_server_codex_planner, "_dispatch_server_codex_structured_plan", fake_dispatch)
    runtime_root = tmp_path / "runtime"
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    binding = _bind_script_revision(client, "m6-drift", SCRIPT_TEXT)
    response = client.post(
        "/projects/m6-drift/m6/script-plan-asset-bible/preview",
        headers={"X-Client-Request-ID": "m6-drift-preview"},
        json={"source_kind": "script", "source_text": SCRIPT_TEXT, **binding},
    )
    assert response.status_code == 200, response.text
    run = response.json()
    for _ in range(200):
        if run["phase"] == "failed":
            break
        time.sleep(0.01)
        loaded = client.get(f"/projects/m6-drift/m6/script-plan-asset-bible/preview-runs/{run['run_id']}")
        assert loaded.status_code == 200, loaded.text
        run = loaded.json()
    assert run["phase"] == "failed", run
    assert run["error"]["category"] == "planning_rejected"
    assert run["error"]["message"] == "制作方案未通过结构校验；制作事实未改变。"
    assert run["error"]["validator_code"] == "canonical_scope_drift"
    assert run["candidate_digest"] == ""
    run_dir = runtime_root / "projects" / "m6-drift" / "m6_preview_runs" / run["run_id"]
    assert not (run_dir / "candidate.json").exists()
    assert not (runtime_root / "projects" / "m6-drift" / "production_graph.json").exists()


def test_m6_confirm_rejects_template_gaming_and_unresolved_lineage(tmp_path) -> None:
    candidate = build_m6_script_plan_asset_bible("m6-bad", {"source_kind": "script", "source_text": SCRIPT_TEXT})["candidate"]

    content_driven_equal_duration = deepcopy(candidate)
    for shot in content_driven_equal_duration["shots"]:
        shot["duration_seconds"] = 6.0
        shot["narrative_purpose"] = f"围绕“{shot['intent']}”完成该动作的独立叙事结果。"
        shot["content_driven_duration_reason"] = f"“{shot['intent']}”需要保留完整动作和人物反应。"
    content_driven_equal_duration["sequence"]["target_duration_seconds"] = 6.0 * len(
        content_driven_equal_duration["shots"]
    )
    assert validate_m6_candidate(content_driven_equal_duration)["verdict"] == "PASS"

    repeated_template = deepcopy(content_driven_equal_duration)
    for shot in repeated_template["shots"]:
        shot["intent"] = "重复的模板镜头意图"
        shot["narrative_purpose"] = "重复的模板叙事目的"
        shot["content_driven_duration_reason"] = "重复的模板时长理由"
    with pytest.raises(M6PlanningError, match="equal-duration shots require distinct"):
        validate_m6_candidate(repeated_template)

    numbered_template = deepcopy(content_driven_equal_duration)
    for index, shot in enumerate(numbered_template["shots"], start=1):
        shot["intent"] = f"镜头{index}重复同一个模板意图"
        shot["narrative_purpose"] = f"第{index}个阶段重复同一个叙事目的"
        shot["content_driven_duration_reason"] = f"第{index}步重复同一个时长理由"
    with pytest.raises(M6PlanningError, match="equal-duration shots require distinct"):
        validate_m6_candidate(numbered_template)

    low_information_variation = deepcopy(content_driven_equal_duration)
    labels = "甲乙丙丁戊己庚辛壬癸"
    for label, shot in zip(labels, low_information_variation["shots"], strict=False):
        shot["intent"] = f"重复同一个镜头意图，仅使用标签{label}区分"
        shot["narrative_purpose"] = f"重复同一个叙事目的，仅使用标签{label}区分"
        shot["content_driven_duration_reason"] = f"重复同一个时长理由，仅使用标签{label}区分"
    with pytest.raises(M6PlanningError, match="equal-duration shots require distinct"):
        validate_m6_candidate(low_information_variation)

    fixed_profile = deepcopy(candidate)
    fixed_profile["shots"] = fixed_profile["shots"][:4]
    for shot in fixed_profile["shots"]:
        shot["duration_seconds"] = 15.0
    fixed_profile["sequence"]["target_duration_seconds"] = 60.0
    with pytest.raises(M6PlanningError, match="4x15 profile is forbidden"):
        validate_m6_candidate(fixed_profile)

    unresolved = deepcopy(candidate)
    unresolved["shots"][0]["asset_refs"] = ["missing-asset"]
    with pytest.raises(M6PlanningError, match="unresolved asset"):
        validate_m6_candidate(unresolved)

    promoted = deepcopy(candidate)
    promoted["knowledge_context"]["items"][0]["promotion_state"] = "promoted"
    with pytest.raises(M6PlanningError, match="cannot be promoted"):
        validate_m6_candidate(promoted)

    contaminated = build_m6_script_plan_asset_bible("m6-bad-closeup", {"source_kind": "idea", "source_text": IDEA_TEXT})["candidate"]
    closeup_id = next(row["asset_id"] for row in contaminated["assets"] if row["kind"] == "closeup")
    contaminated["asset_bible"]["prop_refs"].append(closeup_id)
    with pytest.raises(M6PlanningError, match="prop_refs"):
        validate_m6_candidate(contaminated)

    renamed_scene = deepcopy(candidate)
    renamed_scene["scenes"][0]["name"] = "模型改名场景"
    with pytest.raises(M6PlanningError, match="scenes must exactly match"):
        validate_m6_candidate(renamed_scene)


def test_m6_preview_requires_named_entities_and_story_beats() -> None:
    try:
        build_m6_script_plan_asset_bible("m6-empty", {"source_kind": "idea", "source_text": "一个人想拍一部片子，但是没有名字，也没有场景。"})
    except ValueError as exc:
        assert "named character" in str(exc)
    else:
        raise AssertionError("unnamed idea should require planning")

    valid = build_m6_script_plan_asset_bible("m6-direct", {"source_kind": "idea", "source_text": IDEA_TEXT})["candidate"]
    assert validate_m6_candidate(valid)["P0"] == 0


def _start_and_wait(
    client: TestClient,
    project_id: str,
    source_text: str,
    client_request_id: str,
    *,
    source_kind: str = "script",
    **extra,
) -> dict[str, object]:
    assert source_kind == "script"
    binding = _bind_script_revision(client, project_id, source_text)
    response = client.post(
        f"/projects/{project_id}/m6/script-plan-asset-bible/preview",
        headers={"X-Client-Request-ID": client_request_id},
        json={"source_kind": "script", "source_text": source_text, **binding, **extra},
    )
    assert response.status_code == 200, response.text
    run = response.json()
    for _ in range(200):
        if run["phase"] in {"succeeded", "failed", "cancelled"}:
            break
        time.sleep(0.01)
        loaded = client.get(
            f"/projects/{project_id}/m6/script-plan-asset-bible/preview-runs/{run['run_id']}",
        )
        assert loaded.status_code == 200, loaded.text
        run = loaded.json()
    assert run["phase"] == "succeeded", run
    return run


def _bind_script_revision(
    client: TestClient,
    project_id: str,
    source_text: str,
    *,
    headers: dict[str, str] | None = None,
) -> dict[str, str]:
    response = client.post(
        f"/projects/{project_id}/script-revisions",
        headers=headers or {},
        json={"source_kind": "script", "source_text": source_text},
    )
    assert response.status_code == 200, response.text
    revision = response.json()["revision"]
    return {
        "source_revision_id": revision["revision_id"],
        "source_revision_digest": revision["source_digest"],
    }


def _server_codex_payload() -> dict[str, object]:
    return {
        "language": "zh-CN",
        "title": "雨季观测台的回声",
        "logline": "三名角色在雨季设备故障里追查旧呼救，最终把关系亏欠变成下一场戏的压力。",
        "draft_text": (
            "傍晚观测台上，米拉要求陶记录偏移信号，铜色罗盘在轨道边轻微倒转。"
            "信号室里，陶发现裂开的玻璃杯纹路与波形一致，阿衡的耳机传来十年前的旧广播。"
            "水泵间的手电硬光把三人的沉默切开，阿衡承认自己当年听过呼救却没有上报。"
            "米拉不追逐神秘源头，而把镜头留给三个人必须共同承担的真相。"
        ),
        "revision_notes": "补强角色关系、权利时间摘要和罗盘连续性，镜头时长按动作密度重新分配。",
        "structure": {
            "sequence_count": 1,
            "scene_count": 3,
            "turning_points": ["信号偏移暴露异常", "玻璃裂纹对应波形", "阿衡承认旧呼救"],
            "rhythm_strategy": "从观测台的开阔误判压缩到水泵间的窄距对质，停顿逐步变长。",
            "rights_time_summary": "素材来自用户剧本输入，故事时间为雨季同一傍晚到夜间，摘要闭环到三人共同承担。",
        },
        "characters": [
            {
                "display_name": "米拉",
                "goal": "用镜头证明信号偏移不是天气误差，并让真相进入可拍证据。",
                "conflict": "她需要陶的技术记录，却必须面对阿衡隐瞒旧广播的关系裂缝。",
                "relationship_arc": "从指挥同伴完成记录，转向逼迫三人共同承认十年前的缺口。",
                "change_vector": "从追逐信号源转为把镜头留给沉默和责任。",
                "appearance": "短发，银灰外套，雨水压住发梢，动作克制。",
                "wardrobe": "银灰防雨外套、深色内搭，整夜保持湿冷褶皱。",
                "age_range": "二十七到三十二岁",
                "proportion": "真人写实比例，肩颈线条在三场保持一致。",
                "signature_features": ["短发湿冷轮廓", "单手扶镜头的动作"],
                "do_not_change": ["银灰外套", "短发轮廓", "镜头掌控位置"],
            },
            {
                "display_name": "陶",
                "goal": "记录偏移频率并确认备用电池是否能支撑重做方案。",
                "conflict": "她担心返工压力会压垮预算，却被玻璃杯裂纹逼近真相。",
                "relationship_arc": "从执行记录转为主动把技术证据交给米拉和阿衡共同面对。",
                "change_vector": "从控制风险转为接受必须补拍的事实。",
                "appearance": "黑色雨衣，手边总有记录本和备用电池。",
                "wardrobe": "黑色雨衣、深色防水鞋，雨季湿痕保持连续。",
                "age_range": "二十八到三十四岁",
                "proportion": "真人写实比例，动作利落克制。",
                "signature_features": ["黑色雨衣", "快速记录频率的手势"],
                "do_not_change": ["黑色雨衣", "记录本位置", "技术判断角色"],
            },
            {
                "display_name": "阿衡",
                "goal": "确认耳机里的旧广播来源，同时避免暴露自己十年前没有上报。",
                "conflict": "广播把他的旧选择拖回现场，米拉的镜头让逃避失效。",
                "relationship_arc": "从沉默旁观到主动承认，关系从被质疑转为共同承担。",
                "change_vector": "从隐瞒变为摘下耳机承认旧事实。",
                "appearance": "戴旧耳机，眼神回避，水泵间硬光切出脸侧阴影。",
                "wardrobe": "深色夹克和旧耳机，湿痕贯穿三场。",
                "age_range": "三十到三十五岁",
                "proportion": "真人写实比例，微驼背姿态保持。",
                "signature_features": ["旧耳机", "摘耳机前的停顿"],
                "do_not_change": ["旧耳机", "湿冷夹克", "回避视线"],
            },
        ],
        "scenes": [
            {
                "name": "傍晚观测台",
                "space": "环形轨道包围设备，远处天线被雨云压低。",
                "time_of_day": "傍晚",
                "lighting": "雨后橙光混合设备反光，角色脸部有冷暖分区。",
                "season": "雨季",
                "continuity": "铜色罗盘一直在观测台轨道边，指针首次轻微倒转。",
                "action": "米拉校准镜头，陶记录频率，阿衡在后景监听异常。",
                "rhythm": "开阔场景内动作较快，但每次信号偏移后有短暂停顿。",
                "emotion": "专业克制下出现不安。",
                "visual_expression": "用轨道弧线和镜头反光制造被观察的压力。",
                "dialogue_or_sound": ["米拉要求记录频率", "远处电噪突然升高"],
                "do_not_change": ["罗盘在轨道边", "雨季湿痕", "傍晚橙光"],
            },
            {
                "name": "雨后的信号室",
                "space": "狭窄设备间，桌面只够放电池、玻璃杯和记录本。",
                "time_of_day": "入夜前",
                "lighting": "绿色设备灯和窗外残光交替闪动。",
                "season": "雨季",
                "continuity": "玻璃杯裂纹在每个近景中方向一致，罗盘被移到桌角。",
                "action": "陶打开备用电池，米拉对齐裂纹和波形，阿衡开始沉默。",
                "rhythm": "由技术动作转为发现后的停顿，节奏明显收窄。",
                "emotion": "疑惑变成逼近真相的压力。",
                "visual_expression": "玻璃裂纹叠在监视器波形上，形成证据图像。",
                "dialogue_or_sound": ["备用电池咔哒入位", "陶压低声音读出频率"],
                "do_not_change": ["玻璃裂纹方向", "绿色设备灯", "桌角罗盘"],
            },
            {
                "name": "地下水泵间",
                "space": "低顶潮湿空间，水管把人物切成前后层。",
                "time_of_day": "夜间",
                "lighting": "手电硬光和水面反光制造不稳定阴影。",
                "season": "雨季",
                "continuity": "旧耳机、罗盘、玻璃杯碎纹记录都必须在关键镜头可追溯。",
                "action": "三人沿水声进入，阿衡摘下耳机承认旧广播，米拉把镜头停住。",
                "rhythm": "每句话后留出沉默，结尾不追动作而停在责任上。",
                "emotion": "恐惧转为承认后的沉重。",
                "visual_expression": "硬光压近人物，水声吞没辩解。",
                "dialogue_or_sound": ["旧广播片段断续出现", "阿衡摘下耳机时水泵声压过对白"],
                "do_not_change": ["手电硬光方向", "旧耳机", "水声压力"],
            },
        ],
        "assets": [
            {
                "name": "铜色罗盘",
                "kind": "prop",
                "source": "用户剧本输入的项目道具",
                "version": "candidate.v1",
                "applicable_scope": "project",
                "confidence": 0.86,
                "rights_boundary": "用户提供或项目原创，待创作者确认后进入媒体生成",
                "style": "旧铜金属、磨损边缘",
                "do_not_change": ["铜色材质", "指针方向连续", "相对尺寸"],
            },
            {
                "name": "裂开的玻璃杯",
                "kind": "prop",
                "source": "用户剧本输入的项目道具",
                "version": "candidate.v1",
                "applicable_scope": "project",
                "confidence": 0.84,
                "rights_boundary": "用户提供或项目原创，待创作者确认后进入媒体生成",
                "style": "透明玻璃、杯壁裂纹方向固定",
                "do_not_change": ["裂纹方向", "杯口形状", "桌面位置"],
            },
            {
                "name": "备用电池",
                "kind": "prop",
                "source": "用户剧本输入的项目道具",
                "version": "candidate.v1",
                "applicable_scope": "project",
                "confidence": 0.83,
                "rights_boundary": "用户提供或项目原创，待创作者确认后进入媒体生成",
                "style": "黑色工业电池、磨损标签",
                "do_not_change": ["黑色外壳", "标签方向", "相对尺寸"],
            },
            {
                "name": "玻璃杯裂纹特写",
                "kind": "closeup",
                "source": "用户剧本输入的特写需求",
                "version": "candidate.v1",
                "applicable_scope": "project",
                "confidence": 0.84,
                "rights_boundary": "项目内原创特写，不引用外部图片",
                "style": "裂纹与波形叠化的写实特写",
                "do_not_change": ["裂纹方向", "杯口形状", "桌面位置"],
            },
            {
                "name": "雨季设备空间 ReferenceSet",
                "kind": "reference_set",
                "source": "项目文本抽取的场景和道具连续性参考",
                "version": "candidate.v1",
                "applicable_scope": "project",
                "confidence": 0.81,
                "rights_boundary": "仅项目内文本参考，未含外部图片授权",
                "style": "冷绿色设备灯、雨后湿痕、手电硬光",
                "do_not_change": ["雨季湿痕", "设备灯色", "罗盘和耳机位置"],
            },
            {
                "name": "克制悬疑写实风格",
                "kind": "style",
                "source": "用户剧本输入的风格方向",
                "version": "candidate.v1",
                "applicable_scope": "project",
                "confidence": 0.79,
                "rights_boundary": "风格描述为项目偏好，不声明外部作品复制",
                "style": "克制写实、冷暖对照、窄空间压迫",
                "do_not_change": ["写实比例", "冷暖对照", "低饱和雨季质感"],
            },
        ],
        "shots": [
            {
                "scene_index": 1,
                "duration_seconds": 8.5,
                "intent": "建立观测台空间和罗盘倒转的第一处异常。",
                "character_indexes": [1, 2, 3],
                "asset_indexes": [1, 5],
                "shot_size": "全景",
                "camera_angle": "平视略低",
                "camera_movement": "沿环形轨道缓慢横移",
                "blocking": "米拉在前景扶镜头，阿衡带耳机站在后景设备旁。",
                "sound": "雨后风声和信号电噪逐渐抬高。",
                "transition": "信号声匹配切入",
                "narrative_purpose": "把异常从环境故障推进到可追踪证据。",
                "content_driven_duration_reason": "需要交代空间、三人位置和罗盘状态，因此长于后续特写。",
            },
            {
                "scene_index": 2,
                "duration_seconds": 5.0,
                "intent": "用玻璃裂纹和波形建立证据连接。",
                "character_indexes": [1, 2],
                "asset_indexes": [2, 3, 4, 5],
                "shot_size": "特写",
                "camera_angle": "俯拍",
                "camera_movement": "静止后微推",
                "blocking": "米拉手指停在裂纹旁，监视器波形在后景虚化。",
                "sound": "电池入位声后留出半秒静默。",
                "transition": "图形匹配转场",
                "narrative_purpose": "把抽象频率变成观众能看见的线索。",
                "content_driven_duration_reason": "信息密度集中在道具特写，短镜头足以传递证据。",
            },
            {
                "scene_index": 3,
                "duration_seconds": 11.0,
                "intent": "让阿衡摘下耳机承认旧广播，完成关系变化。",
                "character_indexes": [1, 3],
                "asset_indexes": [1, 5],
                "shot_size": "中景",
                "camera_angle": "平视",
                "camera_movement": "手持轻微后退",
                "blocking": "阿衡站在水管阴影中摘下耳机，米拉没有追问，只稳住镜头。",
                "sound": "水泵声压过第一句对白，旧广播断续出现。",
                "transition": "沉默后切出",
                "narrative_purpose": "把悬疑落到角色责任和下一场戏压力。",
                "content_driven_duration_reason": "承认需要沉默和反应时间，时长由表演节奏决定。",
            },
        ],
    }


def _single_scope_server_codex_payload(character: str, scene: str, prop: str) -> dict[str, object]:
    payload = deepcopy(_server_codex_payload())
    payload["title"] = f"{character}的档案修复"
    payload["logline"] = f"{character}在{scene}完成{prop}修复，并把连续动作拆成可拍镜头。"
    payload["characters"] = [
        {
            **payload["characters"][0],
            "display_name": character,
            "goal": f"在限定时间内完成{prop}修复。",
            "relationship_arc": "单人行动不引入其他人物关系。",
        }
    ]
    payload["scenes"] = [
        {
            **payload["scenes"][0],
            "name": scene,
            "space": f"{scene}的既有空间范围。",
        }
    ]
    payload["assets"] = [
        {
            **payload["assets"][0],
            "name": prop,
            "kind": "prop",
        },
        {
            **payload["assets"][3],
            "name": f"{character}、{scene}与{prop}连续性参考",
            "kind": "reference_set",
        },
    ]
    payload["structure"]["scene_count"] = 1
    for shot in payload["shots"]:
        shot["scene_index"] = 1
        shot["character_indexes"] = [1]
        shot["asset_indexes"] = [1, 2]
    return payload
