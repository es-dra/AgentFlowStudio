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
      console.log(JSON.stringify({{
        projectedCount: projected.length,
        minimumY: Math.min(...projected.map((node) => node.y)),
        sourceBottom: state.nodes.source.y + state.nodes.source.h,
        copilot,
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

    assert result["projectedCount"] == 18
    assert result["minimumY"] > result["sourceBottom"]
    assert result["copilot"]["stage"] == "production_plan_ready"
    assert result["copilot"]["ready_summary"] == "制作方案已保存：3 个角色、2 个场景、5 个镜头。"
    assert result["copilot"]["next_valid_action"]["action"] == "open_storyboard"
    assert result["copilot"]["next_valid_action"]["label"] == "查看故事板"


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
