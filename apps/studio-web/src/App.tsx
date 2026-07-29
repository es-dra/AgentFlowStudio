import { lazy, Suspense, useCallback, useEffect, useState } from "react";

import { AppShell } from "./components/AppShell";
import { AsyncState } from "./components/AsyncState";
import { hasLiveSurfaceContent, type StudioData } from "./api/studioAdapter";
import { useStudioData } from "./hooks/useStudioData";
import {
  patchStudioUrl,
  readStudioUrlState,
  type StudioUrlState
} from "./state/urlState";

const OverviewSurface = lazy(() => import("./surfaces/OverviewSurface"));
const CanvasSurface = lazy(() => import("./surfaces/CanvasSurface"));
const ScriptSurface = lazy(() => import("./surfaces/ScriptSurface"));
const StoryboardSurface = lazy(() => import("./surfaces/StoryboardSurface"));
const AssetBibleSurface = lazy(() => import("./surfaces/AssetBibleSurface"));
const ReviewSurface = lazy(() => import("./surfaces/ReviewSurface"));
const DeliverySurface = lazy(() => import("./surfaces/DeliverySurface"));

export function App() {
  const [urlState, setUrlState] = useState<StudioUrlState>(() =>
    readStudioUrlState(window.location.search)
  );
  const studio = useStudioData(urlState);

  useEffect(() => {
    const onPopState = () => setUrlState(readStudioUrlState(window.location.search));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = useCallback(
    (patch: Partial<StudioUrlState>, replace = false) => {
      const nextUrl = patchStudioUrl(urlState, patch);
      window.history[replace ? "replaceState" : "pushState"]({}, "", nextUrl);
      setUrlState(readStudioUrlState(nextUrl.slice(1)));
    },
    [urlState]
  );

  return (
    <AppShell
      data={studio.data}
      surface={urlState.surface}
      onNavigate={navigate}
    >
      <AsyncState
        status={studio.status}
        message={studio.message}
        onRetry={studio.reload}
        onReturn={() => navigate({ surface: "overview", forcedState: "" })}
      >
        {studio.data ? (
          <Suspense fallback={<SurfaceSkeleton />}>
            <SurfaceOutlet
              data={studio.data}
              urlState={urlState}
              onNavigate={navigate}
              onReload={studio.reload}
            />
          </Suspense>
        ) : null}
      </AsyncState>
    </AppShell>
  );
}

interface SurfaceOutletProps {
  data: StudioData;
  urlState: StudioUrlState;
  onNavigate: (patch: Partial<StudioUrlState>, replace?: boolean) => void;
  onReload: () => void;
}

function SurfaceOutlet({ data, urlState, onNavigate, onReload }: SurfaceOutletProps) {
  const shared = { data, urlState, onNavigate, onReload };
  if (data.source === "live" && !hasLiveSurfaceContent(data)) {
    return (
      <section className="surface-state surface-state--embedded" aria-live="polite">
        <p className="eyebrow">当前工作面</p>
        <h1>还没有可显示的制作对象</h1>
        <p>项目仍然安全保留。完成制作脉络初始化后，这里会显示可继续制作的内容。</p>
        <button
          className="button button--primary"
          type="button"
          onClick={() => onNavigate({ surface: "overview" })}
        >
          返回项目概览
        </button>
      </section>
    );
  }

  switch (urlState.surface) {
    case "overview":
      return <OverviewSurface {...shared} />;
    case "canvas":
      return <CanvasSurface {...shared} />;
    case "script":
      return <ScriptSurface {...shared} />;
    case "storyboard":
      return <StoryboardSurface {...shared} />;
    case "asset-bible":
      return <AssetBibleSurface {...shared} />;
    case "review":
      return <ReviewSurface {...shared} />;
    case "delivery":
      return <DeliverySurface {...shared} />;
    default:
      return <OverviewSurface {...shared} />;
  }
}

function SurfaceSkeleton() {
  return (
    <div className="surface-skeleton" aria-label="正在载入工作面">
      <span />
      <span />
      <span />
    </div>
  );
}

export interface SurfaceProps {
  data: StudioData;
  urlState: StudioUrlState;
  onNavigate: (patch: Partial<StudioUrlState>, replace?: boolean) => void;
  onReload: () => void;
}
