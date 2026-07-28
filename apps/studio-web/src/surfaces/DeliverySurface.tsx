import { useMemo, useState } from "react";
import {
  IconAlertCircle,
  IconArrowRight,
  IconCircleCheck,
  IconMovie,
  IconPlayerPlayFilled
} from "@tabler/icons-react";

import type { SurfaceProps } from "../App";
import { MediaStage, formatSeconds } from "../components/MediaStage";

export default function DeliverySurface({
  data,
  urlState,
  onNavigate
}: SurfaceProps) {
  const view = useMemo(() => deliveryView(data), [data]);
  const initialBlocker = Math.max(
    0,
    view.blockers.findIndex((item) => item.id === urlState.blocker)
  );
  const [selectedBlocker, setSelectedBlocker] = useState(initialBlocker);
  const blocker = view.blockers[selectedBlocker];

  const chooseBlocker = (index: number) => {
    setSelectedBlocker(index);
    onNavigate({ blocker: view.blockers[index]?.id ?? "" });
  };

  const continueBlocker = () => {
    if (!blocker) return;
    onNavigate({
      surface: blocker.surface,
      entity: blocker.entity,
      candidate: blocker.candidate
    });
  };

  return (
    <section className="delivery surface">
      <div className="delivery-workspace">
        <header className="object-header">
          <div>
            <p className="eyebrow">合成交付</p>
            <div className="object-title">
              <h1>当前合成版本 · 版本{toChineseNumber(view.version)}</h1>
              <span className="status status--warning">尚未就绪</span>
            </div>
          </div>
          <span>当前可播放 {formatSeconds(view.playableDuration)} / 目标 {formatSeconds(view.targetDuration)}</span>
        </header>

        {view.mediaUrl ? (
          <MediaStage
            imageUrl={view.mediaUrl}
            title="当前合成版本"
            durationSeconds={view.playableDuration}
          />
        ) : (
          <div className="media-unavailable media-unavailable--large">
            <IconMovie aria-hidden="true" size={28} />
            当前服务信封尚未提供受控交付媒体地址
          </div>
        )}

        <section className="timeline" aria-label="装配时间线">
          <div className="timeline__tracks">
            {view.shots.map((shot) => (
              <button
                key={shot.id}
                type="button"
                className={`timeline-shot timeline-shot--${shot.tone}`}
                style={{ flexGrow: Math.max(shot.duration, 6) }}
                onClick={() => {
                  const index = view.blockers.findIndex(
                    (item) => item.entity === shot.id
                  );
                  if (index >= 0) chooseBlocker(index);
                }}
              >
                <span>镜头 {String(shot.sequence).padStart(2, "0")}</span>
                <strong>{shot.label}</strong>
                <small>{shot.duration} 秒 · {shot.status}</small>
              </button>
            ))}
          </div>
          <div className="timeline__axis" aria-hidden="true">
            <span>00:00</span>
            <span>00:22</span>
            <span>00:50</span>
            <span>01:17</span>
          </div>
          <div className="timeline__legend">
            <span><IconCircleCheck aria-hidden="true" size={16} />已完成</span>
            <span><IconAlertCircle aria-hidden="true" size={16} />待处理</span>
          </div>
        </section>

        <footer className="delivery-spec">
          <span>最终交付配置</span>
          <strong>1920 × 1080 / 24 帧 / 立体声</strong>
        </footer>
      </div>

      <aside className="delivery-check">
        <div className="section-heading">
          <div>
            <p className="eyebrow">交付检查</p>
            <h2>阻塞项（{view.blockers.length}）</h2>
          </div>
        </div>
        <ol className="blocker-list">
          {view.blockers.map((item, index) => (
            <li key={item.id}>
              <button
                type="button"
                className={selectedBlocker === index ? "is-active" : ""}
                aria-current={selectedBlocker === index ? "true" : undefined}
                onClick={() => chooseBlocker(index)}
              >
                <IconAlertCircle aria-hidden="true" size={18} />
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.note}</small>
                </span>
                <IconArrowRight aria-hidden="true" size={17} />
              </button>
            </li>
          ))}
        </ol>

        <section className="version-list">
          <p className="eyebrow">版本记录</p>
          {view.versions.map((item) => (
            <div key={item.version} className={item.current ? "version-row is-current" : "version-row"}>
              <span>
                <strong>版本{toChineseNumber(item.version)}</strong>
                <small>{formatSeconds(item.duration)}</small>
              </span>
              <time>{item.time}</time>
              <IconPlayerPlayFilled aria-label="播放此版本" size={17} />
            </div>
          ))}
        </section>

        <button
          className="button button--primary button--large"
          type="button"
          onClick={continueBlocker}
          disabled={!blocker}
        >
          继续处理阻塞项
          <IconArrowRight aria-hidden="true" size={18} />
        </button>
        <button
          className="button button--quiet"
          type="button"
          disabled
          title="阻塞清零并由服务端允许后才能创建交付版本"
        >
          创建交付版本
        </button>
        <small className="action-explanation">完成全部阻塞项后才可使用</small>
      </aside>
    </section>
  );
}

