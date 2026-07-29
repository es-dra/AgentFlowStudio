import { useMemo } from "react";
import {
  IconArrowRight,
  IconCircleCheck,
  IconLibraryPhoto,
  IconShieldCheck
} from "@tabler/icons-react";

import type { SurfaceProps } from "../App";
import type { StudioEntity } from "../api/studioTypes";
import {
  allowedNavigationAction,
  disabledPrimaryAction,
  entityById,
  formatDuration,
  metadataList,
  metadataNumber,
  metadataRecords,
  metadataText,
  relationTargets,
  selectEntity,
  sortByProductionOrder,
  stateView,
  sumDurations,
  traceLabel
} from "./creationSurfaceModel";

export default function AssetBibleSurface({
  data,
  urlState,
  onNavigate
}: SurfaceProps) {
  const view = useMemo(
    () => assetBibleView(data, urlState.entity),
    [data, urlState.entity]
  );

  if (view.isEmpty) {
    return (
      <section className="creation-surface surface" aria-live="polite">
        <div className="surface-state surface-state--embedded">
          <p className="eyebrow">资产设定</p>
          <h1>还没有可复用的角色、场景或道具</h1>
          <p>
            当前项目还没有形成可复用的资产设定。
            页面不会创建平行资产清单。
          </p>
          <button
            className="button button--primary"
            type="button"
            onClick={() => onNavigate({ surface: "storyboard", entity: "" })}
          >
            回到分镜
          </button>
        </div>
      </section>
    );
  }

  const primary = view.primaryAction;

  return (
    <section className="creation-surface asset-bible-surface surface">
      <aside className="creation-rail" aria-label="资产清单">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Asset Bible</p>
            <h2>{view.assetCountLabel}</h2>
          </div>
        </div>
        {view.assets.map((asset) => (
          <button
            key={asset.id}
            type="button"
            className={asset.id === view.selectedAssetId ? "creation-row is-active" : "creation-row"}
            aria-current={asset.id === view.selectedAssetId ? "true" : undefined}
            onClick={() => onNavigate({ entity: asset.id, candidate: "", blocker: "" })}
          >
            <span>
              <strong>{asset.label}</strong>
              <small>{asset.kind} · {asset.usageLabel}</small>
            </span>
            <em>{asset.status}</em>
          </button>
        ))}
      </aside>

      <div className="creation-workspace">
        <header className="creation-header">
          <div>
            <p className="breadcrumb">{view.sourceLabel}</p>
            <h1>人物、场景和道具是否能跨镜头复用？</h1>
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
                  entity: primary.entity || view.firstUsageId || view.selectedAssetId,
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

        <div className="asset-bible-layout">
          <section className="asset-detail-stage" aria-label="资产设定详情">
            <div className="asset-title-block">
              <span className="asset-title-block__icon" aria-hidden="true">
                <IconShieldCheck size={28} stroke={1.5} />
              </span>
              <div>
                <p className="eyebrow">{view.selectedAsset.kind}</p>
                <h2>{view.selectedAsset.label}</h2>
                <p>{view.selectedAsset.identity}</p>
              </div>
              <span className={`status status--${view.selectedAsset.tone}`}>
                {view.selectedAsset.status}
              </span>
            </div>

            <div className="asset-proof-grid">
              <section>
                <span>复用范围</span>
                <strong>{view.selectedAsset.usageLabel}</strong>
                <small>{view.selectedAsset.sceneLabel}</small>
              </section>
              <section>
                <span>批准图像</span>
                <strong>{view.selectedAsset.imageCountLabel}</strong>
                <small>{view.selectedAsset.trace}</small>
              </section>
              <section>
                <span>项目版本</span>
                <strong>{view.projectVersionLabel}</strong>
                <small>{view.readOnlyLabel}</small>
              </section>
            </div>

            <div className="asset-rules">
              <section>
                <p className="eyebrow">正向锁定</p>
                {view.selectedAsset.positiveTraits.length ? (
                  <ul>
                    {view.selectedAsset.positiveTraits.map((item) => (
                      <li key={item}>
                        <IconCircleCheck aria-hidden="true" size={16} />
                        {item}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty-inline">当前资产尚未提供正向锁定描述。</p>
                )}
              </section>
              <section>
                <p className="eyebrow">禁止漂移</p>
                {view.selectedAsset.negativeLocks.length ? (
                  <ul>
                    {view.selectedAsset.negativeLocks.map((item) => (
                      <li key={item}>
                        <IconCircleCheck aria-hidden="true" size={16} />
                        {item}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty-inline">当前没有额外禁止项。</p>
                )}
              </section>
            </div>
          </section>

          <aside className="creation-detail" aria-label="资产追溯">
            <p className="eyebrow">追溯</p>
            <h2>{view.traceHeading}</h2>
            <dl className="detail-list">
              <div>
                <dt>连续性</dt>
                <dd>{view.selectedAsset.continuityLabel}</dd>
              </div>
              <div>
                <dt>来源证据</dt>
                <dd>{view.selectedAsset.evidenceLabel}</dd>
              </div>
              <div>
                <dt>引用时长</dt>
                <dd>{view.selectedAsset.durationLabel}</dd>
              </div>
            </dl>
            {view.usageShots.length ? (
              <ul className="usage-shot-list">
                {view.usageShots.map((shot) => (
                  <li key={shot.id}>
                    <IconLibraryPhoto aria-hidden="true" size={16} />
                    <button
                      type="button"
                      onClick={() =>
                        onNavigate({ surface: "storyboard", entity: shot.id, candidate: "", blocker: "" })
                      }
                    >
                      <strong>{shot.label}</strong>
                      <span>{shot.durationLabel}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-inline">当前资产还没有绑定到镜头。</p>
            )}
          </aside>
        </div>
      </div>
    </section>
  );
}

export function assetBibleView(
  data: SurfaceProps["data"],
  selectedEntityId = ""
) {
  if (data.source === "fixture") {
    const selectedAsset =
      data.fixture.assets.find((asset) => asset.assetRef === selectedEntityId) ??
      data.fixture.assets[0];
    const usageShots = data.fixture.shots.filter((shot) =>
      selectedAsset?.referencedByShots.includes(shot.shotRef)
    );
    return {
      isEmpty: false,
      sourceLabel: "界面样例 · 不写入项目",
      readiness: "样例资产用于检查布局；真实项目会读取项目脉络里的资产设定。",
      assetCountLabel: `${data.fixture.assets.length} 个样例资产`,
      projectVersionLabel: `版本 ${data.fixture.project.projectVersion}`,
      readOnlyLabel: "样例只读",
      traceHeading: "样例追溯",
      selectedAssetId: selectedAsset?.assetRef ?? "",
      firstUsageId: usageShots[0]?.shotRef ?? "",
      assets: data.fixture.assets.map((asset) => ({
        id: asset.assetRef,
        label: asset.displayName,
        kind: asset.assetType,
        usageLabel: `${asset.referencedByShots.length} 个镜头`,
        status: asset.mediaStatus === "adopted" ? "已采用" : "待审核"
      })),
      selectedAsset: {
        label: selectedAsset?.displayName ?? "当前资产",
        kind: selectedAsset?.assetType ?? "资产",
        identity: "样例视觉身份，不写入项目。",
        usageLabel: `${selectedAsset?.referencedByShots.length ?? 0} 个镜头`,
        sceneLabel: "样例场次",
        imageCountLabel: selectedAsset?.mediaStatus === "adopted" ? "1 张" : "待审核",
        trace: "样例来源",
        status: selectedAsset?.mediaStatus === "adopted" ? "已采用" : "待审核",
        tone: selectedAsset?.mediaStatus === "adopted" ? "success" : "warning",
        positiveTraits: ["保持样例资产身份"],
        negativeLocks: [],
        continuityLabel: "样例连续性",
        evidenceLabel: "样例证据",
        durationLabel: formatDuration(sumFixtureDurations(usageShots))
      },
      usageShots: usageShots.map((shot) => ({
        id: shot.shotRef,
        label: shot.displayName,
        durationLabel: `${shot.durationSeconds} 秒`
      })),
      primaryAction: {
        label: "回到制作画布",
        enabled: true,
        reason: "界面样例导航，不会写入项目。",
        surface: "canvas" as const,
        entity: usageShots[0]?.shotRef ?? "",
        candidate: ""
      }
    };
  }

  const envelope = data.envelope;
  const assets = sortByProductionOrder(
    envelope.entities
      .filter((item) => item.entity_type === "entity" || item.entity_type === "resource")
      .map((entity) => ({ entity }))
  ).map((item) => item.entity);
  const shots = envelope.entities.filter((item) => item.entity_type === "unit");
  const scenes = envelope.entities.filter((item) => item.entity_type === "location");
  const selected = selectEntity(
    assets,
    selectedEntityId,
    envelope.resume_target.entity_id || envelope.focused_entity?.entity_id || ""
  );
  const usageIds = selected
    ? relationTargets(envelope.relations, selected.entity_id, "required_by")
    : [];
  const usageShotEntities = usageIds
    .map((id) => entityById(shots, id))
    .filter((item): item is StudioEntity => Boolean(item));
  const imageCount = selected
    ? relationTargets(envelope.relations, selected.entity_id, "approved_image").length
    : 0;
  const primaryTarget = usageShotEntities[0]?.entity_id || selected?.entity_id || "";
  const primaryAction = allowedNavigationAction(envelope, "return_to_canvas", {
    label: "回到制作画布",
    disabledLabel: "画布未准备",
    surface: "canvas",
    targetEntityId: primaryTarget
  });
  const selectedState = selected ? stateView(selected) : { label: "未选择", tone: "muted" };
  const continuity = metadataRecords(selected, "continuity_states");
  const evidence = metadataRecords(selected, "source_evidence");
  const assetRows = assets.map((asset) => {
    const assetUsageIds = relationTargets(envelope.relations, asset.entity_id, "required_by");
    const state = stateView(asset);
    return {
      id: asset.entity_id,
      label: asset.label,
      kind: assetKind(asset),
      usageLabel: `${assetUsageIds.length} 个引用`,
      status: metadataText(asset, ["asset_bible_review_state", "review_state"], state.label)
    };
  });
  return {
    isEmpty: !assets.length,
    sourceLabel: envelope.authority_mode === "graph_v1" ? `真实项目脉络 · 版本 ${envelope.project_version}` : "旧项目文件",
    readiness:
      selected
        ? "当前资产身份、锁定项、引用镜头和批准图像关系来自同一项目脉络。"
        : "当前项目尚未提供可复用资产。",
    assetCountLabel: `${assets.length} 个资产`,
    projectVersionLabel: `版本 ${envelope.project_version}`,
    readOnlyLabel: primaryAction.enabled ? "可回到画布" : "只读待准备",
    traceHeading: traceLabel(selected),
    selectedAssetId: selected?.entity_id ?? "",
    firstUsageId: primaryTarget,
    assets: assetRows,
    selectedAsset: {
      label: selected?.label || "当前资产",
      kind: selected ? assetKind(selected) : "资产",
      identity: metadataText(selected, ["visual_identity", "appearance", "style", "space"], "视觉身份待补齐"),
      usageLabel: `${usageIds.length} 个引用`,
      sceneLabel: `${sceneUsageCount(usageIds, scenes)} 个场次相关`,
      imageCountLabel: imageCount ? `${imageCount} 张` : "尚无批准图",
      trace: traceLabel(selected),
      status: metadataText(selected, ["asset_bible_review_state", "review_state"], selectedState.label),
      tone: selectedState.tone,
      positiveTraits: metadataList(selected, "positive_traits"),
      negativeLocks: metadataList(selected, "negative_locks"),
      continuityLabel: continuity.length ? `${continuity.length} 条连续性记录` : "连续性记录待补齐",
      evidenceLabel: evidence.length ? `${evidence.length} 条来源证据` : "来源证据待补齐",
      durationLabel: formatDuration(sumDurations(usageShotEntities))
    },
    usageShots: usageShotEntities.slice(0, 8).map((shot) => ({
      id: shot.entity_id,
      label: shot.label,
      durationLabel: formatDuration(metadataNumber(shot, ["duration_seconds", "duration_sec"]))
    })),
    primaryAction: selected
      ? primaryAction
      : disabledPrimaryAction("画布未准备", "当前没有选中的资产。", "canvas")
  };
}

function assetKind(asset: StudioEntity): string {
  const kind = metadataText(asset, ["kind", "classification", "asset_subtype"]);
  if (kind === "character") return "人物";
  if (kind === "scene") return "场景";
  if (kind === "prop") return "道具";
  if (kind === "reference_set") return "参考";
  if (kind === "graphic") return "图形";
  return asset.entity_type === "entity" ? "人物" : "资产";
}

function sceneUsageCount(usageIds: string[], scenes: StudioEntity[]): number {
  const sceneIds = new Set(scenes.map((scene) => scene.entity_id));
  return usageIds.filter((id) => sceneIds.has(id)).length;
}

function sumFixtureDurations(shots: Array<{ durationSeconds: number }>): number | null {
  if (!shots.length) return null;
  return shots.reduce((total, shot) => total + shot.durationSeconds, 0);
}
