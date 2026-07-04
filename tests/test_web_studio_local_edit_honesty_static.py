from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def test_keyframe_video_surfaces_distinguish_regenerate_from_local_edit() -> None:
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    result_view = (STUDIO_ROOT / "src" / "node-result-view.js").read_text(encoding="utf-8")
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    asset_panel = (STUDIO_ROOT / "src" / "panels" / "asset-card-panel.js").read_text(encoding="utf-8")
    algorithm_panel = (STUDIO_ROOT / "src" / "panels" / "algorithm-context-panel.js").read_text(encoding="utf-8")

    assert "重新生成整张图" in node_menu
    assert "重新生成整段视频" in node_menu
    assert "关键帧局部编辑不可用" in node_menu
    assert "局部视频编辑不可用" in node_menu
    assert "需要 image-edit/mask 能力" in node_menu
    assert "需要 video-edit/mask/temporal 能力" in node_menu
    assert "创建视频重生成草稿" in node_menu
    assert "创建视频修改草稿" not in node_menu

    assert "重新生成整张" in result_view
    assert "重新生成整段" in result_view
    assert "这不是局部编辑" in result_view
    assert "提交视频重生成尝试；不是局部编辑" in prompt_bar

    assert "保存并重新生成资产图" in asset_panel
    assert "保存并局部修订生成" not in asset_panel
    assert "局部图像编辑未开放" in asset_panel
    assert "重新绘制整张资产图" in asset_panel
    assert "视频重生成尝试" in algorithm_panel
    assert "重生成片段" in algorithm_panel


def test_video_revision_draft_records_local_edit_unavailable_state() -> None:
    script = textwrap.dedent(
        """
        import { enableVideoRevisionDraft } from "./apps/studio/src/node-video-actions.js";

        const state = {
          nodes: {
            video_1: {
              id: "video_1",
              type: "video",
              prompt: "只让灯光更冷",
              params: { lastVideoJobId: "video_job_001" },
              result: "",
            },
          },
        };
        const store = {
          get: () => state,
          set: (mutator) => mutator(state),
        };

        enableVideoRevisionDraft(store, state.nodes.video_1);
        process.stdout.write(JSON.stringify(state.nodes.video_1));
        """
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    node = json.loads(completed.stdout)
    revision = node["params"]["videoRevision"]
    availability = revision["local_edit_availability"]

    assert revision["enabled"] is True
    assert revision["provider_capability_mode"] == "i2v_revision_attempt"
    assert availability["status"] == "unavailable"
    assert availability["required_capability"] == "video_edit_or_masked_temporal_edit"
    assert availability["reason"] == "current_video_revision_is_global_regeneration_attempt"
    assert "这不是局部编辑" in node["result"]
    assert "整段重生成尝试" in node["result"]
    assert "video-edit/mask/temporal" in node["result"]


def test_local_edit_honesty_does_not_change_runtime_or_provider_contract_markers() -> None:
    video_actions = (STUDIO_ROOT / "src" / "node-video-actions.js").read_text(encoding="utf-8")
    keyframe_actions = (STUDIO_ROOT / "src" / "node-keyframe-actions.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")

    assert "provider_capability_mode: \"i2v_revision_attempt\"" in video_actions
    assert "runtime.generateVideo(request)" in video_actions
    assert "runtime.generateVideoRevision(request)" in video_actions
    assert "runtime.generateKeyframe(request)" in keyframe_actions
    assert "/video-revisions" in runtime_client
    assert "/keyframe-generations" in runtime_client
