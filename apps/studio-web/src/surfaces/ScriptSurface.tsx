import { useMemo } from "react";
import {
  IconArrowRight,
  IconCircleCheck,
  IconRoute
} from "@tabler/icons-react";

import type { SurfaceProps } from "../App";
import type { StudioEntity } from "../api/studioTypes";
import {
  allowedNavigationAction,
  disabledPrimaryAction,
  entityById,
  formatDuration,
  metadataNumber,
  metadataText,
  orderValue,
  relationSources,
  relationTargets,
  selectEntity,
  sortByProductionOrder,
  sumDurations,
  traceLabel
} from "./creationSurfaceModel";

export default function ScriptSurface({
  data,
  urlState,
  onNavigate
}: SurfaceProps) {
  const view = useMemo(
    () => scriptView(data, urlState.entity),
    [data, urlState.entity]
  );

  if (view.isEmpty) {
    return (
      <section className="creation-surface surface" aria-live="polite">
        <div className="surface-state surface-state--embedded">
          <p className="eyebrow">剧本</p>
          <h1>还没有可进入分镜的剧本拆解</h1>
          <p>
            当前项目没有从统一项目脉络投影出剧本版本、场次或镜头意图。
            页面不会补写静态剧情。
          </p>
          <button
            className="button button--primary"
            type="button"
            onClick={() => onNavigate({ surface: "canvas", entity: "" })}
          >
            返回制作画布
          </button>
        </div>
      </section>
    );
  }

  const selectedScene = view.scenes.find((item) => item.id === view.selectedSceneId);
  const primary = view.primaryAction;

  return (
    <section className="creation-surface script-surface surface">
      <aside className="creation-rail" aria-label="剧本场次">
        <div className="section-heading">
          <div>
            <p className="eyebrow">剧本结构</p>
            <h2>{view.sequenceLabel}</h2>
          </div>
        </div>
        {view.scenes.map((scene) => (
          <button
            key={scene.id}
            type="button"
            className={scene.id === view.selectedSceneId ? "creation-row is-active" : "creation-row"}
            aria-current={scene.id === view.selectedSceneId ? "true" : undefined}
            onClick={() => onNavigate({ entity: scene.id, candidate: "", blocker: "" })}
          >
            <span>
              <strong>{scene.orderLabel} · {scene.label}</strong>
              <small>{scene.purpose}</small>
            </span>
            <em>{scene.durationLabel}</em>
          </button>
        ))}
        <div className="creation-rail__meta">
          <span>{view.sceneCount} 场</span>
          <span>{view.shotCount} 个镜头</span>
          <span>{view.durationLabel}</span>
        </div>
      </aside>

      <div className="creation-workspace">
        <header className="creation-header">
          <div>
            <p className="breadcrumb">{view.revisionLabel}</p>
            <h1>这一版故事是否足够进入分镜？</h1>
            <p>{view.readiness}</p>
          </div>
          <div className="primary-action-block">
            <button
              className="button button--primary"
              type="button"
              disabled={!primary.enabled}
              title={primary.reason}
              onClick={() =>
                onNavigate({
                  surface: primary.surface,
                  entity: primary.entity || view.selectedBeatId || view.selectedSceneId,
                  candidate: primary.candidate
                })
              }
            >
              <IconArrowRight aria-hidden="true" size={18} />
              {primary.label}
            </button>
            <small>{primary.reason}</small>
          </div>
        </header>

        <div className="script-layout">
          <section className="script-reader" aria-label="剧本拆解">
            <div className="fact-strip">
              <span>
                <IconCircleCheck aria-hidden="true" size={17} />
                {view.sourceLabel}
              </span>
              <span>{view.traceCount} 个镜头含来源摘要</span>
              <span>{view.readOnlyLabel}</span>
            </div>

            <div className="script-scene-block">
              <p className="eyebrow">当前场次</p>
              <h2>{selectedScene?.label ?? "当前场次"}</h2>
              <p>{selectedScene?.purpose ?? "当前场次尚未写入结构化目的。"}</p>
            </div>

            <div className="script-beat-list">
              {view.beats.map((beat) => (
                <button
                  key={beat.id}
                  type="button"
                  className={beat.id === view.selectedBeatId ? "script-beat is-active" : "script-beat"}
                  aria-current={beat.id === view.selectedBeatId ? "true" : undefined}
                  onClick={() => onNavigate({ entity: beat.id, candidate: "", blocker: "" })}
                >
                  <span>{beat.orderLabel}</span>
                  <strong>{beat.title}</strong>
                  <p>{beat.intent}</p>
                  <small>{beat.durationLabel} · {beat.trace}</small>
                </button>
              ))}
            </div>
          </section>

          <aside className="creation-detail" aria-label="剧本选择详情">
            <p className="eyebrow">选中上下文</p>
            <h2>{view.selectedDetail.title}</h2>
            <dl className="detail-list">
              <div>
                <dt>人物调度</dt>
                <dd>{view.selectedDetail.blocking}</dd>
              </div>
              <div>
                <dt>叙事意图</dt>
                <dd>{view.selectedDetail.intent}</dd>
              </div>
              <div>
                <dt>来源状态</dt>
                <dd>{view.selectedDetail.trace}</dd>
              </div>
            </dl>
            <div className="next-hop">
              <IconRoute aria-hidden="true" size={18} />
              <span>{view.nextContext}</span>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}

export function scriptView(
  data: SurfaceProps["data"],
  selectedEntityId = ""
) {
  if (data.source === "fixture") {
    const scenes = data.fixture.scenes.map((scene) => {
      const shots = data.fixture.shots.filter((shot) => scene.shotRefs.includes(shot.shotRef));
      return {
        id: scene.sceneRef,
        label: scene.title,
        orderLabel: `第 ${scene.sequence} 场`,
        purpose: `${shots.length} 个镜头已拆解`,
        durationLabel: `${scene.durationSeconds} 秒`,
        shotIds: shots.map((shot) => shot.shotRef)
      };
    });
    const selectedSceneId =
      scenes.find((scene) => scene.id === selectedEntityId)?.id ||
      scenes.find((scene) => scene.shotIds.includes(selectedEntityId))?.id ||
      scenes[0]?.id ||
      "";
    const selectedFixtureScene = scenes.find((scene) => scene.id === selectedSceneId);
    const shots = data.fixture.shots.filter((shot) =>
      selectedFixtureScene?.shotIds.includes(shot.shotRef)
    );
    const selectedBeatId =
      shots.find((shot) => shot.shotRef === selectedEntityId)?.shotRef ||
      shots[0]?.shotRef ||
      "";
    const selectedShot = shots.find((shot) => shot.shotRef === selectedBeatId) ?? shots[0];
    return {
      isEmpty: false,
      sequenceLabel: data.fixture.project.episodeName,
      revisionLabel: "界面样例 · 不写入项目",
      readiness: "样例剧本拆解用于界面检查；真实项目只读取统一项目脉络。",
      sourceLabel: "fixture",
      readOnlyLabel: "样例只读",
      sceneCount: scenes.length,
      shotCount: data.fixture.shots.length,
      durationLabel: `${data.fixture.project.targetDurationSeconds} 秒`,
      traceCount: data.fixture.shots.length,
      scenes,
      selectedSceneId,
      selectedBeatId,
      beats: shots.map((shot) => ({
        id: shot.shotRef,
        orderLabel: `镜头 ${String(shot.sequence).padStart(2, "0")}`,
        title: shot.displayName,
        intent: shot.intent,
        durationLabel: `${shot.durationSeconds} 秒`,
        trace: "样例来源"
      })),
      selectedDetail: {
        title: selectedShot?.displayName ?? "当前镜头",
        blocking: selectedShot?.intent ?? "样例镜头尚无调度说明。",
        intent: selectedShot?.intent ?? "样例镜头尚无叙事意图。",
        trace: "界面样例"
      },
      nextContext: "进入分镜后继续检查镜头节奏与资产绑定。",
      primaryAction: {
        label: "进入分镜",
        enabled: true,
        reason: "界面样例导航，不会写入项目。",
        surface: "storyboard" as const,
        entity: selectedBeatId,
        candidate: ""
      }
    };
  }

  const envelope = data.envelope;
  const revision = envelope.entities.find((item) => item.entity_type === "revision") ?? null;
  const sequence = envelope.entities.find(
    (item) => item.entity_type === "collection" && metadataText(item, ["kind"]) !== "asset_bible"
  ) ?? null;
  const shotEntities = sortByProductionOrder(
    envelope.entities
      .filter((item) => item.entity_type === "unit")
      .map((entity) => ({ entity }))
  ).map((item) => item.entity);
  const sceneEntities = sortByProductionOrder(
    envelope.entities
      .filter((item) => item.entity_type === "location")
      .map((entity) => ({ entity }))
  ).map((item) => item.entity);
  const sceneRows = sceneEntities.map((scene, index) => {
    const shotIds = relationTargets(envelope.relations, scene.entity_id, "contains");
    const sceneShots = shotIds
      .map((id) => entityById(shotEntities, id))
      .filter((item): item is StudioEntity => Boolean(item));
    return {
      id: scene.entity_id,
      label: scene.label,
      orderLabel: `第 ${metadataNumber(scene, ["order"]) ?? index + 1} 场`,
      purpose: metadataText(scene, ["purpose"], "场次目的待补齐"),
      durationLabel: formatDuration(sumDurations(sceneShots)),
      shotIds
    };
  });
  const fallbackScene = {
    id: "script-unscoped-shots",
    label: "当前剧本拆解",
    orderLabel: "全部",
    purpose: "项目已形成镜头意图，但尚未提供场次分组。",
    durationLabel: formatDuration(sumDurations(shotEntities)),
    shotIds: shotEntities.map((item) => item.entity_id)
  };
  const scenes = sceneRows.length ? sceneRows : shotEntities.length ? [fallbackScene] : [];
  const selectedEntity = selectEntity(
    [...sceneEntities, ...shotEntities],
    selectedEntityId,
    envelope.resume_target.entity_id || envelope.focused_entity?.entity_id || ""
  );
  const parentSceneId = selectedEntity
    ? relationSources(envelope.relations, selectedEntity.entity_id, "contains")[0]
    : "";
  const selectedSceneId =
    scenes.find((scene) => scene.id === selectedEntity?.entity_id)?.id ||
    scenes.find((scene) => scene.id === parentSceneId)?.id ||
    scenes[0]?.id ||
    "";
  const selectedScene = scenes.find((scene) => scene.id === selectedSceneId);
  const beatEntities = (selectedScene?.shotIds ?? [])
    .map((id) => entityById(shotEntities, id))
    .filter((item): item is StudioEntity => Boolean(item))
    .sort((left, right) => orderValue(left) - orderValue(right));
  const selectedBeat =
    selectedEntity?.entity_type === "unit" && beatEntities.some((item) => item.entity_id === selectedEntity.entity_id)
      ? selectedEntity
      : beatEntities[0] ?? shotEntities[0] ?? revision;
  const primaryTarget = selectedBeat?.entity_id || selectedSceneId;
  const primaryAction = allowedNavigationAction(envelope, "continue_to_storyboard", {
    label: "进入分镜",
    disabledLabel: "分镜未准备",
    surface: "storyboard",
    targetEntityId: primaryTarget
  });
  const traceCount = shotEntities.filter((item) => metadataText(item, ["source_digest"])).length;
  const totalDuration = sumDurations(shotEntities);
  return {
    isEmpty: !revision && !shotEntities.length && !sceneEntities.length,
    sequenceLabel: sequence?.label || "制作序列",
    revisionLabel: revision?.label ? `剧本版本 · ${revision.label}` : "剧本版本待补齐",
    readiness:
      shotEntities.length > 0
        ? "当前读取的是已确认剧本在项目脉络中的场次与镜头意图；剧本文字全文尚未进入 Studio BFF 投影。"
        : "当前只读到剧本版本，还没有可进入分镜的镜头拆解。",
    sourceLabel: envelope.authority_mode === "graph_v1" ? "真实项目脉络" : "旧项目文件",
    readOnlyLabel: primaryAction.enabled ? "可继续导航" : "只读待准备",
    sceneCount: sceneEntities.length,
    shotCount: shotEntities.length,
    durationLabel: formatDuration(totalDuration),
    traceCount,
    scenes,
    selectedSceneId,
    selectedBeatId: selectedBeat?.entity_id ?? "",
    beats: beatEntities.map((shot, index) => ({
      id: shot.entity_id,
      orderLabel: `镜头 ${metadataNumber(shot, ["shot_order"]) ?? index + 1}`,
      title: shot.label,
      intent: metadataText(shot, ["intent"], "叙事意图待补齐"),
      durationLabel: formatDuration(metadataNumber(shot, ["duration_seconds", "duration_sec"])),
      trace: traceLabel(shot)
    })),
    selectedDetail: {
      title: selectedBeat?.label || selectedScene?.label || "当前对象",
      blocking: metadataText(selectedBeat, ["blocking"], "人物调度待补齐"),
      intent: metadataText(selectedBeat, ["intent"], "叙事意图待补齐"),
      trace: traceLabel(selectedBeat)
    },
    nextContext:
      primaryAction.enabled
        ? "进入分镜后保留当前项目与选中镜头。"
        : "后端尚未允许继续分镜导航，当前保持只读。",
    primaryAction: shotEntities.length
      ? primaryAction
      : disabledPrimaryAction("分镜未准备", "当前项目没有可进入分镜的镜头。", "storyboard")
  };
}