function deliveryView(data: SurfaceProps["data"]) {
  if (data.source === "fixture") {
    const fixture = data.fixture;
    return {
      version: fixture.delivery.deliveryVersion,
      playableDuration: fixture.delivery.playableDurationSeconds,
      targetDuration: fixture.project.targetDurationSeconds,
      mediaUrl: fixture.shots[2]?.imageUrl ?? "",
      shots: fixture.shots.map((shot) => ({
        id: shot.shotRef,
        sequence: shot.sequence,
        label: shot.displayName,
        duration: shot.durationSeconds,
        status:
          shot.videoStatus === "review_pending"
            ? "待审核"
            : shot.keyframeStatus === "generating"
              ? "制作中"
              : shot.videoStatus === "not_started"
                ? "尚未开始"
                : "已完成",
        tone:
          shot.videoStatus === "review_pending"
            ? "warning"
            : shot.keyframeStatus === "generating"
              ? "active"
              : shot.videoStatus === "not_started"
                ? "muted"
                : "success"
      })),
      blockers: [
        {
          id: "shot-03-review",
          label: "镜头 03 候选待审核",
          note: "8 秒 · 需要导演决定",
          surface: "review" as const,
          entity: "shot-03",
          candidate: "candidate-shot-03-video-v2"
        },
        {
          id: "shot-05-task",
          label: "镜头 05 关键画面制作中",
          note: "9 秒 · 当前进度 46%",
          surface: "canvas" as const,
          entity: "shot-05",
          candidate: ""
        },
        {
          id: "shot-07-missing",
          label: "镜头 07 视频尚未制作",
          note: "13 秒 · 等待发起制作",
          surface: "canvas" as const,
          entity: "shot-07",
          candidate: ""
        }
      ],
      versions: [
        { version: 3, duration: 47, time: "今天 14:32", current: true },
        { version: 2, duration: 47, time: "今天 11:08", current: false },
        { version: 1, duration: 22, time: "昨天 18:40", current: false }
      ]
    };
  }

  return {
    version: data.envelope.project_version,
    playableDuration: 0,
    targetDuration: 0,
    mediaUrl: "",
    shots: data.envelope.entities.map((entity, index) => ({
      id: entity.entity_id,
      sequence: index + 1,
      label: entity.label,
      duration: Number(entity.metadata.duration_seconds ?? 0),
      status: entity.state,
      tone: entity.state === "active" ? "active" : "muted"
    })),
    blockers: data.envelope.recovery_summary.attention_required
      ? [
          {
            id: "recovery-attention",
            label: "制作任务需要核对",
            note: data.envelope.recovery_summary.message,
            surface: "delivery" as const,
            entity: "",
            candidate: ""
          }
        ]
      : [],
    versions: [
      {
        version: data.envelope.project_version,
        duration: 0,
        time: "服务端当前版本",
        current: true
      }
    ]
  };
}

function toChineseNumber(value: number) {
  return ["零", "一", "二", "三", "四", "五"][value] ?? String(value);
}
