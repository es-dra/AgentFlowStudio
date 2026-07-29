import { useMemo } from "react";
import {
  IconAlertCircle,
  IconArrowRight,
  IconCircleCheck,
  IconMovie,
  IconPlayerPlayFilled
} from "@tabler/icons-react";

import type { SurfaceProps } from "../App";
import {
  stateLabel
} from "../api/studioAdapter";
import { MediaStage, formatSeconds } from "../components/MediaStage";

export default function DeliverySurface({
  data,
  urlState,
  onNavigate
}: SurfaceProps) {
  const view = useMemo(() => deliveryView(data), [data]);
  const selectedBlocker = Math.max(
    0,
    view.blockers.findIndex((item) => item.id === urlState.blocker)
  );
  const blocker = view.blockers[selectedBlocker];

  const chooseBlocker = (index: number) => {
    onNavigate({ blocker: view.blockers[index]?.id ?? "" });
  };

  const continueBlocker = () => {
    if (!blocker?.actionable) return;
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
              <h1>{view.title}</h1>
              <span className={`status status--${view.statusTone}`}>{view.statusLabel}</span>
            </div>
          </div>
          <span>{view.durationLabel}</span>
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
            {view.mediaEmpty}
          </div>
        )}

        <section className="timeline" aria-label="装配时间线">
          {view.shots.length ? (
            <>
              <div className="timeline__tracks">
                {view.shots.map((shot) => (
                  <button
                    key={shot.id}
                    type="button"
                    className={`timeline-shot timeline-shot--${shot.tone}`}
                    style={{ flexGrow: Math.max(shot.duration ?? 6, 6) }}
                    onClick={() => {
                      const index = view.blockers.findIndex(
                        (item) => item.entity === shot.id
                      );
                      if (index >= 0) chooseBlocker(index);
                    }}
                  >
                    <span>{shot.sequenceLabel}</span>
                    <strong>{shot.label}</strong>
                    <small>{shot.durationLabel} · {shot.status}</small>
                  </button>
                ))}
              </div>
              {view.timelineMarks.length ? (
                <div className="timeline__axis" aria-hidden="true">
                  {view.timelineMarks.map((mark) => <span key={mark}>{mark}</span>)}
                </div>
              ) : null}
              <div className="timeline__legend">
                <span><IconCircleCheck aria-hidden="true" size={16} />已完成</span>
                <span><IconAlertCircle aria-hidden="true" size={16} />待处理</span>
              </div>
            </>
          ) : (
            <p className="empty-inline">当前项目尚未形成交付时间线。</p>
          )}
        </section>

        <footer className="delivery-spec">
          <span>最终交付配置</span>
          <strong>{view.specLabel}</strong>
        </footer>
      </div>

      <aside className="delivery-check">
        <div className="section-heading">
          <div>
            <p className="eyebrow">交付检查</p>
            <h2>阻塞项（{view.blockerCount}）</h2>
          </div>
        </div>
        <ol className="blocker-list">
          {view.blockers.length ? view.blockers.map((item, index) => (
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
          )) : (
            <li>
              <p className="empty-inline">当前交付还没有阻塞明细。</p>
            </li>
          )}
        </ol>

        <section className="version-list">
          <p className="eyebrow">版本记录</p>
          {view.versions.length ? view.versions.map((item) => (
            <div key={item.version} className={item.current ? "version-row is-current" : "version-row"}>
              <span>
                <strong>{item.label}</strong>
                <small>{formatSeconds(item.duration)}</small>
              </span>
              <time>{item.time}</time>
              <IconPlayerPlayFilled aria-label="播放此版本" size={17} />
            </div>
          )) : (
            <p className="empty-inline">当前真实项目没有可播放交付版本。</p>
          )}
        </section>

        <button
          className="button button--primary button--large"
          type="button"
          onClick={continueBlocker}
          disabled={!blocker?.actionable}
          title={blocker?.actionable ? view.primaryActionLabel : "当前阻塞项没有可导航目标"}
        >
          {view.primaryActionLabel}
          <IconArrowRight aria-hidden="true" size={18} />
        </button>
        <button
          className="button button--quiet"
          type="button"
          disabled
          title="处理完全部阻塞项后才能创建交付版本"
        >
          创建交付版本
        </button>
        <small className="action-explanation">完成全部阻塞项后才可使用</small>
      </aside>
    </section>
  );
}

