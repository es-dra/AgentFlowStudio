import type { CanonicalFixture } from "../data/canonicalFixture";
import type { StudioSurfaceEnvelope } from "./studioTypes";

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

export function hasAllowedAction(data: StudioData, action: string): boolean {
  if (data.source === "fixture") return false;
  return data.envelope.allowed_actions.some(
    (item) => item.action === action && item.enabled
  );
}

export function hasLiveSurfaceContent(data: StudioData): boolean {
  if (data.source === "fixture") return true;
  return (
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
