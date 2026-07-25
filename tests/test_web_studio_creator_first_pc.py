from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "apps" / "studio"


def test_creator_guidance_is_primary_and_diagnostics_are_progressively_disclosed() -> None:
    panel = (STUDIO / "src" / "agent-chat-panel.js").read_text(encoding="utf-8")
    copilot = panel.split("function productionCopilot", 1)[1].split("function contextDetails", 1)[0]
    primary = copilot.split('const details = el("details"', 1)[0]
    diagnostics = copilot.split('const details = el("details"', 1)[1]

    for visible in ("接下来", "已准备", "需要你", "agent-primary-action"):
        assert visible in primary
    for internal in ("生产 Copilot", "阻塞：", "媒体准入", "当前未调用、未计费"):
        assert internal not in primary
    assert 'details.appendChild(el("summary", "", "制作详情"))' in diagnostics
    assert 'evidenceDetails("诊断信息"' in diagnostics
    assert "agent-production-dependencies" in diagnostics

    context = panel.split("function contextStrip", 1)[1].split("function productionCopilot", 1)[0]
    context_primary = context.split("contextDetails(context)", 1)[0]
    assert "正在制作" in context_primary
    assert "agent-context-chip" not in context_primary
    assert "estimated_cost_usd" not in context_primary


def test_confirmation_keeps_full_human_scope_visible_before_diagnostics() -> None:
    panel = (STUDIO / "src" / "agent-chat-panel.js").read_text(encoding="utf-8")
    preview = panel.split("function commandPreview", 1)[1].split("async function executeEmbeddedCreativeCommand", 1)[0]
    visible = preview.split('evidenceDetails("诊断信息"', 1)[0]

    for label in (
        "保存前预览",
        "确认制作方案",
        "当前状态",
        "仅预览，尚未保存",
        "确认后",
        "m6ScopeImpactReview",
    ):
        assert label in visible
    for label in ("确认并保存", "继续修改"):
        assert label in preview
    for internal_label in ('el("dt", "", "工具")', 'el("dt", "", "能力")', 'el("dt", "", "费用")'):
        assert internal_label not in visible

    scope = panel.split("function m6ScopeImpactReview", 1)[1].split("function evidenceDetails", 1)[0]
    for label in ("新建内容", "名称变化", "内容补充", "资产用途", "影响的镜头与引用"):
        assert label in scope
    for label in ("主要角色", "主要场景", "主要道具", "制作参考"):
        assert label in scope
    for leaked_label in (
        "规范角色 canonical_character",
        "规范场景 canonical_scene",
        "规范道具 canonical_prop",
        "生产辅助 production_aid",
    ):
        assert leaked_label not in scope


