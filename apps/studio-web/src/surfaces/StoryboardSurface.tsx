import { useMemo } from "react";
import {
  IconArrowRight,
  IconCircleCheck,
  IconMovie,
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
  relationSources,
  relationTargets,
  selectEntity,
  sortByProductionOrder,
  stateView,
  sumDurations,
  traceLabel
} from "./creationSurfaceModel";

export default function StoryboardSurface({
  data,
  urlState,
  onNavigate
}: SurfaceProps) {
  const view = useMemo(
    () => storyboardView(data, urlState.entity),
    [data, urlState.entity]
  );

  if (view.isEmpty) {
    return (
      <section className="creation-surface surface" aria-live="polite">
        <div className="surface-state surface-state--embedded">
          <p className="eyebrow">分镜</p>
          <h1>还没有可排布的镜头</h1>
          <p>
            当前项目没有从统一项目脉络投影出镜头列表。
            页面不会用静态镜头卡片冒充制作状态。
          </p>
          <button
            className="button button--primary"
            type="button"
            onClick={() => onNavigate({ surface: "script", entity: "" })}
          >
            回到剧本
          </button>
        </div>
      </section>
    );
  }

  const primary = view.primaryAction;

  return (
    <section className="creation-surface storyboard-surface surface">
      <aside className="creation-rail" aria-label="分镜场次">
        <div className="section-heading">
          <div>
            <p className="eyebrow">场次</p>
            <h2>{view.sequenceLabel}</h2>
          </div>
        </div>
        {view.scenes.map((scene) => (
          <button
            key={scene.id}
            type="button"
            className={scene.id === view.selectedSceneId ? "creation-row is-active" : "creation-row"}
            aria-current={scene.id === view.selectedSceneId ? "true" : undefined}
            onClick={() => onNavigate({ entity: scene.firstShotId || scene.id, candidate: "", blocker: "" })}
          >
            <span>
              <strong>{scene.orderLabel} · {scene.label}</strong>
              <small>{scene.shotCount} 个镜头 · {scene.purpose}</small>
            </span>
            <em>{scene.durationLabel}</em>
          </button>
        ))}
      </aside>

      <div className="creation-workspace">
        <header className="creation-header">
          <div>
            <p className="breadcrumb">{view.sourceLabel}</p>
            <h1>镜头顺序和节奏是否支撑当前制作？</h1>
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
                  entity: primary.entity || view.selectedAssetId || view.selectedShotId,
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

        <div className="storyboard-layout">
          <section className="storyboard-board" aria-label="镜头排布">
            <div className="storyboard-strip">
              {view.shots.map((shot) => (
                <button
                  key={shot.id}
                  type="button"
                  className={shot.id === view.selectedShotId ? "storyboard-shot is-active" : "storyboard-shot"}
                  aria-current={shot.id === view.selectedShotId ? "true" : undefined}
                  onClick={() => onNavigate({ entity: shot.id, candidate: "", blocker: "" })}
                >
                  <span className={`status status--${shot.tone}`}>{shot.status}</span>
                  <strong>{shot.orderLabel}</strong>
                  <span>{shot.title}</span>
                  <small>{shot.durationLabel}</small>
                </button>
              ))}
            </div>

            <div className="shot-stage">
              <span className="shot-stage__icon" aria-hidden="true">
                <IconMovie size={28} stroke={1.5} />
              </span>
              <div>
                <p className="eyebrow">当前镜头</p>
                <h2>{view.selectedShot.title}</h2>
                <p>{view.selectedShot.blocking}</p>
              </div>
              <div className="shot-stage__meta">
                <span>{view.selectedShot.durationLabel}</span>
                <span>{view.selectedShot.trace}</span>
              </div>
            </div>

            <div className="shot-language-grid">
              {view.language.map((item) => (
                <section key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </section>
              ))}
            </div>
          </section>

          <aside className="creation-detail" aria-label="镜头资产依赖">
            <p className="eyebrow">资产依赖</p>
            <h2>{view.assetHeading}</h2>
            {view.assets.length ? (
              <ul className="asset-chip-list">
                {view.assets.map((asset) => (
                  <li key={asset.id}>
                    <IconCircleCheck aria-hidden="true" size={16} />
                    <button
                      type="button"
                      onClick={() =>
                        onNavigate({ surface: "asset-bible", entity: asset.id, candidate: "", blocker: "" })
                      }
                    >
                      <strong>{asset.label}</strong>
                      <span>{asset.kind}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-inline">当前镜头尚未绑定角色、场景或道具设定。</p>
            )}
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

export function storyboardView(
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
        purpose: "样例排布",
        durationLabel: `${scene.durationSeconds} 秒`,
        shotCount: shots.length,
        firstShotId: shots[0]?.shotRef ?? "",
        shotIds: shots.map((shot) => shot.shotRef)
      };
    });
    const selectedSceneId =
      scenes.find((scene) => scene.shotIds.includes(selectedEntityId))?.id ||
      scenes[0]?.id ||
      "";
    const selectedScene = scenes.find((scene) => scene.id === selectedSceneId);
    const sceneShots = data.fixture.shots.filter((shot) =>
      selectedScene?.shotIds.includes(shot.shotRef)
    );
    const selectedShot =
      sceneShots.find((shot) => shot.shotRef === selectedEntityId) ??
      sceneShots[0] ??
      data.fixture.shots[0];
    return {
      isEmpty: false,
      sequenceLabel: data.fixture.project.episodeName,
      sourceLabel: "界面样例 · 不写入项目",
      readiness: "样例分镜用于检查布局；真实项目会读取项目脉络中的镜头语言。",
      scenes,
      selectedSceneId,
      selectedShotId: selectedShot?.shotRef ?? "",
      selectedAssetId: data.fixture.assets[0]?.assetRef ?? "",
      shots: sceneShots.map((shot) => ({
        id: shot.shotRef,
        title: shot.displayName,
        orderLabel: `镜头 ${String(shot.sequence).padStart(2, "0")}`,
        durationLabel: `${shot.durationSeconds} 秒`,
        status: shot.videoStatus === "review_pending" ? "待审核" : "已纳入项目",
        tone: shot.videoStatus === "review_pending" ? "warning" : "muted"
      })),
      selectedShot: {
        title: selectedShot?.displayName ?? "当前镜头",
        blocking: selectedShot?.intent ?? "样例镜头尚无调度说明。",
        durationLabel: `${selectedShot?.durationSeconds ?? 0} 秒`,
        trace: "样例来源"
      },
      language: [
        { label: "景别", value: selectedShot?.shotSize ?? "待补齐" },
        { label: "镜头运动", value: "样例运动" },
        { label: "声音", value: "样例声音" },
        { label: "转场", value: "样例转场" }
      ],
      assetHeading: "样例资产",
      assets: data.fixture.assets.slice(0, 4).map((asset) => ({
        id: asset.assetRef,
        label: asset.displayName,
        kind: asset.assetType
      })),
      nextContext: "进入资产设定后检查角色、场景与道具一致性。",
      primaryAction: {
        label: "检查资产设定",
        enabled: true,
        reason: "界面样例导航，不会写入项目。",
        surface: "asset-bible" as const,
        entity: data.fixture.assets[0]?.assetRef ?? "",
        candidate: ""
      }
    };
  }

  const envelope = data.envelope;
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
  const assetEntities = envelope.entities.filter(
    (item) => item.entity_type === "entity" || item.entity_type === "resource"
  );
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
      shotCount: sceneShots.length,
      firstShotId: sceneShots[0]?.entity_id ?? "",
      shotIds
    };
  });
  const fallbackScene = {
    id: "storyboard-unscoped-shots",
    label: "当前镜头序列",
    orderLabel: "全部",
    purpose: "镜头尚未归入场次",
    durationLabel: formatDuration(sumDurations(shotEntities)),
    shotCount: shotEntities.length,
    firstShotId: shotEntities[0]?.entity_id ?? "",
    shotIds: shotEntities.map((item) => item.entity_id)
  };
  const scenes = sceneRows.length ? sceneRows : shotEntities.length ? [fallbackScene] : [];
  const selectedEntity = selectEntity(
    [...shotEntities, ...sceneEntities],
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
  const sceneShots = (selectedScene?.shotIds ?? [])
    .map((id) => entityById(shotEntities, id))
    .filter((item): item is StudioEntity => Boolean(item))
    .sort((left, right) => orderValueForStoryboard(left) - orderValueForStoryboard(right));
  const selectedShot =
    selectedEntity?.entity_type === "unit" && sceneShots.some((item) => item.entity_id === selectedEntity.entity_id)
      ? selectedEntity
      : sceneShots[0] ?? shotEntities[0] ?? null;
  const assetIds = selectedShot
    ? relationSources(envelope.relations, selectedShot.entity_id, "required_by")
    : [];
  const assets = assetIds
    .map((id) => entityById(assetEntities, id))
    .filter((item): item is StudioEntity => Boolean(item))
    .map((asset) => ({
      id: asset.entity_id,
      label: asset.label,
      kind: assetKind(asset)
    }));
  const primaryTarget = assets[0]?.id || envelope.allowed_actions.find((item) => item.action === "continue_to_asset_bible")?.target_entity_id || "";
  const primaryAction = allowedNavigationAction(envelope, "continue_to_asset_bible", {
    label: "检查资产设定",
    disabledLabel: "资产未准备",
    surface: "asset-bible",
    targetEntityId: primaryTarget
  });
  return {
    isEmpty: !shotEntities.length,
    sequenceLabel: sequence?.label || "制作序列",
    sourceLabel: envelope.authority_mode === "graph_v1" ? `真实项目脉络 · 版本 ${envelope.project_version}` : "旧项目文件",
    readiness:
      selectedShot
        ? "当前镜头语言、时长、调度和资产依赖来自同一项目脉络。"
        : "当前项目尚未提供可排布镜头。",
    scenes,
    selectedSceneId,
    selectedShotId: selectedShot?.entity_id ?? "",
    selectedAssetId: assets[0]?.id ?? "",
    shots: sceneShots.map((shot, index) => {
      const state = stateView(shot);
      return {
        id: shot.entity_id,
        title: shot.label,
        orderLabel: `镜头 ${metadataNumber(shot, ["shot_order"]) ?? index + 1}`,
        durationLabel: formatDuration(metadataNumber(shot, ["duration_seconds", "duration_sec"])),
        status: state.label,
        tone: state.tone
      };
    }),
    selectedShot: {
      title: selectedShot?.label || "当前镜头",
      blocking: metadataText(selectedShot, ["blocking"], "人物调度待补齐"),
      durationLabel: formatDuration(metadataNumber(selectedShot, ["duration_seconds", "duration_sec"])),
      trace: traceLabel(selectedShot)
    },
    language: [
      { label: "景别", value: metadataText(selectedShot, ["shot_size"], "待补齐") },
      { label: "机位", value: metadataText(selectedShot, ["camera_angle"], "待补齐") },
      { label: "运动", value: metadataText(selectedShot, ["movement", "camera_movement"], "待补齐") },
      { label: "声音", value: metadataText(selectedShot, ["sound"], "待补齐") },
      { label: "转场", value: metadataText(selectedShot, ["transition"], "待补齐") }
    ],
    assetHeading: assets.length ? `${assets.length} 个绑定资产` : "资产绑定待补齐",
    assets,
    nextContext:
      primaryAction.enabled
        ? "进入 Asset Bible 后继续检查当前镜头的角色、场景和道具锁定。"
        : "后端尚未允许进入资产检查，当前保持只读。",
    primaryAction: selectedShot
      ? primaryAction
      : disabledPrimaryAction("资产未准备", "当前没有选中的镜头。", "asset-bible")
  };
}

function orderValueForStoryboard(entity: StudioEntity): number {
  return (
    metadataNumber(entity, ["shot_order"]) ??
    metadataNumber(entity, ["order"]) ??
    Number.MAX_SAFE_INTEGER
  );
}

function assetKind(asset: StudioEntity): string {
  const kind = metadataText(asset, ["kind", "classification"]);
  if (kind === "character") return "人物";
  if (kind === "scene") return "场景";
  if (kind === "prop") return "道具";
  if (kind === "reference_set") return "参考";
  return asset.entity_type === "entity" ? "人物" : "资产";
}
