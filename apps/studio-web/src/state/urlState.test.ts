import { describe, expect, it } from "vitest";

import { patchStudioUrl, readStudioUrlState } from "./urlState";

describe("studio URL state", () => {
  it("uses live overview defaults without inventing an expected version", () => {
    const state = readStudioUrlState("");

    expect(state.surface).toBe("overview");
    expect(state.source).toBe("live");
    expect(state.expectedVersion).toBeNull();
  });

  it("round-trips focused review state", () => {
    const initial = readStudioUrlState(
      "?project_id=project-1&surface=review&source=fixture"
    );
    const nextUrl = patchStudioUrl(initial, {
      candidate: "candidate-2",
      entity: "shot-03",
      expectedVersion: 32
    });

    expect(readStudioUrlState(nextUrl)).toMatchObject({
      projectId: "project-1",
      surface: "review",
      source: "fixture",
      candidate: "candidate-2",
      entity: "shot-03",
      expectedVersion: 32
    });
  });

  it("accepts legacy project query but writes canonical project_id", () => {
    const initial = readStudioUrlState(
      "?project=legacy-project&surface=script&entity=scene-03"
    );
    const nextUrl = patchStudioUrl(initial, { surface: "storyboard" });

    expect(initial).toMatchObject({
      projectId: "legacy-project",
      surface: "script",
      entity: "scene-03"
    });
    expect(nextUrl).toContain("project_id=legacy-project");
    expect(nextUrl).not.toContain("project=");
    expect(readStudioUrlState(nextUrl)).toMatchObject({
      projectId: "legacy-project",
      surface: "storyboard",
      entity: "scene-03"
    });
  });

  it("prefers project_id when both current and legacy project query are present", () => {
    const state = readStudioUrlState(
      "?project=legacy-project&project_id=canonical-project&surface=canvas"
    );

    expect(state.projectId).toBe("canonical-project");
    expect(state.surface).toBe("canvas");
  });

  it("rejects unknown surfaces and forced states", () => {
    const state = readStudioUrlState("?surface=debug&ui_state=success");

    expect(state.surface).toBe("overview");
    expect(state.forcedState).toBe("");
  });
});
