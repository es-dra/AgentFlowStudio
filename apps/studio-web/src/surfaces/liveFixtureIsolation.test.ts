import { describe, expect, it } from "vitest";

import { publicCopy, type StudioData } from "../api/studioAdapter";
import type { StudioSurfaceEnvelope } from "../api/studioTypes";
import { canvasView } from "./CanvasSurface";
import { deliveryView } from "./DeliverySurface";
import { overviewView } from "./OverviewSurface";
import { reworkPreviewModel } from "./ReworkPreview";
import { reviewView } from "./ReviewSurface";

const fixtureFacts = [
  "镜头 03",
  "灯塔远景",
  "06–08",
  "版本三",
  "共 7",
  "47",
  "约 4 分钟",
  "界面样例",
  "仅用于界面检查"
];

describe("live studio view models", () => {
  it("does not leak v0.2 fixture facts into sparse live mode", () => {
    const data = liveData({
      surface: "overview",
      surface_summary: {
        state: "ready",
        headline: "真实项目总览",
        entity_count: 2,
        attention_count: 0
      },
      resume_target: {
        available: true,
        surface: "canvas",
        entity_id: "shot-live-01",
        reason: "继续查看真实制作画布"
      },
      delivery_summary: {
        state: "empty",
        blocker_count: 0,
        delivery_version_id: "",
        playable: false
      },
      rework_preview: unavailableRework()
    });

    const output = JSON.stringify({
      overview: overviewView(data),
      canvas: canvasView(data),
      review: reviewView(data),
      delivery: deliveryView(data),
      rework: reworkPreviewModel(data, {
        imageUrl: "",
        title: "真实候选",
        durationSeconds: 12
      })
    });

    for (const fact of fixtureFacts) {
      expect(output).not.toContain(fact);
    }
    expect(overviewView(data).delivery.title).toBe("尚未形成可播放交付");
    expect(deliveryView(data).versions).toHaveLength(0);
    expect(deliveryView(data).playableDuration).toBe(0);
  });

  it("uses exact v0.2 review and rework fields without fixture media or costs", () => {
    const data = liveData({
      surface: "review",
      focused_entity: entity("shot-live-01", "unit", "真实镜头一", {
        duration_seconds: 12
      }),
      resume_target: {
        available: true,
        surface: "review",
        entity_id: "shot-live-01",
        reason: "继续处理真实审核目标。"
      },
      review_queue: [
        {
          review_id: "review-live-01",
          target_entity_id: "shot-live-01",
          state: "pending",
          evidence_refs: ["evidence-live-01"]
        }
      ],
      artifact_summaries: [
        {
          artifact_id: "candidate-live-01",
          state: "pending",
          version: 1,
          selected: false
        }
      ],
      rework_preview: {
        available: true,
        target_entity_id: "shot-live-01",
        impact_refs: ["shot-live-01"],
        keep_refs: ["scene-live-01"],
        cost_available: false,
        reason: "只读局部返工预览"
      }
    });

    const review = reviewView(data);
    expect(review.header.title).toBe("真实镜头一");
    expect(review.candidates[0]?.title).toBe("候选版本 1");
    expect(review.candidates[0]?.durationLabel).toBe("");
    expect(review.candidates[0]?.imageUrl).toBe("");
    expect(review.reworkAvailable).toBe(true);

    const pendingRework = reworkPreviewModel(data, {
      imageUrl: "",
      title: "真实候选一",
      durationSeconds: 12,
      range: [3, 5]
    });
    expect(pendingRework.impact).toBe("完成影响计算后展示");

    const rework = reworkPreviewModel(data, {
      imageUrl: "",
      title: "真实候选一",
      durationSeconds: 12,
      range: [3, 5],
      preview: {
        schema_version: "afs.studio_rework_preview.v0.1",
        status: "preview",
        preview_id: "a".repeat(64),
        project_id: "studio-1785154250742-86s0uf",
        graph_version: 33,
        graph_digest: "fb2573ea31e26c1349867afc0de15a37569ded34b1aa1cb7c09ac13d84448fec",
        target_entity_id: "shot-live-01",
        impact_refs: ["shot-live-01"],
        keep_refs: ["scene-live-01"],
        dependency_evidence: [],
        cost_available: false,
        requires_confirmation: true,
        provider_dispatch_count: 0
      }
    });
    expect(rework.impact).toBe("真实镜头一");
    expect(rework.keep).toBe("真实场景一");
    expect(rework.cost).toBe("费用待确认");
    expect(rework.estimatedTime).toBe("预计耗时暂不可用");
    expect(rework.summary).not.toContain("provider_dispatch_count");
    expect(rework.summary).not.toContain("v0.2");
    expect(rework.range).toBeUndefined();
  });

  it("projects honest review-empty and delivery-blocker states", () => {
    const data = liveData({
      surface: "review",
      review_queue: [],
      artifact_summaries: [],
      delivery_summary: {
        state: "blocked",
        blocker_count: 35,
        delivery_version_id: "",
        playable: false
      }
    });

    const review = reviewView(data);
    const delivery = deliveryView(data);

    expect(review.isEmpty).toBe(true);
    expect(review.projectVersion).toBe(33);
    expect(delivery.blockerCount).toBe(35);
    expect(delivery.blockers).toHaveLength(1);
    expect(delivery.blockers[0]?.actionable).toBe(true);
    expect(delivery.blockers[0]?.surface).toBe("canvas");
    expect(delivery.primaryActionLabel).toBe("返回制作画布");
  });

  it("translates internal command states before presenting creator copy", () => {
    const copy = publicCopy(
      "planned_not_dispatched provider_dispatch_count graph_v1 in_progress BFF"
    );

    expect(copy).toBe(
      "返工计划已保存，尚未开始制作 制作派发状态 项目脉络 制作中 项目数据"
    );
    expect(copy).not.toContain("planned_not_dispatched");
  });

  it("disables duplicate live rework when the service reports a planned task", () => {
    const data = liveData({
      surface: "review",
      focused_entity: entity("shot-live-01", "unit", "真实镜头一"),
      rework_preview: {
        available: false,
        target_entity_id: "shot-live-01",
        impact_refs: [],
        keep_refs: [],
        cost_available: false,
        reason: "该镜头已有待执行的局部返工任务。"
      }
    });

    const review = reviewView(data);

    expect(review.reworkAvailable).toBe(false);
    expect(review.reworkActionLabel).toBe("已有待执行返工任务");
    expect(review.reworkReason).toContain("已有待执行");
  });
});

