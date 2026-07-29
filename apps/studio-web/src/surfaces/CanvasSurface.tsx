import { useMemo, useState, type CSSProperties } from "react";
import {
  IconFocus2,
  IconMinus,
  IconPlus,
  IconRoute,
  IconZoomScan
} from "@tabler/icons-react";

import type { SurfaceProps } from "../App";
import {
  entityLabel,
  entityTypeLabel,
  firstAvailableSurface,
  numberFrom,
  publicCopy,
  stateLabel,
  stateTone
} from "../api/studioAdapter";
import type {
  StudioEntity,
  StudioRelation
} from "../api/studioTypes";

export default function CanvasSurface({
  data,
  urlState,
  onNavigate
}: SurfaceProps) {
  const [zoom, setZoom] = useState(100);
  const view = useMemo(() => canvasView(data), [data]);
  const focusedEntityIsVisible = view.nodes.some(
    (item) => item.id === view.focusedEntity
  );
  const selectedEntity = view.nodes.some((item) => item.id === urlState.entity)
    ? urlState.entity
    : focusedEntityIsVisible
      ? view.focusedEntity
      : view.nodes[0]?.id || "";
  const selected = view.nodes.find((item) => item.id === selectedEntity);
  const currentTask = view.nodes.find((item) => item.tone === "active");
  const primaryDisabled = !view.primaryAction.enabled;

  const chooseEntity = (entityId: string) => {
    onNavigate({ entity: entityId });
  };

  if (!view.nodes.length) {
    return (
      <section className="canvas surface">
        <div className="surface-state surface-state--embedded" aria-live="polite">
          <p className="eyebrow">制作画布</p>
          <h1>当前项目还没有可展示对象</h1>
          <p>页面不会补入虚构节点。完成剧本或分镜后，可继续在这里组织制作关系。</p>
          <button
            className="button button--primary"
            type="button"
            onClick={() => onNavigate({ surface: "overview" })}
          >
            返回项目概览
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="canvas surface">
      <aside className="canvas-scenes" aria-label="场次定位">
        <div className="section-heading">
          <h2>项目结构</h2>
        </div>
        {view.scenes.map((scene) => (
          <section key={scene.id} className="scene-group">
            <header>
              <strong>{scene.label}</strong>
              <span>{scene.durationLabel}</span>
            </header>
            {scene.nodes.map((node) => (
              <button
                key={node.id}
                type="button"
                className={selectedEntity === node.id ? "scene-row is-active" : "scene-row"}
                aria-current={selectedEntity === node.id ? "true" : undefined}
                onClick={() => chooseEntity(node.id)}
              >
                <span>{node.label}</span>
                <small>{node.durationLabel}</small>
              </button>
            ))}
          </section>
        ))}
      </aside>

      <div className="canvas-workspace">
        <header className="canvas-toolbar">
          <div>
            <span>视图</span>
            <button className="control-button" type="button">
              按场景
            </button>
          </div>
          <div className="zoom-control" aria-label="画布缩放">
            <IconZoomScan aria-hidden="true" size={18} />
            <button
              className="icon-button"
              type="button"
              aria-label="缩小画布"
              onClick={() => setZoom((value) => Math.max(75, value - 25))}
            >
              <IconMinus aria-hidden="true" size={17} />
            </button>
            <span>{zoom}%</span>
            <button
              className="icon-button"
              type="button"
              aria-label="放大画布"
              onClick={() => setZoom((value) => Math.min(125, value + 25))}
            >
              <IconPlus aria-hidden="true" size={17} />
            </button>
          </div>
          <button
            className="control-button"
            type="button"
            disabled={!currentTask}
            title={currentTask ? "定位当前制作任务" : "当前没有进行中的任务"}
            onClick={() => {
              if (currentTask) chooseEntity(currentTask.id);
            }}
          >
            <IconFocus2 aria-hidden="true" size={18} />
            定位当前任务
          </button>
          <span className="toolbar-spacer" />
          <button
            className="button button--primary"
            type="button"
            disabled={primaryDisabled}
            title={primaryDisabled ? view.primaryAction.reason : view.primaryAction.label}
            onClick={() =>
              onNavigate({
                surface: view.primaryAction.surface,
                candidate: view.primaryAction.candidate,
                entity: view.primaryAction.entity
              })
            }
          >
            {view.primaryAction.label}
          </button>
        </header>

        <div className="canvas-title">
          <div>
            <p className="eyebrow">当前关系</p>
            <h1>{view.title}</h1>
          </div>
          <span>{view.subtitle}</span>
        </div>

        <div className="graph-stage" style={{ "--canvas-zoom": zoom / 100 } as CSSProperties}>
          <div className="graph-row">
            {view.nodes.map((node, index) => (
              <div className="graph-node-wrap" key={node.id}>
                <button
                  type="button"
                  className={selectedEntity === node.id ? "graph-node is-selected" : "graph-node"}
                  onClick={() => chooseEntity(node.id)}
                >
                  {node.imageUrl ? <img src={node.imageUrl} alt="" /> : null}
                  <span className="graph-node__type">{node.type}</span>
                  <strong>{node.label}</strong>
                  <small>{node.durationLabel}</small>
                  <span className={`status status--${node.tone}`}>{node.status}</span>
                </button>
                {index < view.nodes.length - 1 ? (
                  <span className="graph-connector" aria-label="顺序连接">
                    <IconRoute aria-hidden="true" size={22} />
                  </span>
                ) : null}
              </div>
            ))}
          </div>
        </div>

        <footer className="selection-tray">
          <div>
            <span>当前选择</span>
            <strong>{selected?.label ?? "未选择对象"}</strong>
            <small>{selected ? `${selected.status} · ${selected.durationLabel}` : ""}</small>
          </div>
          <button
            className="text-action"
            type="button"
            disabled
            title={selected ? "当前对象尚无可查看的影响详情" : "请先选择对象"}
          >
            查看来源与影响
          </button>
        </footer>
      </div>
    </section>
  );
}

export function canvasView(data: SurfaceProps["data"]) {
  if (data.source === "fixture") {
    const nodes = data.fixture.shots
      .filter((item) => item.sceneRef === "scene-02")
      .map((shot) => ({
        id: shot.shotRef,
        label: shot.displayName,
        duration: shot.durationSeconds,
        durationLabel: `${shot.durationSeconds} 秒`,
        type: `镜头 ${String(shot.sequence).padStart(2, "0")}`,
        status:
          shot.videoStatus === "review_pending"
            ? "待审核"
            : shot.keyframeStatus === "generating"
              ? "制作中"
              : "已采用",
        tone:
          shot.videoStatus === "review_pending"
            ? "warning"
            : shot.keyframeStatus === "generating"
              ? "active"
              : "success",
        imageUrl: shot.imageUrl
      }));
    return {
      nodes,
      scenes: data.fixture.scenes.map((scene) => ({
        id: scene.sceneRef,
        label: `第${toChineseNumber(scene.sequence)}场 · ${scene.title}`,
        duration: scene.durationSeconds,
        durationLabel: `${scene.durationSeconds} 秒`,
        nodes: data.fixture.shots
          .filter((shot) => scene.shotRefs.includes(shot.shotRef))
          .map((shot) => ({
            id: shot.shotRef,
            label: `镜头 ${String(shot.sequence).padStart(2, "0")} · ${shot.displayName}`,
            duration: shot.durationSeconds,
            durationLabel: `${shot.durationSeconds} 秒`
          }))
      })),
      focusedEntity: "",
      title: "第二场 · 灯塔警示",
      subtitle: "3 个镜头 · 28 秒",
      primaryAction: {
        label: "前往镜头 03 审核",
        enabled: true,
        reason: "",
        surface: "review" as const,
        candidate: data.fixture.project.resumeTarget.entityRef,
        entity: "shot-03"
      }
    };
  }

  const envelope = data.envelope;
  const summary = envelope.surface_summary;
  const unitEntities = envelope.entities.filter((item) => item.entity_type === "unit");
  const displayEntities = (unitEntities.length ? unitEntities : envelope.entities).slice(0, 12);
  const nodes = displayEntities.map((entity) => liveNode(entity));
  const nodesById = new Map(nodes.map((item) => [item.id, item]));
  const primaryCandidate =
    envelope.resume_target.surface === "review"
      ? envelope.resume_target.entity_id
      : envelope.review_queue[0]?.target_entity_id ?? "";
  const focusedEntity =
    envelope.focused_entity?.entity_id ??
    envelope.resume_target.entity_id ??
    nodes[0]?.id ??
    "";
  return {
    nodes,
    scenes: liveScenes(envelope.entities, nodesById, data.envelope.relations),
    focusedEntity,
    title:
      publicCopy(summary.headline) ||
      envelope.focused_entity?.label ||
      entityLabel(envelope, focusedEntity, "当前制作结构"),
    subtitle: `${summary.entity_count} 个对象 · ${summary.attention_count} 个需注意`,
    primaryAction: {
      label: primaryCandidate
        ? `前往${entityLabel(envelope, primaryCandidate, "候选对象")}审核`
        : "等待审核候选",
      enabled: Boolean(primaryCandidate),
      reason: envelope.resume_target.reason || "当前服务投影没有审核目标",
      surface: firstAvailableSurface(envelope.resume_target.surface, "review"),
      candidate: primaryCandidate,
      entity: primaryCandidate
    }
  };
}

function toChineseNumber(value: number) {
  return ["零", "一", "二", "三"][value] ?? String(value);
}

function liveNode(entity: StudioEntity) {
  const duration = numberFrom(entity.metadata.duration_seconds);
  return {
    id: entity.entity_id,
    label: entity.label,
    duration,
    durationLabel: duration === null ? "时长待提供" : `${duration} 秒`,
    type: entityTypeLabel(entity.entity_type),
    status: stateLabel(entity.state),
    tone: stateTone(entity.state),
    imageUrl: ""
  };
}

function liveScenes(
  entities: StudioEntity[],
  nodesById: Map<string, ReturnType<typeof liveNode>>,
  relations: StudioRelation[]
) {
  const entityById = new Map(entities.map((item) => [item.entity_id, item]));
  const groups = entities
    .filter((item) => item.entity_type === "location" || item.entity_type === "collection")
    .map((entity) => {
      const childIds = relations
        .filter((relation) => relation.from_id === entity.entity_id && relation.relation_type === "contains")
        .map((relation) => relation.to_id);
      const childNodes = childIds
        .map((id) => nodesById.get(id))
        .filter((item): item is ReturnType<typeof liveNode> => Boolean(item));
      if (!childNodes.length) return null;
      const duration = sumDurations(childNodes);
      return {
        id: entity.entity_id,
        label: entity.label || entityById.get(entity.entity_id)?.label || "当前分组",
        duration,
        durationLabel: duration === null ? `${childNodes.length} 个对象` : `${duration} 秒`,
        nodes: childNodes
      };
    })
    .filter((item): item is NonNullable<typeof item> => Boolean(item));

  if (groups.length) return groups;
  const fallbackNodes = [...nodesById.values()];
  const duration = sumDurations(fallbackNodes);
  return [
    {
      id: "live-entities",
      label: "当前制作对象",
      duration,
      durationLabel: duration === null ? `${fallbackNodes.length} 个对象` : `${duration} 秒`,
      nodes: fallbackNodes
    }
  ];
}

function sumDurations(nodes: Array<ReturnType<typeof liveNode>>): number | null {
  const values = nodes
    .map((item) => item.duration)
    .filter((value): value is number => value !== null);
  if (!values.length) return null;
  return values.reduce((total, value) => total + value, 0);
}
