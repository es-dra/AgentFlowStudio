import { useMemo, useState, type CSSProperties } from "react";
import {
  IconFocus2,
  IconMinus,
  IconPlus,
  IconRoute,
  IconZoomScan
} from "@tabler/icons-react";

import type { SurfaceProps } from "../App";

export default function CanvasSurface({
  data,
  urlState,
  onNavigate
}: SurfaceProps) {
  const [zoom, setZoom] = useState(100);
  const view = useMemo(() => canvasView(data), [data]);
  const [selectedEntity, setSelectedEntity] = useState(
    urlState.entity || view.nodes[0]?.id || ""
  );
  const selected = view.nodes.find((item) => item.id === selectedEntity);

  const chooseEntity = (entityId: string) => {
    setSelectedEntity(entityId);
    onNavigate({ entity: entityId });
  };

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
              <span>{scene.duration} 秒</span>
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
                <small>{node.duration} 秒</small>
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
            onClick={() => {
              const task = view.nodes.find((item) => item.status === "制作中");
              if (task) chooseEntity(task.id);
            }}
          >
            <IconFocus2 aria-hidden="true" size={18} />
            定位当前任务
          </button>
          <span className="toolbar-spacer" />
          <button
            className="button button--primary"
            type="button"
            onClick={() =>
              onNavigate({
                surface: "review",
                candidate: view.primaryCandidate,
                entity: "shot-03"
              })
            }
          >
            前往镜头 03 审核
          </button>
        </header>

        <div className="canvas-title">
          <div>
            <p className="eyebrow">当前关系</p>
            <h1>第二场 · 灯塔警示</h1>
          </div>
          <span>3 个镜头 · 28 秒</span>
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
                  <small>{node.duration} 秒</small>
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
            <small>{selected ? `${selected.status} · ${selected.duration} 秒` : ""}</small>
          </div>
          <button
            className="text-action"
            type="button"
            disabled={!selected}
            title={selected ? "查看对象关系摘要" : "请先选择对象"}
          >
            查看来源与影响
          </button>
        </footer>
      </div>
    </section>
  );
}

function canvasView(data: SurfaceProps["data"]) {
  if (data.source === "fixture") {
    const nodes = data.fixture.shots
      .filter((item) => item.sceneRef === "scene-02")
      .map((shot) => ({
        id: shot.shotRef,
        label: shot.displayName,
        duration: shot.durationSeconds,
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
        nodes: data.fixture.shots
          .filter((shot) => scene.shotRefs.includes(shot.shotRef))
          .map((shot) => ({
            id: shot.shotRef,
            label: `镜头 ${String(shot.sequence).padStart(2, "0")} · ${shot.displayName}`,
            duration: shot.durationSeconds
          }))
      })),
      primaryCandidate: data.fixture.project.resumeTarget.entityRef
    };
  }

  const nodes = data.envelope.entities.slice(0, 6).map((entity) => ({
    id: entity.entity_id,
    label: entity.label,
    duration: Number(entity.metadata.duration_seconds ?? 0),
    type: entity.entity_type,
    status: entity.state,
    tone: entity.state === "active" ? "active" : "muted",
    imageUrl: ""
  }));
  return {
    nodes,
    scenes: [
      {
        id: "live-entities",
        label: "服务端对象",
        duration: nodes.reduce((total, item) => total + item.duration, 0),
        nodes
      }
    ],
    primaryCandidate: data.envelope.review_queue[0]?.target_entity_id ?? ""
  };
}

function toChineseNumber(value: number) {
  return ["零", "一", "二", "三"][value] ?? String(value);
}
