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


def test_approved_keyframe_projects_into_storyboard_from_the_same_graph_after_refresh() -> None:
    projection_uri = (STUDIO / "src" / "production-graph-workspace-projection.js").as_uri()
    script = f"""
      import {{ productionGraphWorkspaceProjection }} from {json.dumps(projection_uri)};
      const workspace = {{
        status: "ready",
        project_id: "project-refresh",
        graph_version: 14,
        graph_digest: "graph-v14",
        storyboard: {{ graph_version: 14, graph_digest: "graph-v14" }},
        sequence: {{
          shots: [
            {{ node_id: "shot-01", state: "active", metadata: {{ title: "镜头 01", duration_seconds: 6 }} }},
            {{ node_id: "shot-02", state: "active", metadata: {{ title: "镜头 02", duration_seconds: 7 }} }},
            {{ node_id: "shot-03", state: "active", metadata: {{ title: "镜头 03", duration_seconds: 5 }} }},
          ],
          scenes: [{{ node_id: "scene-main", state: "active", metadata: {{ name: "主场景" }} }}],
          approved_media: [
            {{
              media_node_id: "approved-character",
              media_kind: "image",
              preview_url: "/projects/project-refresh/image-assets/character-image/preview",
              target_node_ids: ["character-main"],
            }},
            {{
              media_node_id: "approved-shot-01",
              media_kind: "image",
              preview_url: "/projects/project-refresh/image-assets/keyframe-01/preview",
              target_node_ids: ["shot-01"],
            }},
            {{
              media_node_id: "cross-project",
              media_kind: "image",
              preview_url: "/projects/other-project/image-assets/keyframe-02/preview",
              target_node_ids: ["shot-02"],
            }},
            {{
              media_node_id: "ambiguous-shot-03-a",
              media_kind: "image",
              preview_url: "/projects/project-refresh/image-assets/keyframe-03-a/preview",
              target_node_ids: ["shot-03"],
            }},
            {{
              media_node_id: "ambiguous-shot-03-b",
              media_kind: "image",
              preview_url: "/projects/project-refresh/image-assets/keyframe-03-b/preview",
              target_node_ids: ["shot-03"],
            }},
          ],
          dependencies: [
            {{ from_id: "scene-main", to_id: "shot-01", relation_type: "contains" }},
            {{ from_id: "scene-main", to_id: "shot-02", relation_type: "contains" }},
            {{ from_id: "scene-main", to_id: "shot-03", relation_type: "contains" }},
          ],
        }},
      }};
      const first = productionGraphWorkspaceProjection(workspace);
      const refreshed = productionGraphWorkspaceProjection(JSON.parse(JSON.stringify(workspace)));
      console.log(JSON.stringify({{ first, refreshed }}));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)

    for projection in (result["first"], result["refreshed"]):
        assert [shot["preview"] for shot in projection["shots"]] == [
            "/projects/project-refresh/image-assets/keyframe-01/preview",
            "",
            "",
        ]
        assert projection["graphVersion"] == 14
        assert projection["graphDigest"] == "graph-v14"

    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    graph_shot_model = shell.split("function graphShotModel()", 1)[1].split(
        "function graphSceneModel()",
        1,
    )[0]
    shot_card = shell.split("function buildShotCard", 1)[1].split(
        "function buildVersionBar",
        1,
    )[0]
    assert "safePreview(shot.preview)" in graph_shot_model
    assert "setRuntimeMediaSource(image, shot.preview)" in shot_card
    assert "image.src = shot.preview" not in shot_card


def test_approved_video_projects_into_storyboard_canvas_and_counts_after_refresh() -> None:
    projection_uri = (STUDIO / "src" / "production-graph-workspace-projection.js").as_uri()
    result_view_uri = (STUDIO / "src" / "node-result-view.js").as_uri()
    script = f"""
      import {{
        applyProductionGraphCanvasProjection,
        productionGraphWorkspaceProjection,
      }} from {json.dumps(projection_uri)};
      import {{ previewAspectRatio }} from {json.dumps(result_view_uri)};
      const workspace = {{
        status: "ready",
        project_id: "video-project",
        graph_version: 16,
        graph_digest: "graph-v16",
        storyboard: {{ graph_version: 16, graph_digest: "graph-v16" }},
        sequence: {{
          shots: [
            {{ node_id: "shot-alpha", state: "active", metadata: {{ title: "Alpha", duration_seconds: 6 }} }},
            {{ node_id: "shot-beta", state: "active", metadata: {{ title: "Beta", duration_seconds: 8 }} }},
          ],
          scenes: [{{ node_id: "scene-main", state: "active", metadata: {{ name: "Main" }} }}],
          approved_media: [
            {{
              media_node_id: "image-alpha",
              media_kind: "image",
              preview_url: "/projects/video-project/image-assets/image-alpha/preview",
              width: 1280,
              height: 720,
              target_node_ids: ["shot-alpha"],
            }},
            {{
              media_node_id: "video-alpha",
              media_kind: "video",
              preview_url: "/projects/video-project/approved-video-assets/video-alpha/preview",
              mime_type: "video/mp4",
              container: "video/mp4",
              width: 1280,
              height: 720,
              duration_sec: 6.04,
              codec: "h264",
              model: "model-alpha",
              resolution: "720p",
              approval_graph_version: 16,
              target_node_ids: ["shot-alpha"],
              lineage: {{ source_kind: "approved_video_receipt", target_relation: "approved_video" }},
            }},
            {{
              media_node_id: "video-cross-project",
              media_kind: "video",
              preview_url: "/projects/other/approved-video-assets/video-cross-project/preview",
              target_node_ids: ["shot-beta"],
            }},
            {{
              media_node_id: "video-beta-a",
              media_kind: "video",
              preview_url: "/projects/video-project/approved-video-assets/video-beta-a/preview",
              target_node_ids: ["shot-beta"],
            }},
            {{
              media_node_id: "video-beta-b",
              media_kind: "video",
              preview_url: "/projects/video-project/approved-video-assets/video-beta-b/preview",
              target_node_ids: ["shot-beta"],
            }},
          ],
          dependencies: [
            {{ from_id: "scene-main", to_id: "shot-alpha", relation_type: "contains" }},
            {{ from_id: "scene-main", to_id: "shot-beta", relation_type: "contains" }},
            {{ from_id: "shot-alpha", to_id: "video-alpha", relation_type: "approved_video" }},
          ],
        }},
      }};
      const first = productionGraphWorkspaceProjection(workspace);
      const refreshed = productionGraphWorkspaceProjection(JSON.parse(JSON.stringify(workspace)));
      const state = {{
        nodes: {{}},
        edges: {{}},
        order: [],
        selection: {{ nodeIds: [], edgeId: null }},
        production: {{}},
      }};
      applyProductionGraphCanvasProjection(state, workspace);
      const canvasVideo = Object.values(state.nodes).find(
        (node) => node.type === "video" && node.params?.productionGraphProjection
      );
      console.log(JSON.stringify({{
        first,
        refreshed,
        canvasVideo,
        canvasVideoAspectRatio: previewAspectRatio(canvasVideo),
        approvedVideoEdges: Object.values(state.edges).filter(
          (edge) => edge.relation_type === "production_graph_approved_video"
        ).length,
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

    for projection in (result["first"], result["refreshed"]):
        alpha, beta = projection["shots"]
        assert alpha["preview"].endswith("/image-alpha/preview")
        assert alpha["video"] == {
            "mediaNodeId": "video-alpha",
            "mediaKind": "video",
            "previewUrl": (
                "/projects/video-project/approved-video-assets/"
                "video-alpha/preview"
            ),
            "mimeType": "video/mp4",
            "container": "video/mp4",
            "width": 1280,
            "height": 720,
            "durationSeconds": 6.04,
            "codec": "h264",
            "model": "model-alpha",
            "resolution": "720p",
            "generationMode": "",
            "approvalGraphVersion": 16,
            "targetNodeIds": ["shot-alpha"],
            "lineage": {
                "sourceKind": "approved_video_receipt",
                "targetRelation": "approved_video",
            },
        }
        assert beta["video"] is None
        assert projection["mediaSummary"] == {
            "approvedImages": 1,
            "approvedAssetImages": 0,
            "approvedShotImages": 1,
            "approvedVideos": 1,
            "pendingVideoCandidates": 0,
            "generatedVideos": 1,
            "readyShots": 1,
        }

    canvas_video = result["canvasVideo"]
    assert canvas_video["status"] == "complete"
    assert canvas_video["result"] == "视频已保存到当前项目。"
    assert canvas_video["previewUrl"].startswith(
        "/projects/video-project/approved-video-assets/"
    )
    assert canvas_video["params"]["approvedMedia"]["model"] == "model-alpha"
    assert canvas_video["params"]["approvedMedia"]["source_node_ids"] == ["shot-alpha"]
    assert canvas_video["params"]["approvedMedia"]["width"] == 1280
    assert canvas_video["params"]["approvedMedia"]["height"] == 720
    assert canvas_video["params"]["previewAspectRatio"] == "1280:720"
    assert result["canvasVideoAspectRatio"] == "16 / 9"
    assert result["approvedVideoEdges"] == 1


def test_pending_video_candidate_projects_into_storyboard_canvas_without_approval() -> None:
    projection_uri = (STUDIO / "src" / "production-graph-workspace-projection.js").as_uri()
    script = f"""
      import {{
        applyProductionGraphCanvasProjection,
        productionGraphWorkspaceProjection,
      }} from {json.dumps(projection_uri)};
      const workspace = {{
        status: "ready",
        project_id: "video-project",
        graph_version: 30,
        graph_digest: "graph-v30",
        storyboard: {{ graph_version: 30, graph_digest: "graph-v30" }},
        sequence: {{
          shots: [
            {{ node_id: "shot-alpha", state: "active", metadata: {{ title: "Alpha", duration_seconds: 6 }} }},
            {{ node_id: "shot-beta", state: "active", metadata: {{ title: "Beta", duration_seconds: 8 }} }},
          ],
          scenes: [{{ node_id: "scene-main", state: "active", metadata: {{ name: "Main" }} }}],
          video_candidates: [
            {{
              media_node_id: "video-candidate-alpha",
              media_kind: "video",
              review_state: "candidate",
              preview_url: "/projects/video-project/video-generations/video-job-alpha/candidates/candidate_001/preview",
              mime_type: "video/mp4",
              container: "video/mp4",
              width: 1280,
              height: 720,
              duration_sec: 6.04,
              codec: "h264",
              model: "model-alpha",
              resolution: "720p",
              generation_mode: "reference_conditioned",
              manifest_id: "video-admission-alpha",
              manifest_hash: "a".repeat(64),
              job_id: "video-job-alpha",
              candidate_id: "candidate_001",
              sha256: "b".repeat(64),
              byte_count: 123,
              target_node_ids: ["shot-alpha"],
              lineage: {{ source_kind: "video_admission_candidate", target_relation: "video_candidate" }},
            }},
            {{
              media_node_id: "video-candidate-other",
              media_kind: "video",
              review_state: "candidate",
              preview_url: "/projects/other/video-generations/video-job/candidates/candidate_001/preview",
              target_node_ids: ["shot-beta"],
            }},
          ],
          dependencies: [
            {{ from_id: "scene-main", to_id: "shot-alpha", relation_type: "contains" }},
            {{ from_id: "scene-main", to_id: "shot-beta", relation_type: "contains" }},
            {{ from_id: "shot-alpha", to_id: "video-candidate-alpha", relation_type: "video_candidate" }},
          ],
        }},
      }};
      const projection = productionGraphWorkspaceProjection(workspace);
      const state = {{ nodes: {{}}, edges: {{}}, order: [], selection: {{ nodeIds: [], edgeId: null }}, production: {{}} }};
      applyProductionGraphCanvasProjection(state, workspace);
      const shotNode = Object.values(state.nodes).find(
        (node) => node.params?.productionGraphTruth?.graph_node_id === "shot-alpha"
      );
      const candidateNode = Object.values(state.nodes).find(
        (node) => node.params?.productionGraphTruth?.graph_node_id === "video-candidate-alpha"
      );
      const candidateEdges = Object.values(state.edges).filter(
        (edge) => edge.relation_type === "production_graph_video_candidate"
      );
      console.log(JSON.stringify({{ projection, shotNode, candidateNode, candidateEdges }}));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    alpha, beta = result["projection"]["shots"]
    assert alpha["state"] == "candidate"
    assert alpha["video"] is None
    assert alpha["videoCandidate"]["previewUrl"].endswith("/video-job-alpha/candidates/candidate_001/preview")
    assert beta["videoCandidate"] is None
    assert result["projection"]["mediaSummary"] == {
        "approvedImages": 0,
        "approvedAssetImages": 0,
        "approvedShotImages": 0,
        "approvedVideos": 0,
        "pendingVideoCandidates": 1,
        "generatedVideos": 1,
        "readyShots": 1,
    }
    assert result["shotNode"]["status"] == "complete"
    assert result["shotNode"]["result"] == "视频候选已写入当前项目，等待审看批准。"
    assert result["shotNode"]["params"]["approvedMedia"] is None
    assert result["shotNode"]["params"]["videoCandidate"]["review_state"] == "candidate"
    assert result["shotNode"]["params"]["videoCandidate"]["preview_url"].endswith("/video-job-alpha/candidates/candidate_001/preview")
    assert result["candidateNode"]["type"] == "video"
    assert result["candidateNode"]["title"] == "待审看镜头视频候选"
    assert result["candidateNode"]["previewUrl"].endswith("/video-job-alpha/candidates/candidate_001/preview")
    assert result["candidateNode"]["params"]["approvedMedia"] is None
    assert result["candidateNode"]["params"]["videoCandidate"]["review_state"] == "candidate"
    assert len(result["candidateEdges"]) == 1

    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    assert "buildPendingShotVideoCandidate(currentShot())" in shell
    assert "pending-shot-video-candidate" in shell
    assert "视频候选待审看" in shell


def test_pending_video_candidate_projects_from_graph_artifact_relation() -> None:
    projection_uri = (STUDIO / "src" / "production-graph-workspace-projection.js").as_uri()
    script = f"""
      import {{
        applyProductionGraphCanvasProjection,
        productionGraphWorkspaceProjection,
      }} from {json.dumps(projection_uri)};
      const workspace = {{
        status: "ready",
        project_id: "video-project",
        graph_version: 31,
        graph_digest: "graph-v31",
        storyboard: {{ graph_version: 31, graph_digest: "graph-v31" }},
        sequence: {{
          shots: [
            {{ node_id: "shot-20", state: "active", metadata: {{ title: "棋剑坠落", duration_seconds: 6 }} }},
            {{ node_id: "shot-21", state: "active", metadata: {{ title: "棋室对坐", duration_seconds: 6 }} }},
          ],
          scenes: [{{ node_id: "scene-03", state: "active", metadata: {{ name: "场景03" }} }}],
          video_candidates: [],
          artifact_nodes: [
            {{
              node_id: "video-candidate-video-admission-shot20",
              category: "artifact",
              state: "active",
              metadata: {{
                kind: "pending_video_candidate",
                review_state: "candidate",
                creative_approval_state: "pending",
                technical_qa_status: "pass",
                source_shot_id: "shot-20",
                manifest_id: "video-admission-shot20",
                manifest_hash: "a".repeat(64),
                job_id: "video-job-shot20",
                candidate_id: "candidate_001",
                sha256: "b".repeat(64),
                byte_count: 4350315,
                mime_type: "video/mp4",
                codec: "h264",
                width: 1280,
                height: 720,
                duration_sec: 6,
                model: "doubao-seedance-2-0",
                resolution: "720p",
                generation_mode: "reference_conditioned",
              }},
            }},
            {{
              node_id: "video-candidate-failed",
              category: "artifact",
              state: "active",
              metadata: {{
                kind: "pending_video_candidate",
                review_state: "candidate",
                technical_qa_status: "failed",
                source_shot_id: "shot-21",
                job_id: "video-job-shot21",
                candidate_id: "candidate_001",
              }},
            }},
          ],
          dependencies: [
            {{ from_id: "scene-03", to_id: "shot-20", relation_type: "contains" }},
            {{ from_id: "scene-03", to_id: "shot-21", relation_type: "contains" }},
            {{ from_id: "shot-20", to_id: "video-candidate-video-admission-shot20", relation_type: "video_candidate" }},
            {{ from_id: "shot-21", to_id: "video-candidate-failed", relation_type: "video_candidate" }},
          ],
        }},
      }};
      const projection = productionGraphWorkspaceProjection(workspace);
      const state = {{ nodes: {{}}, edges: {{}}, order: [], selection: {{ nodeIds: [], edgeId: null }}, production: {{}} }};
      applyProductionGraphCanvasProjection(state, workspace);
      const shotNode = Object.values(state.nodes).find(
        (node) => node.params?.productionGraphTruth?.graph_node_id === "shot-20"
      );
      const candidateNode = Object.values(state.nodes).find(
        (node) => node.params?.productionGraphTruth?.graph_node_id === "video-candidate-video-admission-shot20"
      );
      console.log(JSON.stringify({{ projection, shotNode, candidateNode }}));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    shot20, shot21 = result["projection"]["shots"]
    assert shot20["state"] == "candidate"
    assert shot20["videoCandidate"]["previewUrl"].endswith(
        "/video-job-shot20/candidates/candidate_001/preview"
    )
    assert shot20["videoCandidate"]["lineage"] == {
        "sourceKind": "production_graph_artifact_node",
        "targetRelation": "video_candidate",
    }
    assert shot21["videoCandidate"] is None
    assert result["projection"]["mediaSummary"]["pendingVideoCandidates"] == 1
    assert result["shotNode"]["params"]["videoCandidate"]["manifest_id"] == "video-admission-shot20"
    assert result["candidateNode"]["title"] == "待审看镜头视频候选"
    assert result["candidateNode"]["previewUrl"].endswith(
        "/video-job-shot20/candidates/candidate_001/preview"
    )


def test_approved_asset_media_projects_to_canvas_nodes_without_candidate_leakage() -> None:
    projection_uri = (STUDIO / "src" / "production-graph-workspace-projection.js").as_uri()
    result_view_uri = (STUDIO / "src" / "node-result-view.js").as_uri()
    script = f"""
      import {{
        applyProductionGraphCanvasProjection,
        productionGraphWorkspaceProjection,
      }} from {json.dumps(projection_uri)};
      import {{ previewAspectRatio }} from {json.dumps(result_view_uri)};
      const workspace = {{
        status: "ready",
        project_id: "asset-media-project",
        graph_version: 21,
        graph_digest: "graph-v21",
        storyboard: {{ graph_version: 21, graph_digest: "graph-v21" }},
        sequence: {{
          script_revisions: [],
          sequences: [],
          characters: [
            {{ node_id: "M-CHAR-01", state: "active", metadata: {{ display_name: "叶安安" }} }},
            {{ node_id: "M-CHAR-03", state: "active", metadata: {{ display_name: "孟欣" }} }},
          ],
          scenes: [
            {{ node_id: "M-ENV-03", state: "active", metadata: {{ name: "豪宅泳池派对" }} }},
          ],
          props: [],
          reference_sets: [],
          shots: [
            {{ node_id: "shot-04", state: "active", metadata: {{ title: "泳池苏醒", duration_seconds: 6 }} }},
          ],
          production_aids: [],
          approved_media: [
            {{
              media_node_id: "approved-mchar01",
              media_kind: "image",
              preview_url: "/projects/asset-media-project/image-assets/img-approved-mchar01/preview",
              width: 960,
              height: 1280,
              target_node_ids: ["M-CHAR-01"],
              approval_graph_version: 20,
            }},
            {{
              media_node_id: "approved-menv03",
              media_kind: "image",
              preview_url: "/projects/asset-media-project/image-assets/img-approved-menv03/preview",
              width: 1280,
              height: 720,
              target_node_ids: ["M-ENV-03"],
              approval_graph_version: 21,
            }},
            {{
              media_node_id: "approved-shot04",
              media_kind: "image",
              preview_url: "/projects/asset-media-project/image-assets/img-shot04/preview",
              width: 1280,
              height: 720,
              target_node_ids: ["shot-04"],
              approval_graph_version: 21,
            }},
          ],
          dependencies: [
            {{ from_id: "M-ENV-03", to_id: "shot-04", relation_type: "contains" }},
            {{ from_id: "M-CHAR-01", to_id: "approved-mchar01", relation_type: "approved_image" }},
            {{ from_id: "M-ENV-03", to_id: "approved-menv03", relation_type: "approved_image" }},
            {{ from_id: "shot-04", to_id: "approved-shot04", relation_type: "approved_image" }},
          ],
        }},
      }};
      const pendingCandidateUrl = "/projects/asset-media-project/image-assets/img-pending-mchar03/preview";
      const projection = productionGraphWorkspaceProjection(workspace);
      const state = {{
        nodes: {{}},
        edges: {{}},
        order: [],
        selection: {{ nodeIds: [], edgeId: null }},
        production: {{}},
      }};
      applyProductionGraphCanvasProjection(state, workspace);
      const nodes = Object.values(state.nodes);
      const character = nodes.find((node) => node.params?.productionGraphTruth?.graph_node_id === "M-CHAR-01");
      const pending = nodes.find((node) => node.params?.productionGraphTruth?.graph_node_id === "M-CHAR-03");
      const scene = nodes.find((node) => node.params?.productionGraphTruth?.graph_node_id === "M-ENV-03");
      console.log(JSON.stringify({{
        projection,
        character,
        pending,
        scene,
        characterAspect: previewAspectRatio(character),
        sceneAspect: previewAspectRatio(scene),
        leakedPendingCandidate: JSON.stringify(state).includes(pendingCandidateUrl),
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

    assert result["projection"]["mediaSummary"] == {
        "approvedImages": 3,
        "approvedAssetImages": 2,
        "approvedShotImages": 1,
        "approvedVideos": 0,
        "pendingVideoCandidates": 0,
        "generatedVideos": 0,
        "readyShots": 1,
    }
    character = result["character"]
    assert character["previewUrl"].endswith("/img-approved-mchar01/preview")
    assert character["status"] == "complete"
    assert character["result"] == "已批准参考图已保存到当前项目。"
    assert character["params"]["approvedMedia"]["media_node_id"] == "approved-mchar01"
    assert character["params"]["approvedMedia"]["source_node_ids"] == ["M-CHAR-01"]
    assert result["characterAspect"] == "3 / 4"
    assert result["scene"]["previewUrl"].endswith("/img-approved-menv03/preview")
    assert result["sceneAspect"] == "16 / 9"
    assert result["pending"].get("previewUrl", "") == ""
    assert result["pending"]["params"]["approvedMedia"] is None
    assert result["leakedPendingCandidate"] is False


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


def test_asset_bible_source_context_follows_nested_sequence_before_stale_legacy_state() -> None:
    bible_uri = (STUDIO / "src" / "asset-bible-workspace.js").as_uri()
    script = f"""
      import {{ assetBibleSourceContext }} from {json.dumps(bible_uri)};
      const legacyShotPlan = {{
        candidate_id: "legacy-candidate",
        scenes: [{{
          scene_id: "legacy-scene",
          name: "Legacy Stage",
          shots: [{{ shot_id: "legacy-shot", title: "Legacy Shot", duration_sec: 5 }}],
        }}],
      }};
      const staleLegacyState = {{
        nodes: {{
          story: {{
            id: "story",
            type: "text",
            content: "Legacy source must not override canonical graph v3.",
            params: {{
              currentRevisionId: "legacy-revision",
              revisions: [{{
                revision_id: "legacy-revision",
                screenplay_candidate: {{
                  screenplay_text: "Legacy source must not override canonical graph v3.",
                }},
              }}],
              shotPlanDraft: {{ ...legacyShotPlan, source_revision_id: "legacy-revision" }},
              embeddedCreativeAction: {{
                action_type: "shot_breakdown",
                status: "applied",
                applied_graph_version: 0,
                applied_revision_id: "legacy-revision",
                applied_subgraph: {{ candidate_id: "legacy-candidate", shot_plan: legacyShotPlan }},
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
      const workspace = {{
        status: "ready",
        graph_version: 3,
        graph_digest: "graph-v3-digest",
        storyboard: {{ graph_version: 3, graph_digest: "graph-v3-digest" }},
        sequence: {{
          script_revisions: [
            {{ node_id: "revision-v3", state: "active", metadata: {{ source_digest: "source" }} }},
          ],
          sequences: [
            {{ node_id: "sequence-v3", state: "active", metadata: {{ kind: "story_sequence" }} }},
          ],
          characters: [],
          scenes: [
            {{ node_id: "scene-modern", state: "active", metadata: {{ name: "现代重生域", space: "雨夜医院" }} }},
            {{ node_id: "scene-ancient", state: "active", metadata: {{ name: "古言棋局域", space: "王府密室" }} }},
          ],
          props: [],
          production_aids: [],
          shots: [
            {{ node_id: "shot-modern-01", state: "active", metadata: {{ title: "深海坠落", review_state: "needs_revision", duration_seconds: 8, blocking: "林晚面对傅行舟，濒死感打开重生设定。", intent: "保留返修问题" }} }},
            {{ node_id: "shot-modern-02", state: "active", metadata: {{ title: "医院醒来", duration_seconds: 7, blocking: "林晚从病床坐起。", intent: "现代重生域推进" }} }},
            {{ node_id: "shot-ancient-01", state: "active", metadata: {{ title: "棋局开场", duration_seconds: 6, blocking: "容华面对白筱，烛火照亮棋盘。", intent: "古言棋局域推进" }} }},
          ],
          dependencies: [
            {{ from_id: "revision-v3", to_id: "sequence-v3", relation_type: "derived_from" }},
            {{ from_id: "sequence-v3", to_id: "scene-modern", relation_type: "contains" }},
            {{ from_id: "sequence-v3", to_id: "scene-ancient", relation_type: "contains" }},
            {{ from_id: "scene-modern", to_id: "shot-modern-01", relation_type: "contains" }},
            {{ from_id: "scene-modern", to_id: "shot-modern-02", relation_type: "contains" }},
            {{ from_id: "scene-ancient", to_id: "shot-ancient-01", relation_type: "contains" }},
          ],
        }},
      }};
      const source = assetBibleSourceContext(staleLegacyState, workspace);
      const legacyOnly = assetBibleSourceContext(staleLegacyState, null);
      console.log(JSON.stringify({{ source, legacyOnly }}));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    source = result["source"]

    assert result["legacyOnly"]["script_revision_id"] == "legacy-revision"
    assert source["authority_mode"] == "canonical_production_graph"
    assert source["script_revision_id"] == "revision-v3"
    assert source["shot_candidate_id"] == "graph-v3-digest"
    assert source["scene_count"] == 2
    assert source["shot_count"] == 3
    assert source["duration_sec"] == 21
    assert [item["display_name"] for item in source["canonical_assets"]] == [
        "现代重生域",
        "古言棋局域",
    ]
    assert source["planning_issues"] == [
        {
            "issue_code": "shot_needs_revision_without_reason",
            "severity": "planning",
            "scene_id": "scene-modern",
            "scene_name": "现代重生域",
            "shot_id": "shot-modern-01",
            "shot_name": "深海坠落",
            "review_state": "needs_revision",
            "review_reason": "",
            "next_action": "补充返修原因或确认镜头修订后再进入媒体制作。",
        }
    ]
    assert "Legacy source" not in source["source_text"]
    assert "林晚面对傅行舟" in source["source_text"]
    assert source["provider_dispatch_count"] == 0
    assert source["external_cost_usd"] == 0