function liveData(
  overrides: Partial<StudioSurfaceEnvelope> = {}
): Extract<StudioData, { source: "live" }> {
  const envelope: StudioSurfaceEnvelope = {
    schema_version: "afs.studio_bff.v0.2",
    project_id: "studio-1785154250742-86s0uf",
    project: {
      project_id: "studio-1785154250742-86s0uf",
      project_type: "short_video",
      name: "真实服务端项目",
      status: "active"
    },
    authority_mode: "graph_v1",
    project_version: 33,
    graph_digest: "fb2573ea31e26c1349867afc0de15a37569ded34b1aa1cb7c09ac13d84448fec",
    event_cursor: 421,
    surface: "overview",
    surface_summary: {
      state: "ready",
      headline: "真实项目",
      entity_count: 2,
      attention_count: 0
    },
    focused_entity: null,
    resume_target: {
      available: false,
      surface: "overview",
      entity_id: "",
      reason: "当前没有可恢复的制作位置。"
    },
    agent_summary: {
      state: "collapsed",
      based_on_project_version: 33,
      entity_id: "",
      headline: "真实项目上下文"
    },
    entities: [
      entity("scene-live-01", "location", "真实场景一"),
      entity("shot-live-01", "unit", "真实镜头一", { duration_seconds: 12 })
    ],
    relations: [
      {
        from_id: "scene-live-01",
        to_id: "shot-live-01",
        relation_type: "contains"
      }
    ],
    allowed_actions: [
      {
        action: "inspect_entity",
        enabled: true,
        requires_preview: false,
        target_entity_id: "shot-live-01",
        reason: "只读查看"
      }
    ],
    task_summaries: [],
    review_queue: [],
    artifact_summaries: [],
    rework_preview: unavailableRework(),
    delivery_summary: {
      state: "empty",
      blocker_count: 0,
      delivery_version_id: "",
      playable: false
    },
    cost_summary: {
      available: false,
      reserved: 0,
      committed: 0,
      currency: "",
      message: "费用账本尚未迁移到统一 Studio 投影。"
    },
    recovery_summary: {
      attention_required: false,
      attention_task_count: 0,
      safe_to_repeat_provider_dispatch: false,
      message: "统一远端任务账本尚未迁移，不能据此重复派发。"
    },
    provider_dispatch_count: 0,
    ...overrides
  };
  return { source: "live", fixture: null, envelope };
}

function entity(
  entity_id: string,
  entity_type: string,
  label: string,
  metadata: Record<string, unknown> = {}
) {
  return {
    entity_id,
    entity_type,
    label,
    state: "active",
    metadata
  };
}

function unavailableRework() {
  return {
    available: false,
    target_entity_id: "",
    impact_refs: [],
    keep_refs: [],
    cost_available: false,
    reason: "服务端尚未提供局部返工预览回执。"
  };
}
