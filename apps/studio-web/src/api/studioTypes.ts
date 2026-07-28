export const studioSurfaces = [
  "canvas",
  "script",
  "storyboard",
  "asset-bible",
  "review",
  "delivery"
] as const;

export type StudioSurface = (typeof studioSurfaces)[number];
export type AppSurface = "overview" | StudioSurface;

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
  schema_version: "afs.studio_bff.v0.1";
  project_id: string;
  project: StudioProjectSummary;
  authority_mode: "legacy_file" | "graph_v1";
  project_version: number;
  graph_digest: string;
  surface: StudioSurface;
  entities: StudioEntity[];
  relations: StudioRelation[];
  allowed_actions: StudioAllowedAction[];
  task_summaries: StudioTaskSummary[];
  review_queue: StudioReviewItem[];
  artifact_summaries: StudioArtifactSummary[];
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
  return value === "overview" || studioSurfaces.includes(value as StudioSurface);
}

export function apiSurfaceFor(surface: AppSurface): StudioSurface {
  return surface === "overview" ? "canvas" : surface;
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