def test_empty_project_canvas_and_agent_offer_the_same_enabled_next_action() -> None:
    module_uri = (STUDIO / "src" / "asset-bible-workspace.js").as_uri()
    script = f"""
      import {{ deriveProductionCopilotState }} from {json.dumps(module_uri)};
      const state = {{
        nodes: {{}},
        edges: {{}},
        selection: {{ nodeIds: [] }},
        production: {{}},
      }};
      const result = deriveProductionCopilotState({{
        studioState: state,
        capabilityGates: {{ llm: false, image: false, video: false }},
        section: "canvas",
      }});
      console.log(JSON.stringify(result));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)

    assert result["next_valid_action"] == {
        "action": "start_idea",
        "label": "输入创作想法",
        "reason": "先描述故事、角色或一个画面，AI 创作搭档会和画布一起继续。",
        "enabled": True,
    }
    assert result["ready_summary"] == "项目已创建，可以从一个想法开始。"

    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    assert 'action.action === "start_idea"' in shell
    assert '".canvas-empty-onboarding textarea"' in shell
    assert "agentCollapsed = isNarrowAgentLayout();" in shell
    assert "agentCollapsed = true;" not in shell
    display_name = shell.split("function projectDisplayName()", 1)[1].split("function projectIdentityStatus()", 1)[0]
    assert "snapshot.project?.project_id" not in display_name
    assert '|| "未命名项目"' in display_name


def test_failed_plan_projects_offer_same_run_recovery_instead_of_starting_over() -> None:
    module_uri = (STUDIO / "src" / "asset-bible-workspace.js").as_uri()
    script = f"""
      import {{ deriveProductionCopilotState }} from {json.dumps(module_uri)};
      const result = deriveProductionCopilotState({{
        studioState: {{
          nodes: {{ idea: {{ id: "idea", type: "text", content: "已有创作想法" }} }},
          production: {{}},
        }},
        capabilityGates: {{ llm: true, image: false, video: false }},
        section: "canvas",
        planningRun: {{
          run_id: "failed-plan-run",
          phase: "failed",
          dispatch_count: 1,
          error: {{ message: "制作方案未通过结构校验；制作事实未改变。" }},
        }},
      }});
      console.log(JSON.stringify(result));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)

    assert result["stage"] == "plan_recovery_required"
    assert result["ready_summary"] == "制作方案未通过检查，现有项目内容未改变。"
    assert result["needs_input"] == "检查失败原因并恢复同一预览。"
    assert result["next_valid_action"] == {
        "action": "recover_plan_preview",
        "label": "恢复制作方案",
        "reason": "查看同一任务的失败状态和原始输入，不会再次提交文本任务。",
        "enabled": True,
    }
    assert result["provider_dispatch_count"] == 1
    assert result["external_cost_usd"] is None

    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    assert 'action.action === "recover_plan_preview"' in shell
    assert "writeM6SourceDraft(currentM6SourceDraftKey(), m6SourceText)" in shell
    assert "writeM6SourceDraft(currentM6SubmittedSourceKey(), m6SourceText)" in shell
    assert "readM6SourceDraft(currentM6SubmittedSourceKey())" in shell
    assert ': readM6SourceDraft(currentM6SourceDraftKey())' in shell
    assert "sessionStorage" in shell
    assert 'planningPanelPreferenceKey !== "afs:m6:plan-panel:studio"' in shell
    assert "enteringLoadedProject && m6SourceDraftDirty && m6SourceText" in shell
    version_bar = shell.split("function buildVersionBar()", 1)[1].split("function buildAgentChat()", 1)[0]
    assert "script.disabled = !sceneAvailable" in version_bar
    assert "先完成制作方案并建立场景" in version_bar


def test_plan_in_progress_projects_do_not_offer_the_idle_start_action() -> None:
    module_uri = (STUDIO / "src" / "asset-bible-workspace.js").as_uri()
    script = f"""
      import {{ deriveProductionCopilotState }} from {json.dumps(module_uri)};
      const result = deriveProductionCopilotState({{
        studioState: {{
          nodes: {{ idea: {{ id: "idea", type: "text", content: "已有创作想法" }} }},
          production: {{}},
        }},
        capabilityGates: {{ llm: true, image: false, video: false }},
        section: "canvas",
        planningRun: {{
          run_id: "active-plan-run",
          phase: "running",
          dispatch_count: 1,
        }},
      }});
      console.log(JSON.stringify(result));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)

    assert result["stage"] == "plan_in_progress"
    assert result["ready_summary"] == "制作方案正在准备。"
    assert result["needs_input"] == "当前无需重复提交创作想法。"
    assert result["next_valid_action"] == {
        "action": "view_plan_progress",
        "label": "查看制作进度",
        "reason": "制作方案正在准备；可以查看同一任务的进度。",
        "enabled": True,
    }
    assert result["provider_dispatch_count"] == 1
    assert result["external_cost_usd"] is None
    assert "项目已创建，可以从一个想法开始" not in json.dumps(result, ensure_ascii=False)
    assert "输入创作想法" not in json.dumps(result, ensure_ascii=False)

    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    assert 'action.action === "view_plan_progress"' in shell
    assert 'document.querySelector(".m6-preview-run-status")?.focus()' in shell
    assert "panel.tabIndex = -1" in shell


def test_media_result_context_offers_review_instead_of_starting_over() -> None:
    module_uri = (STUDIO / "src" / "asset-bible-workspace.js").as_uri()
    script = f"""
      import {{ deriveProductionCopilotState }} from {json.dumps(module_uri)};
      const result = deriveProductionCopilotState({{
        studioState: {{}},
        capabilityGates: {{ llm: false, image: false, video: false }},
        section: "storyboard",
        mediaOperations: {{
          schema_version: "afs.media_operations_review.v0.1",
          summary: {{ shot_count: 3, ready_shot_count: 2 }},
          shots: [{{ shot_id: "one" }}, {{ shot_id: "two" }}, {{ shot_id: "three" }}],
          stage: {{ next_action: "审看镜头并确认连续性。" }},
          advanced_evidence: {{ provider_dispatch_count: 0 }},
        }},
      }});
      console.log(JSON.stringify(result));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)

    assert result["stage"] == "media_review"
    assert result["ready_summary"] == "2/3 个镜头可以审看。"
    assert result["needs_input"] == "审看镜头并确认连续性。"
    assert result["next_valid_action"] == {
        "action": "review_current_shot",
        "label": "播放当前镜头",
        "reason": "审看镜头并确认连续性。",
        "enabled": True,
    }
    assert result["provider_dispatch_count"] == 0

    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    assert 'action.action === "review_current_shot"' in shell
    assert "mediaOperations: mediaOperationsReady() ? mediaOperationsView() : null" in shell


