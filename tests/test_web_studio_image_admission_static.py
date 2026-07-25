from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_SHELL = ROOT / "apps" / "studio" / "src" / "product-shell.js"
RUNTIME_CLIENT = ROOT / "apps" / "studio" / "src" / "runtime-client.js"
WORKSPACE = ROOT / "apps" / "studio" / "src" / "image-admission-workspace.js"
STYLES = ROOT / "apps" / "studio" / "styles" / "asset-bible.css"


def test_agent_image_admission_action_opens_same_asset_bible_workspace() -> None:
    source = PRODUCT_SHELL.read_text(encoding="utf-8")

    assert '"image_admission_ready"' in source
    assert "].includes(action.action)" in source
    assert "imageAdmissionOpen = true" in source
    assert "showAssetBible();" in source
    assert "buildImageAdmissionPanel()" in source
    assert "第二控制台" not in source


def test_image_admission_uses_preview_confirm_runtime_command_path() -> None:
    shell = PRODUCT_SHELL.read_text(encoding="utf-8")
    client = RUNTIME_CLIENT.read_text(encoding="utf-8")
    workspace = WORKSPACE.read_text(encoding="utf-8")

    assert "previewImageAdmissionCommand(request)" in shell
    assert "confirmImageAdmissionCommand" in shell
    assert "/m6/image-admission/commands/preview" in client
    assert "/m6/image-admission/commands/confirm" in client
    assert "现在仅供预览，确认后才会保存" in shell
    assert "公开估算，非最终账单" in shell
    assert "preflightKeyframe(request)" in shell
    assert "generateKeyframe({" in shell
    assert "pollKeyframe(imageAdmissionItemJobId(item))" in shell
    assert "disable_provider_retry: true" in workspace
    assert 'type: "record_job"' in workspace
    assert 'type: "record_failure"' in shell
    assert "Provider 调用" not in shell
    assert "codex_image" not in shell
    assert "gpt-image" not in shell


def test_image_admission_projection_keeps_actual_billing_nullable_and_counts_states() -> None:
    script = f"""
      import {{ imageAdmissionProjection }} from {json.dumps(WORKSPACE.as_uri())};
      const result = imageAdmissionProjection({{
        manifest: {{
          status: "locked",
          actual_usd: null,
          billing_verification_state: "unverified",
          budget_contract: {{ max_dispatches: 9, max_estimated_usd: "0.3500" }},
          budget: {{ dispatches_reserved: 2, estimated_reserved_usd: "0.0754" }},
          items: [
            {{ item_id: "a", state: "approved" }},
            {{ item_id: "b", state: "candidate" }},
            {{ item_id: "c", state: "failed" }}
          ]
        }},
        capability: {{ image_gate_open: false, keyframe_continuity_ready: true }}
      }});
      console.log(JSON.stringify(result));
    """
    completed = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    result = json.loads(completed.stdout)

    assert result["status"] == "locked"
    assert result["counts"]["approved"] == 1
    assert result["counts"]["candidate"] == 1
    assert result["counts"]["failed"] == 1
    assert result["actual_usd"] is None
    assert result["billing_verification_state"] == "unverified"


def test_generation_request_uses_the_locked_prompt_contract_without_frontend_recompile() -> None:
    script = f"""
      import {{ imageAdmissionGenerationRequest }} from {json.dumps(WORKSPACE.as_uri())};
      const item = {{
        item_id: "item-a",
        target_asset_ids: ["asset-a"],
        aspect_ratio: "3:4",
        reference_media_ids: [],
        prompt_contract: {{
          provider_prompt: "【生成目标】锁定提示\\n【资产身份】已确认身份",
          art_direction: {{ visual_style: "写实动作片" }},
        }},
      }};
      console.log(JSON.stringify(imageAdmissionGenerationRequest(item, "manifest-a", "2026-07-24T00:00:00Z")));
    """
    completed = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    result = json.loads(completed.stdout)

    assert result["prompt_text"] == "【生成目标】锁定提示\n【资产身份】已确认身份"
    assert result["style"] == "写实动作片"
    assert result["candidate_count"] == 1
    assert result["node_parameters"]["disable_provider_retry"] is True


