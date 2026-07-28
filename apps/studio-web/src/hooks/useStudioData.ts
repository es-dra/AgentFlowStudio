import { useCallback, useEffect, useState } from "react";

import { getStudioSurface, isStudioRequestError } from "../api/studioClient";
import type { StudioData } from "../api/studioAdapter";
import type { ScreenState } from "../api/studioTypes";
import { canonicalFixture } from "../data/canonicalFixture";
import type { StudioUrlState } from "../state/urlState";

interface StudioDataState {
  status: ScreenState;
  data: StudioData | null;
  message: string;
  reload: () => void;
}

export function useStudioData(urlState: StudioUrlState): StudioDataState {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<Omit<StudioDataState, "reload">>({
    status: "loading",
    data: null,
    message: "正在读取项目…"
  });

  const reload = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    if (urlState.forcedState) {
      setState({
        status: urlState.forcedState,
        data: urlState.source === "fixture" ? fixtureData() : null,
        message: forcedStateMessage(urlState.forcedState)
      });
      return;
    }

    if (urlState.source === "fixture") {
      setState({ status: "ready", data: fixtureData(), message: "" });
      return;
    }

    const controller = new AbortController();
    setState({ status: "loading", data: null, message: "正在读取项目…" });
    getStudioSurface({
      projectId: urlState.projectId,
      surface: urlState.surface,
      signal: controller.signal
    })
      .then((envelope) => {
        if (
          urlState.expectedVersion !== null &&
          urlState.expectedVersion !== envelope.project_version
        ) {
          setState({
            status: "stale",
            data: { source: "live", fixture: null, envelope },
            message: "内容已更新，需要重新检查后继续。"
          });
          return;
        }
        setState({
          status: "ready",
          data: { source: "live", fixture: null, envelope },
          message: ""
        });
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (isStudioRequestError(error)) {
          setState({ status: error.kind, data: null, message: error.message });
          return;
        }
        setState({
          status: "error",
          data: null,
          message: error instanceof Error ? error.message : "读取项目失败。"
        });
      });

    return () => controller.abort();
  }, [
    revision,
    urlState.expectedVersion,
    urlState.forcedState,
    urlState.projectId,
    urlState.source,
    urlState.surface
  ]);

  return { ...state, reload };
}

function fixtureData(): StudioData {
  return { source: "fixture", fixture: canonicalFixture, envelope: null };
}

function forcedStateMessage(state: ScreenState): string {
  switch (state) {
    case "loading":
      return "正在读取项目…";
    case "empty":
      return "当前工作面还没有可显示的制作对象。";
    case "stale":
      return "内容已更新，需要重新检查后继续。";
    case "forbidden":
      return "你没有查看这个项目的权限。";
    case "error":
      return "读取项目失败，已有结果保持不变。";
    default:
      return "";
  }
}
