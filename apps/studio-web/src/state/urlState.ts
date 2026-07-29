import { isAppSurface, type AppSurface, type ScreenState } from "../api/studioTypes";

export interface StudioUrlState {
  projectId: string;
  surface: AppSurface;
  candidate: string;
  entity: string;
  blocker: string;
  source: "live" | "fixture";
  forcedState: ScreenState | "";
  expectedVersion: number | null;
}

const forcedStates = new Set<ScreenState>([
  "loading",
  "empty",
  "error",
  "stale",
  "forbidden"
]);

export function readStudioUrlState(search: string): StudioUrlState {
  const params = new URLSearchParams(search);
  const rawSurface = params.get("surface");
  const rawState = params.get("ui_state");
  const rawExpected = params.get("expected_version");
  const expected = rawExpected === null ? Number.NaN : Number(rawExpected);
  return {
    projectId:
      params.get("project_id")?.trim() || "studio-1785154250742-86s0uf",
    surface: isAppSurface(rawSurface) ? rawSurface : "overview",
    candidate: params.get("candidate")?.trim() || "",
    entity: params.get("entity")?.trim() || "",
    blocker: params.get("blocker")?.trim() || "",
    source: params.get("source") === "fixture" ? "fixture" : "live",
    forcedState:
      rawState && forcedStates.has(rawState as ScreenState)
        ? (rawState as ScreenState)
        : "",
    expectedVersion:
      Number.isInteger(expected) && expected >= 0 ? expected : null
  };
}

export function patchStudioUrl(
  current: StudioUrlState,
  patch: Partial<StudioUrlState>
): string {
  const next = { ...current, ...patch };
  const params = new URLSearchParams();
  params.set("project_id", next.projectId);
  params.set("surface", next.surface);
  if (next.candidate) params.set("candidate", next.candidate);
  if (next.entity) params.set("entity", next.entity);
  if (next.blocker) params.set("blocker", next.blocker);
  if (next.source === "fixture") params.set("source", "fixture");
  if (next.forcedState) params.set("ui_state", next.forcedState);
  if (next.expectedVersion !== null) {
    params.set("expected_version", String(next.expectedVersion));
  }
  return `?${params.toString()}`;
}
