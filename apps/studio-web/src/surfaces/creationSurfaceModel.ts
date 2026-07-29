import {
  firstAvailableSurface,
  numberFrom,
  publicCopy,
  stateLabel,
  stateTone
} from "../api/studioAdapter";
import type {
  AppSurface,
  StudioAllowedAction,
  StudioEntity,
  StudioRelation,
  StudioSurfaceEnvelope
} from "../api/studioTypes";

export interface PrimarySurfaceAction {
  label: string;
  enabled: boolean;
  reason: string;
  surface: AppSurface;
  entity: string;
  candidate: string;
}

export function allowedNavigationAction(
  envelope: StudioSurfaceEnvelope,
  actionName: string,
  options: {
    label: string;
    disabledLabel: string;
    surface: AppSurface;
    targetEntityId?: string;
    candidate?: string;
  }
): PrimarySurfaceAction {
  const action = envelope.allowed_actions.find((item) => item.action === actionName);
  const entity = options.targetEntityId || action?.target_entity_id || "";
  return {
    label: action?.enabled ? options.label : options.disabledLabel,
    enabled: action?.enabled === true,
    reason: publicCopy(action?.reason, "当前项目还没有准备好这个动作。"),
    surface: firstAvailableSurface(options.surface, "canvas"),
    entity,
    candidate: options.candidate ?? ""
  };
}

export function disabledPrimaryAction(
  label: string,
  reason: string,
  surface: AppSurface,
  entity = ""
): PrimarySurfaceAction {
  return {
    label,
    enabled: false,
    reason,
    surface,
    entity,
    candidate: ""
  };
}

export function textFrom(
  value: unknown,
  fallback = ""
): string {
  const text = publicCopy(String(value ?? "").trim(), fallback);
  return text || fallback;
}

export function metadataText(
  entity: StudioEntity | null | undefined,
  keys: string[],
  fallback = ""
): string {
  if (!entity) return fallback;
  for (const key of keys) {
    const value = entity.metadata[key];
    if (typeof value === "string" && value.trim()) return publicCopy(value, fallback);
  }
  return fallback;
}

export function metadataNumber(
  entity: StudioEntity | null | undefined,
  keys: string[]
): number | null {
  if (!entity) return null;
  for (const key of keys) {
    const value = numberFrom(entity.metadata[key]);
    if (value !== null) return value;
  }
  return null;
}

export function metadataList(
  entity: StudioEntity | null | undefined,
  key: string
): string[] {
  const value = entity?.metadata[key];
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (typeof item === "string") return publicCopy(item);
      if (isRecord(item)) {
        return publicCopy(String(item.label ?? "")) ||
          publicCopy(String(item.excerpt ?? "")) ||
          publicCopy(String(item.summary ?? "")) ||
          publicCopy(String(item.status ?? ""));
      }
      return "";
    })
    .filter(Boolean)
    .slice(0, 6);
}

export function metadataRecords(
  entity: StudioEntity | null | undefined,
  key: string
): Array<Record<string, unknown>> {
  const value = entity?.metadata[key];
  if (!Array.isArray(value)) return [];
  return value.filter(isRecord).slice(0, 8);
}

export function entityById(
  entities: StudioEntity[],
  id: string | undefined
): StudioEntity | null {
  const selectedId = String(id ?? "");
  return entities.find((item) => item.entity_id === selectedId) ?? null;
}

export function selectEntity(
  entities: StudioEntity[],
  preferredId: string,
  fallbackId = ""
): StudioEntity | null {
  return entityById(entities, preferredId) ??
    entityById(entities, fallbackId) ??
    entities[0] ??
    null;
}

export function sortByProductionOrder<T extends { entity: StudioEntity }>(
  items: T[]
): T[] {
  return [...items].sort((left, right) => {
    const leftOrder = orderValue(left.entity);
    const rightOrder = orderValue(right.entity);
    if (leftOrder !== rightOrder) return leftOrder - rightOrder;
    return left.entity.label.localeCompare(right.entity.label, "zh-CN");
  });
}

export function orderValue(entity: StudioEntity): number {
  return (
    metadataNumber(entity, ["order"]) ??
    metadataNumber(entity, ["scene_order"]) ??
    metadataNumber(entity, ["shot_order"]) ??
    Number.MAX_SAFE_INTEGER
  );
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null) return "时长待补齐";
  if (Number.isInteger(seconds)) return `${seconds} 秒`;
  return `${seconds.toFixed(1)} 秒`;
}

export function sumDurations(entities: StudioEntity[]): number | null {
  const values = entities
    .map((item) => metadataNumber(item, ["duration_seconds", "duration_sec"]))
    .filter((value): value is number => value !== null);
  if (!values.length) return null;
  return values.reduce((total, value) => total + value, 0);
}

export function stateView(entity: StudioEntity) {
  return {
    label: stateLabel(String(entity.state || "")),
    tone: stateTone(String(entity.state || ""))
  };
}

export function relationTargets(
  relations: StudioRelation[],
  fromId: string,
  relationType: string
): string[] {
  return relations
    .filter((item) => item.from_id === fromId && item.relation_type === relationType)
    .map((item) => item.to_id);
}

export function relationSources(
  relations: StudioRelation[],
  toId: string,
  relationType: string
): string[] {
  return relations
    .filter((item) => item.to_id === toId && item.relation_type === relationType)
    .map((item) => item.from_id);
}

export function traceLabel(entity: StudioEntity | null | undefined): string {
  if (!entity) return "来源待补齐";
  if (metadataText(entity, ["source_digest"])) return "来源已绑定";
  if (metadataText(entity, ["asset_bible_revision_id"])) return "资产版本已绑定";
  if (metadataRecords(entity, "source_evidence").length) return "证据已绑定";
  return "来源待补齐";
}

export function safeActionReason(action: StudioAllowedAction | undefined): string {
  return publicCopy(action?.reason, "当前项目还没有准备好这个动作。");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