export function deliveryView(data: SurfaceProps["data"]) {
  if (data.source === "fixture") {
    const fixture = data.fixture;
    return {
      title: `当前合成版本 · 版本${toChineseNumber(fixture.delivery.deliveryVersion)}`,
      statusLabel: "尚未就绪",
      statusTone: "warning",
      playableDuration: fixture.delivery.playableDurationSeconds,
      targetDuration: fixture.project.targetDurationSeconds,
      durationLabel: `当前可播放 ${formatSeconds(fixture.delivery.playableDurationSeconds)} / 目标 ${formatSeconds(fixture.project.targetDurationSeconds)}`,
      mediaUrl: fixture.shots[2]?.imageUrl ?? "",
      mediaEmpty: "当前版本尚无可预览的交付媒体",
      shots: fixture.shots.map((shot) => ({
        id: shot.shotRef,
        sequence: shot.sequence,
        sequenceLabel: `镜头 ${String(shot.sequence).padStart(2, "0")}`,
        label: shot.displayName,
        duration: shot.durationSeconds,
        durationLabel: `${shot.durationSeconds} 秒`,
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
          candidate: "candidate-shot-03-video-v2",
          actionable: true
        },
        {
          id: "shot-05-task",
          label: "镜头 05 关键画面制作中",
          note: "9 秒 · 当前进度 46%",
          surface: "canvas" as const,
          entity: "shot-05",
          candidate: "",
          actionable: true
        },
        {
          id: "shot-07-missing",
          label: "镜头 07 视频尚未制作",
          note: "13 秒 · 等待发起制作",
          surface: "canvas" as const,
          entity: "shot-07",
          candidate: "",
          actionable: true
        }
      ],
      blockerCount: 3,
      primaryActionLabel: "继续处理阻塞项",
      versions: [
        { version: 3, label: "版本三", duration: 47, time: "今天 14:32", current: true },
        { version: 2, label: "版本二", duration: 47, time: "今天 11:08", current: false },
        { version: 1, label: "版本一", duration: 22, time: "昨天 18:40", current: false }
      ],
      timelineMarks: ["00:00", "00:22", "00:50", "01:17"],
      specLabel: "1920 × 1080 / 24 帧 / 立体声"
    };
  }

  const envelope = data.envelope;
  const summary = envelope.delivery_summary;
  const hasDelivery = summary.playable;
  const playableDuration = 0;
  const blockerCount = summary.blocker_count;
  const blockers = blockerCount > 0
    ? [
        {
          id: "delivery-blockers",
          label: `当前有 ${blockerCount} 个阻塞项`,
          note: "交付摘要尚未提供阻塞明细，可回到制作画布继续处理",
          surface: "canvas" as const,
          entity: "",
          candidate: "",
          duration: 0,
          actionable: true
        }
      ]
    : [];
  return {
    title: hasDelivery ? "交付版本可播放" : "尚未形成可播放交付",
    statusLabel: stateLabel(summary.state),
    statusTone: hasDelivery ? "success" : blockerCount > 0 ? "warning" : "muted",
    playableDuration,
    targetDuration: 0,
    durationLabel: `当前可播放 ${formatSeconds(playableDuration)} / 目标时长待项目补充`,
    mediaUrl: "",
    mediaEmpty: hasDelivery
      ? "当前交付摘要未提供受控媒体地址"
      : "当前真实项目没有已采用视频或交付记录，尚未形成可播放交付",
    shots: [],
    blockers,
    blockerCount,
    primaryActionLabel: "返回制作画布",
    versions: [],
    timelineMarks: [],
    specLabel: "交付规格尚未提供"
  };
}

function toChineseNumber(value: number) {
  return ["零", "一", "二", "三", "四", "五"][value] ?? String(value);
}
