from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _create_project(client: TestClient, project_id: str) -> None:
    response = client.post(
        "/projects",
        json={
            "project_id": project_id,
            "project_type": "freeform_canvas",
            "goal": "embedded creative action test",
            "status": "in_progress",
        },
    )
    assert response.status_code == 200, response.text


def _creative_action_request(**overrides) -> dict:
    payload = {
        "action_type": "script_revision",
        "node_id": "idea_node_1",
        "node_type": "text",
        "source_text": "孙悟空大战猪八戒。",
        "mode": "professional_expansion",
        "context_summary": {
            "project_name": "节点内创作测试",
            "selected_node_title": "短想法",
            "selected_node_type": "text",
            "selected_node_status": "draft",
            "counts": {"nodes": 1, "scenes": 0, "shots": 0},
            "section": "canvas",
        },
        "constraints": ["普通优化必须保持同一节点身份。", "确认前不改动画布。"],
        "provider_service_id": "server_codex",
        "generated_at": "2026-07-22T12:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_embedded_creative_action_gate_closed_is_preview_only_unavailable(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "embedded-action-unavailable"
    _create_project(client, project_id)
    before = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]

    response = client.post(
        f"/projects/{project_id}/embedded-creative-actions/preview",
        json=_creative_action_request(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "unavailable"
    assert payload["provider_calls_started"] is False
    assert "不会使用本地模板冒充专业改写" in payload["preview"]["rationale"]
    assert payload["graph_mutation"]["mutated"] is False
    after = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert after["version"] == before["version"]
    assert after["graph_digest"] == before["graph_digest"]


def test_embedded_script_revision_uses_server_codex_schema_and_preserves_graph(tmp_path, monkeypatch) -> None:
    calls = []

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            calls.append((capability, service_id, request))
            return {
                "provider_calls_started": True,
                "structured_output": {
                    "action_type": "script_revision",
                    "mode": "professional_expansion",
                    "revised_text": (
                        "花果山傍晚，孙悟空误以为猪八戒偷吃了给师父准备的供果，举棒逼问。"
                        "猪八戒一边躲闪一边护着篮子，嘴上求饶却仍惦记最后一口甜桃。"
                        "两人的打斗从玩笑升级到真怒，又在发现妖怪踪迹时转成默契联手。"
                    ),
                    "change_summary": ["补足冲突起因和人物目标", "加入动作、对白节奏和关系变化"],
                    "rationale": "这版把短想法扩写成可继续拆分的戏剧场面，同时保留同一节点身份。",
                    "unresolved_decisions": ["是否加入唐僧旁观反应"],
                    "quality_flags": ["preview_only"],
                    "screenplay_candidate": {
                        "title": "花果山误会",
                        "version_label": "v1",
                        "logline": "孙悟空误会猪八戒偷吃供果，两人从嬉闹冲突转向发现妖怪踪迹后的默契联手。",
                        "characters": [
                            {
                                "name": "孙悟空",
                                "goal": "查清供果失踪并保护师父",
                                "conflict": "急躁误判八戒，几乎错过真正妖怪线索",
                                "change": "从追问压迫转为听取解释并主动联手",
                            },
                            {
                                "name": "猪八戒",
                                "goal": "证明自己没有偷吃并保住最后一篮供果",
                                "conflict": "馋嘴名声让解释缺乏可信度",
                                "change": "从躲闪辩解转为指出妖气并配合行动",
                            },
                        ],
                        "scenes": [
                            {
                                "heading": "外景 - 花果山果林 - 傍晚",
                                "space_type": "外景",
                                "location": "花果山果林",
                                "time_of_day": "傍晚",
                                "purpose": "建立误会、关系冲突和转向联手的线索",
                                "blocks": [
                                    {"type": "action", "text": "空篮倒在石阶旁，桃核滚进草丛，孙悟空握紧金箍棒逼近猪八戒。"},
                                    {"type": "character", "text": "孙悟空"},
                                    {"type": "dialogue", "text": "呆子，供果少了三颗，你还敢护着篮子？"},
                                    {"type": "character", "text": "猪八戒"},
                                    {"type": "dialogue", "text": "猴哥，我只闻了闻，真动手的是林子里那股腥风。"},
                                    {"type": "action", "text": "两人的追打戛然而止，枝头黑影掠过，八戒把篮子递回，悟空抬眼锁定妖气。"},
                                ],
                            }
                        ],
                    },
                },
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_embedded_creative_actions.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "embedded-action-llm"
    _create_project(client, project_id)
    before = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]

    response = client.post(
        f"/projects/{project_id}/embedded-creative-actions/preview",
        json=_creative_action_request(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "llm"
    assert payload["provider_calls_started"] is True
    assert payload["provider_lineage"]["service_id"] == "server_codex"
    assert payload["provider_lineage"]["provider"] == "codex_local"
    assert payload["provider_lineage"]["structured_output_contract_id"] == "afs.runtime.embedded_creative_action.v0.2"
    assert payload["provider_lineage"]["provider_dispatch_count"] == 1
    assert payload["provider_lineage"]["repair_attempted"] is False
    assert payload["safe_manifest"]["provider_dispatch_count"] == 1
    assert payload["safe_manifest"]["repair_attempted"] is False
    assert payload["preview"]["revised_text"].startswith("《花果山误会》")
    assert "外景 - 花果山果林 - 傍晚" in payload["preview"]["revised_text"]
    assert payload["preview"]["screenplay_candidate"]["scenes"][0]["heading"].startswith("外景")
    assert payload["preview"]["screenplay_candidate"]["scenes"][0]["space_type"] == "外景"
    assert payload["graph_mutation"]["mutated"] is False
    after = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert after["version"] == before["version"]
    assert after["graph_digest"] == before["graph_digest"]
    assert calls and calls[0][0] == "llm"
    assert calls[0][1] == "server_codex"
    request = calls[0][2]
    assert request.structured_output_contract_id == "afs.runtime.embedded_creative_action.v0.2"
    assert request.structured_output_schema_digest
    assert "不修改画布" in request.prompt
    assert "孙悟空大战猪八戒" in request.prompt
    assert "固定4x15/10x6" in request.prompt
    assert "screenplay_candidate" in request.prompt


def test_embedded_script_revision_rejects_prose_without_screenplay_candidate(tmp_path, monkeypatch) -> None:
    calls = []

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            calls.append(request)
            return {
                "provider_calls_started": True,
                "structured_output": {
                    "action_type": "script_revision",
                    "mode": "professional_expansion",
                    "revised_text": "孙悟空和猪八戒在花果山发生冲突，后来发现妖怪踪迹并联手追击。这个故事强调误会和伙伴关系。",
                    "change_summary": ["只有散文扩写", "没有专业剧本结构"],
                    "rationale": "这是一段散文故事，不是剧本候选。",
                    "unresolved_decisions": [],
                    "quality_flags": ["prose_only"],
                },
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_embedded_creative_actions.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "embedded-action-prose-rejected"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/embedded-creative-actions/preview",
        json=_creative_action_request(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "unavailable"
    assert payload["provider_calls_started"] is True
    assert payload["provider_lineage"]["provider_calls_started"] is True
    assert payload["safe_manifest"]["fallback_reason"] == "unsafe_or_invalid_llm_preview"
    assert payload["safe_manifest"]["validation_error_category"] == "screenplay_candidate_missing"
    assert payload["provider_lineage"]["validation_error_category"] == "screenplay_candidate_missing"
    assert payload["creative_task"]["error_detail"] == "screenplay_candidate_missing"
    assert payload["safe_manifest"]["provider_calls_started"] is True
    assert payload["safe_manifest"]["provider_dispatch_count"] == 2
    assert payload["safe_manifest"]["repair_attempted"] is True
    assert payload["creative_task"]["error_category"] == "unsafe_or_invalid_llm_preview"
    assert payload["creative_task"]["error_owner"] == "provider_output_validation"
    assert len(calls) == 2
    assert "provider-backed 修复重试" in calls[1].prompt


def test_embedded_script_revision_rejects_dangling_character_cue(tmp_path, monkeypatch) -> None:
    calls = []

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            calls.append(request)
            return {
                "provider_calls_started": True,
                "structured_output": {
                    "action_type": "script_revision",
                    "mode": "professional_expansion",
                    "revised_text": "《停机之后》\n内景 - 旧摄影棚 - 夜\n林澈\n\n下一场继续。",
                    "change_summary": ["尝试输出剧本格式", "但人物提示悬空"],
                    "rationale": "这段结果故意留下悬空人物名，应该被安全验证拒绝。",
                    "unresolved_decisions": [],
                    "quality_flags": ["dangling_character_cue"],
                    "screenplay_candidate": {
                        "title": "停机之后",
                        "version_label": "v1",
                        "logline": "导演与制片人在停电摄影棚里围绕是否继续拍摄发生冲突。",
                        "characters": [
                            {"name": "林澈", "goal": "拍完最后一条", "conflict": "被预算和停电影响", "change": "从执拗转为承担风险"},
                            {"name": "许岚", "goal": "控制预算和安全", "conflict": "必须阻止导演冒险", "change": "从否决转为要求边界"},
                        ],
                        "scenes": [{
                            "heading": "内景 - 旧摄影棚 - 夜",
                            "space_type": "内景",
                            "location": "旧摄影棚",
                            "time_of_day": "夜",
                            "purpose": "建立导演与制片人的正面冲突",
                            "blocks": [
                                {"type": "action", "text": "停电后的摄影棚只剩应急灯，林澈盯着黑屏。"},
                                {"type": "character", "text": "林澈"},
                                {"type": "action", "text": "许岚把预算表放到监视器旁，示意所有人收工。"},
                            ],
                        }],
                    },
                },
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_embedded_creative_actions.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "embedded-action-dangling-cue-rejected"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/embedded-creative-actions/preview",
        json=_creative_action_request(source_text="林澈和许岚在停电摄影棚争执是否继续拍。"),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "unavailable"
    assert payload["provider_calls_started"] is True
    assert payload["safe_manifest"]["fallback_reason"] == "unsafe_or_invalid_llm_preview"
    assert payload["creative_task"]["error_owner"] == "provider_output_validation"
    assert len(calls) == 2


def test_embedded_script_revision_normalizes_speaker_prefixed_dialogue_blocks(tmp_path, monkeypatch) -> None:
    calls = []

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            calls.append(request)
            return {
                "provider_calls_started": True,
                "structured_output": {
                    "action_type": "script_revision",
                    "mode": "professional_expansion",
                    "revised_text": "模型返回的可读投影会被 typed screenplay candidate 覆盖。",
                    "change_summary": ["保留棚内争执", "把中文人物冒号对白规范为剧本块"],
                    "rationale": "真实模型常以人物冒号 shorthand 返回中文对白，应用层应规范化为专业剧本块而不是误判失败。",
                    "unresolved_decisions": [],
                    "quality_flags": ["provider_structured_preview"],
                    "screenplay_candidate": {
                        "title": "停电十分钟",
                        "version_label": "v1",
                        "logline": "导演与制片人在旧摄影棚停电后围绕继续拍摄发生正面冲突。",
                        "characters": [
                            {
                                "name": "林澈",
                                "goal": "证明必须拍完最后一条",
                                "conflict": "停电和预算压力让他失去控制权",
                                "change": "从强撑转为承认需要边界",
                            },
                            {
                                "name": "许岚",
                                "goal": "守住预算和现场安全",
                                "conflict": "导演的执念可能拖垮团队",
                                "change": "从阻止转为提出可执行条件",
                            },
                        ],
                        "scenes": [{
                            "heading": "内景 - 旧摄影棚 - 夜",
                            "space_type": "内景",
                            "location": "旧摄影棚",
                            "time_of_day": "夜",
                            "purpose": "通过停电后的争执建立两人的目标、冲突和信任裂缝",
                            "blocks": [
                                {"type": "action", "text": "应急灯把布景切成几块冷色阴影，监视器黑屏后仍有电流声。"},
                                {"type": "dialogue", "text": "林澈：不是机器坏了，是它不想让我们拍完。"},
                                {"type": "dialogue", "text": "许岚：再等十分钟，我们就赔不起了。"},
                                {"type": "action", "text": "林澈扶住镜头，许岚把预算表压在场记板上，两人都没有退开。"},
                            ],
                        }],
                    },
                },
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_embedded_creative_actions.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "embedded-action-speaker-prefix-normalized"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/embedded-creative-actions/preview",
        json=_creative_action_request(source_text="林澈和许岚在停电摄影棚争执是否继续拍。"),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "llm"
    blocks = payload["preview"]["screenplay_candidate"]["scenes"][0]["blocks"]
    assert [block["type"] for block in blocks] == ["action", "character", "dialogue", "character", "dialogue", "action"]
    assert blocks[1]["text"] == "林澈"
    assert blocks[2]["text"] == "不是机器坏了，是它不想让我们拍完。"
    assert payload["provider_lineage"]["provider_dispatch_count"] == 1
    assert len(calls) == 1


def test_embedded_script_revision_repairs_invalid_structured_output_with_provider_retry(tmp_path, monkeypatch) -> None:
    calls = []

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            calls.append(request)
            if len(calls) == 1:
                return {
                    "provider_calls_started": True,
                    "structured_output": {
                        "action_type": "script_revision",
                        "mode": "professional_expansion",
                        "revised_text": "孙悟空和猪八戒发生误会，然后一起发现妖怪线索。",
                        "change_summary": ["散文扩写", "缺少剧本候选"],
                        "rationale": "第一轮故意缺少专业剧本结构。",
                        "unresolved_decisions": [],
                        "quality_flags": ["needs_repair"],
                    },
                }
            return {
                "provider_calls_started": True,
                "structured_output": {
                    "action_type": "script_revision",
                    "mode": "professional_expansion",
                    "revised_text": "修复后把短想法转换成有标题、人物目标、场景动作和对白的专业剧本预览，仍保持当前节点身份。",
                    "change_summary": ["补齐专业剧本结构", "保留同一节点预览"],
                    "rationale": "修复轮基于同一原文重新生成 closed schema 结构。",
                    "unresolved_decisions": [],
                    "quality_flags": ["provider_backed_repair"],
                    "screenplay_candidate": {
                        "title": "花果山误会",
                        "version_label": "repair-v1",
                        "logline": "悟空误会八戒偷吃供果，两人在冲突中发现真正妖怪线索。",
                        "characters": [
                            {"name": "孙悟空", "goal": "查清供果去向", "conflict": "急躁误判八戒", "change": "从逼问转为联手"},
                            {"name": "猪八戒", "goal": "证明自己清白", "conflict": "馋嘴名声不被信任", "change": "从躲闪转为指出妖气"},
                        ],
                        "scenes": [{
                            "heading": "外景 - 花果山果林 - 傍晚",
                            "space_type": "外景",
                            "location": "花果山果林",
                            "time_of_day": "傍晚",
                            "purpose": "让误会从争执转为共同发现线索",
                            "blocks": [
                                {"type": "action", "text": "空篮倒在石阶旁，孙悟空握棒挡住猪八戒退路。"},
                                {"type": "character", "text": "孙悟空"},
                                {"type": "dialogue", "text": "呆子，供果少了三颗，你还护着篮子？"},
                                {"type": "character", "text": "猪八戒"},
                                {"type": "dialogue", "text": "猴哥，我真没偷，是林子里那股腥风先来过。"},
                                {"type": "action", "text": "枝头黑影掠过，两人同时停手，转向妖气深处。"},
                            ],
                        }],
                    },
                },
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_embedded_creative_actions.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "embedded-action-provider-repair"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/embedded-creative-actions/preview",
        json=_creative_action_request(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "llm"
    assert payload["provider_calls_started"] is True
    assert payload["provider_lineage"]["provider_dispatch_count"] == 2
    assert payload["provider_lineage"]["repair_attempted"] is True
    assert payload["safe_manifest"]["provider_dispatch_count"] == 2
    assert payload["safe_manifest"]["repair_attempted"] is True
    assert payload["preview"]["screenplay_candidate"]["version_label"] == "repair-v1"
    assert len(calls) == 2
    assert "provider-backed 修复重试" in calls[1].prompt


def test_embedded_shot_breakdown_returns_dynamic_preview_without_creating_shots(tmp_path, monkeypatch) -> None:
    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            return {
                "provider_calls_started": True,
                "structured_output": {
                    "action_type": "shot_breakdown",
                    "mode": "dynamic_shot_breakdown",
                    "revised_text": (
                        "这一场可拆成三段动作：误会、追打、共同发现妖怪踪迹。"
                        "悟空的压迫、八戒的闪躲和两人突然停手的节奏都需要明确镜头目的，"
                        "每个镜头时长由动作节拍和信息揭示决定，不套用固定数量模板。"
                    ),
                    "change_summary": ["按内容拆为三段", "每个镜头都有叙事目的"],
                    "rationale": "分镜草案只作为当前节点预览，等待用户确认后再派生具体镜头。",
                    "unresolved_decisions": [],
                    "quality_flags": ["dynamic_count"],
                    "shot_plan": {
                        "total_shots": 3,
                        "estimated_duration_sec": 21,
                        "scenes": [{
                            "title": "花果山误会",
                            "purpose": "从误会推进到联手",
                            "shots": [
                                {
                                    "title": "供果空篮",
                                    "duration_sec": 5,
                                    "shot_size": "中近景",
                                    "camera_angle": "略低机位",
                                    "movement": "缓慢推进到空篮",
                                    "blocking": "悟空压近，八戒后退护篮",
                                    "sound": "风声与桃核落地声",
                                    "transition": "动作切",
                                    "narrative_purpose": "建立误会证据",
                                },
                                {
                                    "title": "棍耙交错",
                                    "duration_sec": 9,
                                    "shot_size": "全景转近景",
                                    "camera_angle": "侧向跟拍",
                                    "movement": "横移追随两人绕树",
                                    "blocking": "悟空追打，八戒躲闪解释",
                                    "sound": "金属碰撞和急促喘息",
                                    "transition": "节奏切",
                                    "narrative_purpose": "把冲突推到最高点",
                                },
                            ],
                        }],
                    },
                },
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_embedded_creative_actions.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "embedded-action-shot-plan"
    _create_project(client, project_id)
    before = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]

    response = client.post(
        f"/projects/{project_id}/embedded-creative-actions/preview",
        json=_creative_action_request(
            action_type="shot_breakdown",
            mode="dynamic_shot_breakdown",
            node_type="script",
            source_text="悟空和八戒因为供果争执，最后发现妖怪踪迹。",
        ),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "llm"
    assert payload["preview"]["shot_plan"]["total_shots"] == 2
    assert payload["preview"]["shot_plan"]["estimated_duration_sec"] == 21
    assert payload["graph_mutation"]["mutated"] is False
    after = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert after["version"] == before["version"]
    assert after["graph_digest"] == before["graph_digest"]
