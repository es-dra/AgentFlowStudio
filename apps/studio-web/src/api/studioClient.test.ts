import { describe, expect, it } from "vitest";

import { parseStudioEnvelope, resolveRuntimeBaseUrl } from "./studioClient";
import { apiSurfaceFor } from "./studioTypes";

const baseEnvelope = {
  schema_version: "afs.studio_bff.v0.2",
  project_id: "project-1",
  project: {
    project_id: "project-1",
    project_type: "short_film",
    name: "雾港来信",
    status: "active"
  },
  authority_mode: "graph_v1",
  project_version: 32,
  graph_digest: "digest",
  event_cursor: 12,
  surface: "canvas",
  surface_summary: {
    state: "ready",
    headline: "当前工作面已从 ProductionGraph 投影",
    entity_count: 0,
    attention_count: 0
  },
  focused_entity: null,
  resume_target: {
    available: false,
    surface: "canvas",
    entity_id: "",
    reason: "当前没有可恢复的制作位置。"
  },
  agent_summary: {
    state: "collapsed",
    based_on_project_version: 32,
    entity_id: "",
    headline: "创作助手已收起。"
  },
  entities: [],
  relations: [],
  allowed_actions: [],
  task_summaries: [],
  review_queue: [],
  artifact_summaries: [],
  rework_preview: {
    available: false,
    target_entity_id: "",
    impact_refs: [],
    keep_refs: [],
    cost_available: false,
    reason: "当前没有可预览局部返工的审核目标。"
  },
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
    currency: "CNY",
    message: ""
  },
  recovery_summary: {
    attention_required: false,
    attention_task_count: 0,
    safe_to_repeat_provider_dispatch: false,
    message: ""
  },
  provider_dispatch_count: 0
};

describe("studio BFF client", () => {
  it("maps overview to the only shared API surface", () => {
    expect(apiSurfaceFor("overview")).toBe("overview");
    expect(apiSurfaceFor("review")).toBe("review");
  });

  it("accepts v0.2 studio envelopes and rejects other schemas", () => {
    expect(parseStudioEnvelope(baseEnvelope).project_version).toBe(32);
    expect(
      parseStudioEnvelope({
        ...baseEnvelope,
        surface: "overview",
        project_version: 33,
        event_cursor: 421
      }).project_version
    ).toBe(33);
    expect(() =>
      parseStudioEnvelope({ ...baseEnvelope, schema_version: "future" })
    ).toThrow("不兼容");
  });

  it("allows same-origin and loopback runtime overrides only", () => {
    const sameOrigin = {
      origin: "http://localhost:4173",
      search: "?runtime=http://localhost:4173"
    } as Location;
    const loopback = {
      origin: "http://localhost:4173",
      search: "?runtime=http://127.0.0.1:8790/"
    } as Location;
    const remote = {
      origin: "http://localhost:4173",
      search: "?runtime=https://example.com"
    } as Location;

    expect(resolveRuntimeBaseUrl(sameOrigin)).toBe("http://localhost:4173");
    expect(resolveRuntimeBaseUrl(loopback)).toBe("http://127.0.0.1:8790");
    expect(resolveRuntimeBaseUrl(remote)).toBe("http://localhost:4173");
  });
});