def test_image_admission_projection_marks_missing_or_failed_candidate_media() -> None:
    script = f"""
      import {{ imageAdmissionMediaKey, imageAdmissionProjection }} from {json.dumps(WORKSPACE.as_uri())};
      const item = {{
        item_id: "image-item-a",
        state: "candidate",
        candidate: {{
          image_asset_id: "image-a",
          sha256: "a".repeat(64),
          preview_url: "/projects/project-a/image-assets/image-a/preview",
        }},
      }};
      const key = imageAdmissionMediaKey(item, "project-a");
      const failed = imageAdmissionProjection({{
        manifest: {{ project_id: "project-a", items: [item] }},
      }}, {{ [key]: "failed" }});
      const missing = imageAdmissionProjection({{
        manifest: {{
          project_id: "project-a",
          items: [{{ ...item, candidate: {{ ...item.candidate, preview_url: "" }} }}],
        }},
      }});
      console.log(JSON.stringify({{ failed, missing }}));
    """
    completed = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    result = json.loads(completed.stdout)

    assert result["failed"]["counts"]["media_load_failed"] == 1
    assert result["missing"]["counts"]["media_load_failed"] == 1


def test_image_admission_generation_requires_complete_verified_media_evidence() -> None:
    script = f"""
      import {{ imageAdmissionGenerationResult }} from {json.dumps(WORKSPACE.as_uri())};
      const digest = "a".repeat(64);
      const preview = {{
        candidate_id: "candidate_001",
        sha256: digest,
        preview_url: "/projects/project-001/keyframe-generations/job-001/candidates/candidate_001/preview",
      }};
      const authority = {{
        asset_id: "asset-001",
        role: "generated_keyframe_reference",
        source_kind: "keyframe_candidate",
        source_job_id: "job-001",
        source_candidate_id: "candidate_001",
        source_candidate_digest: digest,
        sha256: digest,
        status: "succeeded",
        mime_type: "image/png",
        width: 1024,
        height: 1024,
        preview_url: "/projects/project-001/image-assets/asset-001/preview",
      }};
      const response = (asset) => ({{
        job: {{ job_id: "job-001", project_id: "project-001", status: "succeeded" }},
        candidate_previews: [preview],
        reusable_image_assets: [asset],
      }});
      console.log(JSON.stringify({{
        valid: imageAdmissionGenerationResult(response(authority)),
        incomplete: imageAdmissionGenerationResult(response({{ ...authority, width: null }})),
        crossProject: imageAdmissionGenerationResult(response({{
          ...authority,
          preview_url: "/projects/project-002/image-assets/asset-001/preview",
        }})),
      }}));
    """
    completed = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    result = json.loads(completed.stdout)

    assert result["valid"]["candidate"] == {
        "image_asset_id": "asset-001",
        "sha256": "a" * 64,
        "format": "png",
        "width": 1024,
        "height": 1024,
        "preview_url": "/projects/project-001/image-assets/asset-001/preview",
    }
    assert result["incomplete"]["candidate"] is None
    assert result["crossProject"]["candidate"] is None


def test_image_admission_mobile_layout_has_no_forced_horizontal_tracks() -> None:
    styles = STYLES.read_text(encoding="utf-8")

    assert ".image-admission-panel" in styles
    assert ".image-admission-item { align-items: flex-start; flex-wrap: wrap; }" in styles
    assert ".image-admission-item-actions { width: 100%; justify-content: flex-start; }" in styles
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in styles
    assert ".image-admission-thumbnail-button { width: 100%; max-height: 240px; }" in styles
    assert "object-fit: contain" in styles


def test_image_candidate_review_requires_loaded_thumbnail_and_accessible_viewer() -> None:
    shell = PRODUCT_SHELL.read_text(encoding="utf-8")

    for marker in (
        "候选图片成功加载后才能批准",
        "批准候选",
        "拒绝候选",
        "查看大图",
        "候选图片加载失败",
        "载入零费用测试候选",
        "测试候选 · 零费用本地证据 · 不代表创作质量",
        'event.key === "Escape"',
        'setAttribute("role", "dialog")',
        'setAttribute("aria-modal", "true")',
        'document.querySelector(".image-admission-viewer-close")?.focus()',
        "dataset.admissionMediaKey",
    ):
        assert marker in shell
    assert '"预览批准"' not in shell
    assert '"预览拒绝"' not in shell
    assert "approve.disabled = !media.canApprove" in shell
    assert "imageAdmissionMediaStates.set(key, state)" in shell


