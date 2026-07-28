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

  it("rejects unknown surfaces and forced states", () => {
    const state = readStudioUrlState("?surface=debug&ui_state=success");

    expect(state.surface).toBe("overview");
    expect(state.forcedState).toBe("");
  });
});
