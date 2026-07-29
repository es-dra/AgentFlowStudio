export const studioSurfaces = [
  "canvas",
  "script",
  "storyboard",
  "asset-bible",
  "review",
  "delivery"
] as const;

export type StudioWorkSurface = (typeof studioSurfaces)[number];
export type StudioSurface = "overview" | StudioWorkSurface;
export type AppSurface = StudioSurface;

export interface StudioProjectSummary {
  project_id: string;
  project_type: string;
  name: string;
  status: string;
}

export interface StudioEntity {
  entity_id: string;
  entity_type: string;
  label: string;
  state: string;
  metadata: Record<string, unknown>;
}

export interface StudioRelation {
  from_id: string;
  to_id: string;
  relation_type: string;
}

export interface StudioAllowedAction {
  action: string;
  enabled: boolean;
  requires_preview: boolean;
  target_entity_id: string;
  reason: string;
}

export interface StudioTaskSummary {
  task_id: string;
  state: string;
  depends_on: string[];
  attempt_count: number;
}

export interface StudioReviewItem {
  review_id: string;
  target_entity_id: string;
  state: string;
  evidence_refs: string[];
}

export interface StudioArtifactSummary {
  artifact_id: string;
  state: string;
  version: number;
  selected: boolean;
}

export interface StudioSurfaceSummary {
  state: "empty" | "ready" | "attention" | "blocked";
  headline: string;
  entity_count: number;
  attention_count: number;
}

export interface StudioResumeTarget {
  available: boolean;
  surface: AppSurface;
  entity_id: string;
  reason: string;
}

export interface StudioAgentSummary {
  state: "collapsed" | "suggestion_available" | "attention_required" | "content_updated";
  based_on_project_version: number;
  entity_id: string;
  headline: string;
}

export interface StudioReworkPreview {
  available: boolean;
  target_entity_id: string;
  impact_refs: string[];
  keep_refs: string[];
  cost_available: boolean;
  reason: string;
}

export interface StudioDeliverySummary {
  state: "empty" | "blocked" | "review_ready" | "ready" | "delivered";
  blocker_count: number;
  delivery_version_id: string;
  playable: boolean;
}

export interface StudioReworkPreviewReceipt {
  schema_version: "afs.studio_rework_preview.v0.1";
  status: "preview";
  preview_id: string;
  project_id: string;
  graph_version: number;
  graph_digest: string;
  target_entity_id: string;
  impact_refs: string[];
  keep_refs: string[];
  dependency_evidence: Array<{
    from_id: string;
    to_id: string;
    relation_type: string;
  }>;
  cost_available: false;
  requires_confirmation: true;
  provider_dispatch_count: 0;
}

export interface StudioReworkConfirmReceipt {
  schema_version: "afs.studio_command_receipt.v0.1";
  status: "confirmed";
  action: "plan_local_rework";
  receipt_id: string;
  project_id: string;
  graph_version: number;
  graph_digest: string;
  target_entity_id: string;
  task_id: string;
  impact_refs: string[];
  dispatch_state: "planned_not_dispatched";
  idempotent_replay: boolean;
  provider_dispatch_count: 0;
}

export interface StudioCostSummary {
  available: boolean;
  reserved: number;
  committed: number;
  currency: string;
  message: string;
}

export interface StudioRecoverySummary {
  attention_required: boolean;
  attention_task_count: number;
  safe_to_repeat_provider_dispatch: false;
  message: string;
}

export interface StudioSurfaceEnvelope {
  schema_version: "afs.studio_bff.v0.2";
  project_id: string;
  project: StudioProjectSummary;
  authority_mode: "legacy_file" | "graph_v1";
  project_version: number;
  graph_digest: string;
  event_cursor: number;
  surface: StudioSurface;
  surface_summary: StudioSurfaceSummary;
  focused_entity: StudioEntity | null;
  resume_target: StudioResumeTarget;
  agent_summary: StudioAgentSummary;
  entities: StudioEntity[];
  relations: StudioRelation[];
  allowed_actions: StudioAllowedAction[];
  task_summaries: StudioTaskSummary[];
  review_queue: StudioReviewItem[];
  artifact_summaries: StudioArtifactSummary[];
  rework_preview: StudioReworkPreview;
  delivery_summary: StudioDeliverySummary;
  cost_summary: StudioCostSummary;
  recovery_summary: StudioRecoverySummary;
  provider_dispatch_count: 0;
}

export type ScreenState =
  | "loading"
  | "ready"
  | "empty"
  | "error"
  | "stale"
  | "forbidden";

export interface StudioRequestError {
  kind: Exclude<ScreenState, "loading" | "ready">;
  status: number;
  message: string;
}

export function isAppSurface(value: string | null): value is AppSurface {
  return value === "overview" || studioSurfaces.includes(value as StudioWorkSurface);
}

export function apiSurfaceFor(surface: AppSurface): StudioSurface {
  return surface;
}

export function surfaceLabel(surface: AppSurface): string {
  const labels: Record<AppSurface, string> = {
    overview: "项目概览",
    canvas: "制作画布",
    script: "剧本",
    storyboard: "分镜",
    "asset-bible": "资产设定",
    review: "生成审核",
    delivery: "合成交付"
  };
  return labels[surface];
}
