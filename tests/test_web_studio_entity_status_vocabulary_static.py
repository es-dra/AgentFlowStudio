from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path


CONTRACT = Path("docs/architecture/AFS_STUDIO_ENTITY_STATUS_VOCABULARY_CONTRACT.md")

REQUIRED_ENTITIES = {
    "project_asset": "Project Asset",
    "reference_input": "Reference Input",
    "generation_candidate": "Generation Candidate",
    "keyframe_version": "Keyframe Version",
    "video_revision": "Video Revision",
    "binding": "Binding",
    "lineage": "Lineage",
}

REQUIRED_STATUSES = {
    "draft": "草稿",
    "queued": "排队中",
    "submitted": "已提交",
    "running": "生成中",
    "succeeded": "已完成",
    "partial": "部分完成",
    "failed": "失败",
    "retryable": "可重试",
    "retrying": "重试中",
    "cancelled": "已停止刷新",
    "blocked": "已阻断",
    "needs_attention": "需要检查",
    "accepted": "已采纳",
    "rejected": "已拒绝",
    "fixed": "已固定",
    "retired": "已停用",
    "bound": "已绑定",
    "unbound": "未绑定",
    "replaced": "已替换",
    "available": "可查看",
}

REQUIRED_ACTIONS = {
    "bind": "绑定",
    "unbind": "取消绑定",
    "replace": "替换",
    "reference": "用作参考",
    "retry": "重试",
    "accept": "采纳",
    "reject": "拒绝",
    "view_lineage": "查看来源链路",
    "view_evidence": "查看证据",
    "continue_to_video": "继续生成视频",
    "edit_keyframe": "编辑关键帧",
}


def test_contract_doc_covers_required_entities_statuses_actions_and_non_claims() -> None:
    text = CONTRACT.read_text(encoding="utf-8")

    assert "`p0-20260704`" in text

    for entity_id, canonical in REQUIRED_ENTITIES.items():
        assert f"`{entity_id}`" in text
        assert canonical in text

    for status, zh_label in REQUIRED_STATUSES.items():
        assert f"`{status}`" in text
        assert zh_label in text

    for action, zh_label in REQUIRED_ACTIONS.items():
        assert f"`{action}`" in text
        assert zh_label in text

    assert "| `replace` | 替换 | Project Asset, Reference Input, Keyframe Version, Video Revision, Binding, Lineage |" in text

    for marker in (
        "provider raw response",
        "signed URLs",
        "human acceptance",
        "generated-media QA",
        "business validation",
        "CompanyOS/COS promotion",
        "does not prove provider-side cancellation",
        "retry failed items only",
    ):
        assert marker in text


def test_studio_vocabulary_module_is_importable_and_matches_required_contract_ids() -> None:
    script = textwrap.dedent(
        """
        import {
          STUDIO_ACTION_VOCABULARY,
          STUDIO_ENTITY_VOCABULARY,
          STUDIO_ENTITY_STATUS_VOCABULARY_VERSION,
          STUDIO_STATUS_VOCABULARY,
          canonicalStudioStatusId,
          studioActionVocabularyEntry,
          studioEntityVocabularyEntry,
          studioStatusLabel,
          studioStatusVocabularyEntry,
        } from "./apps/studio/src/studio-entity-status-vocabulary.js";

        const requiredEntities = ["project_asset", "reference_input", "generation_candidate", "keyframe_version", "video_revision", "binding", "lineage"];
        const requiredStatuses = ["draft", "queued", "submitted", "running", "succeeded", "partial", "failed", "retryable", "retrying", "cancelled", "blocked", "needs_attention", "accepted", "rejected", "fixed", "retired", "bound", "unbound", "replaced", "available"];
        const requiredActions = ["bind", "unbind", "replace", "reference", "retry", "accept", "reject", "view_lineage", "view_evidence", "continue_to_video", "edit_keyframe"];
        const aliases = {
          empty: "draft",
          complete: "succeeded",
          completed: "succeeded",
          success: "succeeded",
          generated: "succeeded",
          partially_complete: "partial",
          error: "failed",
          failure: "failed",
          pending: "queued",
          generating: "running",
          cancelled_local_only: "cancelled",
          excluded: "retired",
        };

        function assertUnique(items, label) {
          const ids = items.map((item) => item.id);
          if (new Set(ids).size !== ids.length) throw new Error(`duplicate ${label} ids`);
        }

        assertUnique(STUDIO_ENTITY_VOCABULARY, "entity");
        assertUnique(STUDIO_STATUS_VOCABULARY, "status");
        assertUnique(STUDIO_ACTION_VOCABULARY, "action");

        if (STUDIO_ENTITY_STATUS_VOCABULARY_VERSION !== "p0-20260704") {
          throw new Error("unexpected vocabulary version");
        }
        for (const id of requiredEntities) {
          const entry = studioEntityVocabularyEntry(id);
          if (!entry?.canonicalLabel || !entry?.zhLabel || !entry?.allowedStates?.length || !entry?.nextActions?.length) {
            throw new Error(`missing entity ${id}`);
          }
        }
        for (const id of requiredStatuses) {
          const entry = studioStatusVocabularyEntry(id);
          if (!entry?.zhLabel || !entry?.existingEquivalents?.length) throw new Error(`missing status ${id}`);
        }
        for (const [alias, expected] of Object.entries(aliases)) {
          if (canonicalStudioStatusId(alias) !== expected) {
            throw new Error(`alias ${alias} did not canonicalize to ${expected}`);
          }
          if (!studioStatusLabel(alias)) throw new Error(`alias ${alias} did not resolve a label`);
        }
        for (const id of requiredActions) {
          const entry = studioActionVocabularyEntry(id);
          if (!entry?.zhLabel || !entry?.appliesTo?.length) throw new Error(`missing action ${id}`);
        }

        const actionsById = new Map(STUDIO_ACTION_VOCABULARY.map((entry) => [entry.id, entry]));
        for (const entity of STUDIO_ENTITY_VOCABULARY) {
          for (const stateId of entity.allowedStates) {
            if (!studioStatusVocabularyEntry(stateId)) {
              throw new Error(`entity ${entity.id} references unknown allowedState ${stateId}`);
            }
          }
          for (const actionId of entity.nextActions) {
            const action = actionsById.get(actionId);
            if (!action) throw new Error(`entity ${entity.id} references unknown action ${actionId}`);
            if (!action.appliesTo.includes(entity.id)) {
              throw new Error(`entity ${entity.id} nextAction ${actionId} is not allowed by action.appliesTo`);
            }
          }
        }
        """
    )
    subprocess.run(["node", "--input-type=module", "-e", script], check=True)