def test_copilot_prioritizes_admission_recovery_and_candidate_review_over_media_gate() -> None:
    script = f"""
      import {{ deriveProductionCopilotState }} from {json.dumps((ROOT / "apps/studio/src/asset-bible-workspace.js").as_uri())};
      const bible = {{
        schema_version: "afs.asset_bible.v0.1",
        status: "locked",
        locked_revision_id: "asset-bible-r1",
        candidate_set: {{ script_revision_id: "script-r1", shot_count: 17, scene_count: 3 }},
        coverage: {{ coverage_pass: true, quality_pass: true, shot_total: 17, shot_covered: 17, unresolved_required: 0 }},
        recognition_quality: {{ status: "pass", issues: [] }},
        art_direction: {{
          visual_style: "写实动作片", medium: "电影摄影", palette: "低饱和冷色", lighting: "侧逆光", confirmed_at: "2026-07-24T00:00:00Z"
        }},
        assets: [{{
          stable_id: "asset-a", asset_type: "character", display_name: "角色", review_state: "approved",
          visual_identity: "已确认角色轮廓与配色", positive_traits: ["稳定辨识特征"], pending_fields: [],
          continuity_states: [{{ label: "造型连续", status: "confirmed" }}],
          occurrences: {{ scene_ids: [], shot_ids: [] }}
        }}],
      }};
      const base = {{ studioState: {{ assetBible: bible, nodes: {{}} }}, capabilityGates: {{ image: false }}, section: "asset_bible" }};
      const failed = deriveProductionCopilotState({{
        ...base,
        imageAdmission: {{
          status: "locked",
          counts: {{ failed: 1, candidate: 0, processing: 0 }},
          budget: {{ dispatches_reserved: 1 }},
          provider_dispatch_count: 1,
          actual_usd: null,
        }},
      }});
      const review = deriveProductionCopilotState({{
        ...base,
        imageAdmission: {{
          status: "locked",
          counts: {{ failed: 0, candidate: 2, processing: 0 }},
          budget: {{ dispatches_reserved: 2 }},
          provider_dispatch_count: 2,
          actual_usd: null,
        }},
      }});
      const mediaFailure = deriveProductionCopilotState({{
        ...base,
        imageAdmission: {{
          status: "locked",
          counts: {{ failed: 1, candidate: 1, media_load_failed: 1 }},
          budget: {{ dispatches_reserved: 0 }},
          provider_dispatch_count: 0,
          actual_usd: null,
        }},
      }});
      const approved = deriveProductionCopilotState({{
        ...base,
        imageAdmission: {{
          status: "locked",
          counts: {{ failed: 0, candidate: 0, processing: 0, approved: 1, media_load_failed: 0 }},
          budget: {{ dispatches_reserved: 0 }},
          provider_dispatch_count: 0,
          actual_usd: null,
        }},
      }});
      console.log(JSON.stringify({{ failed, review, mediaFailure, approved }}));
    """
    completed = subprocess.run(["node", "--input-type=module", "-e", script], check=True, capture_output=True, text=True)
    result = json.loads(completed.stdout)

    assert result["failed"]["stage"] == "image_admission_recovery"
    assert result["failed"]["next_valid_action"]["action"] == "recover_image_admission"
    assert "1 个图片项目失败且已隔离" in result["failed"]["blockers"]
    assert result["failed"]["provider_dispatch_count"] == 1
    assert result["failed"]["gate"]["cost_state"] == "estimated_reserved"
    assert result["review"]["stage"] == "image_candidate_review"
    assert result["review"]["next_valid_action"]["action"] == "review_image_candidates"
    assert result["review"]["next_valid_action"]["reason"] == "2 个图片候选待人工查看；批准前不会写入制作图。"
    assert result["mediaFailure"]["stage"] == "image_candidate_media_recovery"
    assert result["mediaFailure"]["next_valid_action"]["action"] == "reload_image_candidate"
    assert "批准已禁用" in result["mediaFailure"]["next_valid_action"]["reason"]
    assert result["approved"]["stage"] == "media_gate_closed"
    assert "已批准图片已写回 Asset Bible / ProductionGraph" in result["approved"]["next_valid_action"]["reason"]
