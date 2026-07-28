import { IconArrowLeft, IconListDetails } from "@tabler/icons-react";

import type { SurfaceProps } from "../App";
import { surfaceLabel, type AppSurface } from "../api/studioTypes";

interface PlaceholderSurfaceProps extends SurfaceProps {
  surface: Exclude<AppSurface, "overview" | "canvas" | "review" | "delivery">;
}

export default function PlaceholderSurface({
  data,
  surface,
  onNavigate
}: PlaceholderSurfaceProps) {
  const entities =
    data.source === "live" ? data.envelope.entities.slice(0, 8) : [];

  return (
    <section className="placeholder-surface surface">
      <header className="surface-heading">
        <div>
          <p className="eyebrow">{surfaceLabel(surface)}</p>
          <h1>{placeholderQuestion(surface)}</h1>
          <p>当前入口保留同一项目、版本和助手上下文。</p>
        </div>
        <button
          className="button button--primary"
          type="button"
          onClick={() => onNavigate({ surface: "canvas" })}
        >
          <IconArrowLeft aria-hidden="true" size={18} />
          返回制作画布
        </button>
      </header>
      <section className="panel placeholder-content">
        <IconListDetails aria-hidden="true" size={28} />
        {entities.length ? (
          <>
            <h2>服务端对象摘要</h2>
            <ul>
              {entities.map((entity) => (
                <li key={entity.entity_id}>
                  <strong>{entity.label}</strong>
                  <span>{entity.state}</span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <>
            <h2>专业工具尚未进入当前垂直切片</h2>
            <p>
              这里不会用静态表单冒充剧本、分镜或资产工具。当前项目内容仍安全保留。
            </p>
          </>
        )}
      </section>
    </section>
  );
}

function placeholderQuestion(surface: PlaceholderSurfaceProps["surface"]) {
  if (surface === "script") return "故事结构和文本是否成立？";
  if (surface === "storyboard") return "镜头顺序、节奏和拍摄意图是否成立？";
  return "人物、场景和道具是否一致、可复用？";
}