def test_confirmed_production_graph_offers_storyboard_review_and_has_no_overlapping_projection_nodes() -> None:
    copilot_uri = (STUDIO / "src" / "asset-bible-workspace.js").as_uri()
    projection_uri = (STUDIO / "src" / "production-graph-workspace-projection.js").as_uri()
    script = f"""
      import {{ deriveProductionCopilotState }} from {json.dumps(copilot_uri)};
      import {{ applyProductionGraphCanvasProjection, productionGraphWorkspaceProjection }} from {json.dumps(projection_uri)};
      const records = (prefix, count) => Array.from({{ length: count }}, (_, index) => ({{
        node_id: `${{prefix}}-${{index + 1}}`,
        state: "active",
        metadata: {{ title: `${{prefix}} ${{index + 1}}` }},
      }}));
      const workspace = {{
        status: "ready",
        graph_version: 3,
        graph_digest: "graph-digest",
        storyboard: {{ graph_version: 3, graph_digest: "graph-digest" }},
        sequence: {{
          script_revisions: records("script", 1),
          sequences: records("sequence", 1),
          characters: records("character", 3),
          scenes: records("scene", 2),
          props: records("prop", 2),
          reference_sets: records("reference", 4),
          production_aids: records("aid", 3),
          shots: records("shot", 5),
          dependencies: [],
          tasks: [],
          candidates: [],
          selections: [],
          reviews: [],
          delivery_plan: [],
          version_history: [],
        }},
      }};
      workspace.sequence.script_revisions.push({{
        node_id: "script-history",
        state: "invalidated",
        metadata: {{ title: "historical script" }},
      }});
      const state = {{
        nodes: {{ source: {{ id: "source", x: 80, y: 80, w: 280, h: 190, params: {{}} }} }},
        edges: {{}},
        order: ["source"],
        selection: {{ nodeIds: [], edgeId: null }},
        production: {{}},
      }};
      applyProductionGraphCanvasProjection(state, workspace);
      const projected = Object.values(state.nodes).filter((node) => node.params?.productionGraphProjection);
      for (let index = 0; index < projected.length; index += 1) {{
        for (let other = index + 1; other < projected.length; other += 1) {{
          const a = projected[index];
          const b = projected[other];
          const overlaps = a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
          if (overlaps) throw new Error(`overlap:${{a.id}}:${{b.id}}`);
        }}
      }}
      const graph = productionGraphWorkspaceProjection(workspace);
      const copilot = deriveProductionCopilotState({{
        studioState: {{}},
        capabilityGates: {{ llm: true, image: false, video: false }},
        section: "canvas",
        productionGraph: graph,
      }});
      const bibleCopilot = deriveProductionCopilotState({{
        studioState: {{}},
        capabilityGates: {{ llm: true, image: false, video: false }},
        section: "asset_bible",
        productionGraph: graph,
      }});
      console.log(JSON.stringify({{
        projectedCount: projected.length,
        minimumY: Math.min(...projected.map((node) => node.y)),
        sourceBottom: state.nodes.source.y + state.nodes.source.h,
        copilot,
        bibleCopilot,
      }}));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)

    assert result["projectedCount"] == 19
    assert result["minimumY"] > result["sourceBottom"]
    assert result["copilot"]["stage"] == "production_plan_ready"
    assert result["copilot"]["dependencies"][0] == {
        "key": "script",
        "label": "当前剧本",
        "state": "ready",
    }
    assert result["copilot"]["ready_summary"] == "制作方案已保存：3 个角色、2 个场景、5 个镜头。"
    assert result["copilot"]["next_valid_action"]["action"] == "open_storyboard"
    assert result["copilot"]["next_valid_action"]["label"] == "查看故事板"
    assert result["bibleCopilot"]["next_valid_action"] == {
        "action": "generate_asset_candidates",
        "label": "识别资产候选",
        "reason": "基于已保存的角色、场景、道具和镜头建立可审核资产候选。",
        "enabled": True,
    }


def test_canvas_storyboard_bible_and_agent_remain_one_product_graph_projection() -> None:
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    projection = (STUDIO / "src" / "production-graph-workspace-projection.js").read_text(encoding="utf-8")

    for view in ('viewButton("canvas", "画布")', 'viewButton("storyboard", "故事板")', 'viewButton("asset_bible", "资产 Bible")'):
        assert view in shell
    assert "buildAgentChatPanel" in shell
    assert "productionGraphWorkspaceProjection(snapshot.sequenceWorkspace)" in shell
    assert "productionGraphAgentContext" in shell
    assert "canonical_production_graph" in projection
    for forbidden in ("secondProductionGraph", "secondaryGraphStore", "creatorShellGraph"):
        assert forbidden not in shell


def test_confirmed_graph_projects_asset_bible_source_across_refresh_without_preview_leakage() -> None:
    bible_uri = (STUDIO / "src" / "asset-bible-workspace.js").as_uri()
    script = f"""
      import {{ assetBibleSourceContext, deriveProductionCopilotState }} from {json.dumps(bible_uri)};
      const workspace = {{
        status: "ready",
        graph_version: 8,
        graph_digest: "confirmed-graph-digest",
        storyboard: {{ graph_version: 8, graph_digest: "confirmed-graph-digest" }},
        sequence: {{
          script_revisions: [
            {{ node_id: "revision-8", state: "active", metadata: {{ source_digest: "source" }} }},
          ],
          characters: [
            {{ node_id: "character-nova", state: "active", metadata: {{ display_name: "Nova Reed" }} }},
          ],
          scenes: [
            {{ node_id: "scene-copper-quay", state: "active", metadata: {{ name: "Copper Quay", space: "rain-washed quay" }} }},
          ],
          props: [
            {{ node_id: "prop-glass-compass", state: "active", metadata: {{ name: "Glass Compass", kind: "prop", classification: "canonical_prop" }} }},
          ],
          production_aids: [
            {{ node_id: "aid-weather", state: "active", metadata: {{ name: "Weather Reference", classification: "production_aid" }} }},
          ],
          shots: [
            {{ node_id: "shot-a", state: "active", metadata: {{ intent: "find north", duration_seconds: 4 }} }},
            {{ node_id: "shot-b", state: "active", metadata: {{ intent: "cross the quay", duration_seconds: 7 }} }},
          ],
          dependencies: [
            {{ from_id: "revision-8", to_id: "character-nova", relation_type: "derived_from" }},
            {{ from_id: "revision-8", to_id: "scene-copper-quay", relation_type: "derived_from" }},
            {{ from_id: "revision-8", to_id: "prop-glass-compass", relation_type: "derived_from" }},
            {{ from_id: "revision-8", to_id: "aid-weather", relation_type: "derived_from" }},
            {{ from_id: "scene-copper-quay", to_id: "shot-a", relation_type: "contains" }},
            {{ from_id: "scene-copper-quay", to_id: "shot-b", relation_type: "contains" }},
          ],
        }},
      }};
      const failedPreviewOnlyState = {{
        nodes: {{}},
        planningRun: {{
          phase: "failed",
          source_text: "This failed preview must not become Asset Bible truth.",
        }},
      }};
      const first = assetBibleSourceContext(failedPreviewOnlyState, workspace);
      const refreshed = assetBibleSourceContext({{}}, JSON.parse(JSON.stringify(workspace)));
      const failedOnly = assetBibleSourceContext(failedPreviewOnlyState, {{
        status: "planning_required",
        graph_version: 0,
      }});
      const ambiguous = JSON.parse(JSON.stringify(workspace));
      ambiguous.sequence.script_revisions.push({{
        node_id: "revision-history",
        state: "active",
        metadata: {{ source_digest: "historical" }},
      }});
      const legacyShotPlan = {{
        candidate_id: "legacy-candidate",
        scenes: [{{
          scene_id: "legacy-scene",
          name: "Legacy Stage",
          shots: [{{ shot_id: "legacy-shot", title: "Legacy Shot", duration_sec: 5 }}],
        }}],
      }};
      const legacyState = {{
        nodes: {{
          story: {{
            id: "story",
            type: "text",
            content: "Legacy source that must not override canonical fail-closed state.",
            params: {{
              currentRevisionId: "legacy-revision",
              revisions: [{{
                revision_id: "legacy-revision",
                screenplay_candidate: {{
                  screenplay_text: "Legacy source that must not override canonical fail-closed state.",
                }},
              }}],
              shotPlanDraft: {{ ...legacyShotPlan, source_revision_id: "legacy-revision" }},
              embeddedCreativeAction: {{
                action_type: "shot_breakdown",
                status: "applied",
                applied_at: "2026-07-24T00:00:00Z",
                applied_revision_id: "legacy-revision",
                applied_subgraph: {{
                  candidate_id: "legacy-candidate",
                  shot_plan: legacyShotPlan,
                }},
              }},
            }},
          }},
          sequence: {{
            id: "sequence",
            type: "sequence",
            params: {{
              nodeRole: "m6_6_shot_sequence_candidate",
              candidate_id: "legacy-candidate",
              source_revision_id: "legacy-revision",
            }},
          }},
          scene: {{
            id: "scene",
            type: "scene",
            title: "Legacy Stage",
            params: {{
              nodeRole: "m6_6_scene_candidate",
              candidate_id: "legacy-candidate",
              source_revision_id: "legacy-revision",
              source_sequence_node_id: "sequence",
            }},
          }},
          shot: {{
            id: "shot",
            type: "shot",
            title: "Legacy Shot",
            params: {{
              nodeRole: "m6_6_shot_candidate",
              candidate_id: "legacy-candidate",
              source_revision_id: "legacy-revision",
              source_scene_node_id: "scene",
              duration_sec: 5,
            }},
          }},
        }},
        edges: {{
          source: {{ from: "story", to: "sequence", relation_type: "proposed" }},
          scene: {{ from: "sequence", to: "scene", relation_type: "sequence" }},
          shot: {{ from: "scene", to: "shot", relation_type: "sequence" }},
        }},
      }};
      const legacySource = assetBibleSourceContext(legacyState, null);
      const ambiguousSource = assetBibleSourceContext(legacyState, ambiguous);
      const ambiguousCopilot = deriveProductionCopilotState({{
        studioState: legacyState,
        capabilityGates: {{ llm: true, image: false, video: false }},
        section: "asset_bible",
        productionGraph: {{
          status: "ready",
          shots: [{{ graphNodeId: "shot-a" }}, {{ graphNodeId: "shot-b" }}],
          summary: {{
            scriptRevisions: 2,
            characters: 1,
            locations: 1,
            props: 1,
          }},
        }},
      }});
      console.log(JSON.stringify({{
        first,
        refreshed,
        failedOnly,
        legacySource,
        ambiguousSource,
        ambiguousCopilot,
      }}));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    first = result["first"]

    assert first == result["refreshed"]
    assert result["failedOnly"] is None
    assert result["ambiguousSource"] is None
    assert "authority_mode" not in result["legacySource"]
    assert result["legacySource"]["script_revision_id"] == "legacy-revision"
    assert result["ambiguousCopilot"]["stage"] == "production_plan_revision_conflict"
    assert result["ambiguousCopilot"]["next_valid_action"] == {
        "action": "resolve_script_revision",
        "label": "等待版本确认",
        "reason": "当前存在多个已应用剧本版本，确认唯一版本后才能整理资产。",
        "enabled": False,
    }
    assert first["authority_mode"] == "canonical_production_graph"
    assert first["script_revision_id"] == "revision-8"
    assert first["scene_count"] == 1
    assert first["shot_count"] == 2
    assert first["duration_sec"] == 11
    assert [
        (item["asset_type"], item["display_name"])
        for item in first["canonical_assets"]
    ] == [
        ("character", "Nova Reed"),
        ("scene", "Copper Quay"),
        ("prop", "Glass Compass"),
    ]
    assert [item["display_name"] for item in first["production_aids"]] == [
        "Weather Reference"
    ]
    assert first["provider_dispatch_count"] == 0
    assert first["external_cost_usd"] == 0

    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    assert shell.count(
        "assetBibleSourceContext(snapshot.studioState || {}, snapshot.sequenceWorkspace)"
    ) == 3
    assert "source?.canonical_assets?.length" in shell
    assert "项来源已确认" in shell
