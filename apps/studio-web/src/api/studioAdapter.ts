import type { CanonicalFixture } from "../data/canonicalFixture";
import type {
  AppSurface,
  StudioEntity,
  StudioSurfaceEnvelope
} from "./studioTypes";

export type StudioData =
  | {
      source: "fixture";
      fixture: CanonicalFixture;
      envelope: null;
    }
  | {
      source: "live";
      fixture: null;
      envelope: StudioSurfaceEnvelope;
    };

export function projectName(data: StudioData): string {
  return data.source === "fixture"
    ? data.fixture.project.displayName
    : data.envelope.project.name;
}

export function projectVersion(data: StudioData): number {
  return data.source === "fixture"
    ? data.fixture.project.projectVersion
    : data.envelope.project_version;
}

export function projectCheckpoint(data: StudioData): string {
  if (data.source === "fixture") {
    return new Intl.DateTimeFormat("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false
    }).format(new Date(data.fixture.project.lastCheckpointAt));
  }
  return `版本 ${data.envelope.project_version}`;
}

export function publicCopy(value: string | undefined, fallback = ""): string {
  const text = String(value ?? "").trim();
  if (!text) return fallback;
  return text
    .replaceAll("当前工作面已从 ProductionGraph 投影", "当前工作面已由项目脉络确认")
    .replaceAll("ProductionGraph", "项目脉络")
    .replace(/\bBFF\b/g, "服务端")
    .replaceAll("adopted video/delivery", "已采用视频或交付记录")
    .replace(/\bpreview\b/g, "预览");
}

export function hasAllowedAction(data: StudioData, action: string): boolean {
  if (data.source === "fixture") return false;
  return data.envelope.allowed_actions.some(
    (item) => item.action === action && item.enabled
  );
}

export function hasLiveSurfaceContent(data: StudioData): boolean {
  if (data.source === "fixture") return true;
  return (
    Boolean(data.envelope.surface_summary) ||
    Boolean(data.envelope.resume_target) ||
    data.envelope.entities.length > 0 ||
    data.envelope.review_queue.length > 0 ||
    data.envelope.artifact_summaries.length > 0 ||
    data.envelope.task_summaries.length > 0
  );
}

export function liveNotice(data: StudioData): string {
  if (data.source === "fixture") return "界面样例";
  if (data.envelope.authority_mode === "legacy_file") {
    return "项目尚未建立制作脉络";
  }
  return `服务端已确认 · 版本 ${data.envelope.project_version}`;
}

export function entityById(
  envelope: StudioSurfaceEnvelope,
  entityId: string | undefined
): StudioEntity | null {
  const id = String(entityId ?? "").trim();
  if (!id) return null;
  return envelope.entities.find((item) => item.entity_id === id) ?? null;
}

export function entityLabel(
  envelope: StudioSurfaceEnvelope,
  entityId: string | undefined,
  fallback = "服务端对象"
): string {
  const entity = entityById(envelope, entityId);
  const label = String(entity?.label ?? "").trim();
  if (!label || isInternalDisplayLabel(label, entityId)) return fallback;
  return label;
}

export function entityTypeLabel(type: string): string {
  switch (type) {
    case "unit":
      return "镜头";
    case "location":
      return "场景";
    case "character":
      return "角色";
    case "asset":
      return "资产";
    case "artifact":
      return "候选";
    case "collection":
      return "分组";
    default:
      return "对象";
  }
}

export function projectTypeLabel(type: string): string {
  switch (type) {
    case "studio_creator_authoring":
    case "creator_authoring":
      return "创作者项目";
    case "short_video":
      return "短视频项目";
    case "short_film":
      return "短片项目";
    default:
      return "当前项目";
  }
}

export function firstAvailableSurface(value: unknown, fallback: AppSurface): AppSurface {
  return value === "overview" ||
    value === "canvas" ||
    value === "script" ||
    value === "storyboard" ||
    value === "asset-bible" ||
    value === "review" ||
    value === "delivery"
    ? value
    : fallback;
}

export function numberFrom(value: unknown): number | null {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric >= 0 ? numeric : null;
}

export function labelFrom(value: unknown, fallback: string): string {
  const text = String(value ?? "").trim();
  return text || fallback;
}

export function stateLabel(state: string): string {
  switch (state) {
    case "active":
      return "已纳入项目";
    case "in_progress":
      return "制作中";
    case "empty":
      return "未形成";
    case "blocked":
      return "受阻";
    case "ready":
      return "已就绪";
    case "review_ready":
      return "待复核";
    case "delivered":
      return "已交付";
    case "planned":
      return "计划中";
    case "running":
      return "制作中";
    case "succeeded":
      return "已完成";
    case "failed":
      return "失败可恢复";
    case "pending":
      return "待审核";
    case "approved":
    case "selected":
      return "已采用";
    case "candidate":
      return "候选";
    case "reconcile_required":
      return "需对账";
    default:
      return state || "状态未提供";
  }
}

function isInternalDisplayLabel(label: string, entityId: string | undefined): boolean {
  const id = String(entityId ?? "").trim();
  if (id && label === id) return true;
  return (
    /^studio-\d{8,}-[a-z0-9]+$/i.test(label) ||
    /^[a-z0-9]+(?:-[a-z0-9]+)*-studio-\d{8,}-[a-z0-9]+$/i.test(label) ||
    /^[A-Z]+(?:-[A-Z0-9]+)+-\d+$/.test(label)
  );
}

export function stateTone(state: string): string {
  switch (state) {
    case "active":
    case "planned":
    case "candidate":
      return "muted";
    case "running":
    case "in_progress":
      return "active";
    case "succeeded":
    case "approved":
    case "selected":
      return "success";
    case "pending":
    case "blocked":
    case "review_ready":
    case "reconcile_required":
      return "warning";
    case "empty":
      return "muted";
    case "ready":
    case "delivered":
      return "success";
    default:
      return "muted";
  }
}
