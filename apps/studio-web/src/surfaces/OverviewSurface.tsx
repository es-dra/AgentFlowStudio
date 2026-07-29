import {
  IconArrowRight,
  IconCircleCheck,
  IconClock,
  IconPlayerPlayFilled,
  IconProgress,
  IconShieldExclamation
} from "@tabler/icons-react";

import type { SurfaceProps } from "../App";
import {
  entityLabel,
  firstAvailableSurface,
  numberFrom,
  publicCopy,
  projectTypeLabel,
  projectName,
  projectVersion,
  stateLabel
} from "../api/studioAdapter";
import type { AppSurface } from "../api/studioTypes";
import { formatSeconds } from "../components/MediaStage";

export default function OverviewSurface({
  data,
  onNavigate
}: SurfaceProps) {
  const view = overviewView(data);

  return (
    <section className="overview surface">
      <header className="surface-heading overview__heading">
        <div>
          <p className="eyebrow">项目概览</p>
          <h1>{projectName(data)}</h1>
          <p>{view.episode}</p>
          <div className="inline-facts">
            <span><IconProgress aria-hidden="true" size={16} />{view.projectStatus}</span>
            <span>{view.targetDuration === null ? "目标总时长待项目补充" : `目标总时长 ${formatSeconds(view.targetDuration)}`}</span>
            <span>项目版本 {projectVersion(data)}</span>
          </div>
        </div>
        <div className="primary-action-block">
          <button
            className="button button--primary button--large"
            type="button"
            disabled={!view.primaryAction.enabled}
            title={view.primaryAction.enabled ? view.primaryAction.help : "当前没有可执行的下一步"}
            onClick={() =>
              onNavigate({
                surface: view.primaryAction.surface,
                candidate: view.primaryAction.candidate,
                entity: view.primaryAction.entity
              })
            }
          >
            {view.primaryAction.label}
            <IconArrowRight aria-hidden="true" size={19} />
          </button>
          <span>{view.primaryAction.help}</span>
        </div>
      </header>

      <section className="overview-summary" aria-label="项目状态摘要">
        {view.coverage.map((item) => (
          <div key={item.label} className="summary-cell">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small>{item.note}</small>
          </div>
        ))}
      </section>

      <div className="overview-grid">
        <section className="panel decision-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">当前待决策</p>
              <h2>{view.decision.title}</h2>
            </div>
            <span className={`status status--${view.decision.tone}`}>{view.decision.status}</span>
          </div>
          <p>{view.decision.description}</p>
          <button
            className="text-action"
            type="button"
            disabled={!view.decision.enabled}
            title={view.decision.enabled ? view.decision.actionLabel : view.decision.disabledTitle}
            onClick={() =>
              onNavigate({
                surface: view.decision.surface,
                candidate: view.decision.candidate,
                entity: view.decision.entity
              })
            }
          >
            {view.decision.actionLabel}
            <IconArrowRight aria-hidden="true" size={17} />
          </button>
        </section>

        <section className="panel current-cut">
          <div className="section-heading">
            <div>
              <p className="eyebrow">当前成片</p>
              <h2>{view.delivery.title}</h2>
            </div>
            <span>{formatSeconds(view.delivery.playableDuration)} 可播放</span>
          </div>
          {view.delivery.mediaUrl ? (
            <button
              className="current-cut__media"
              type="button"
              onClick={() => onNavigate({ surface: "delivery" })}
            >
              <img src={view.delivery.mediaUrl} alt={view.delivery.mediaAlt} />
              <span>
                <IconPlayerPlayFilled aria-hidden="true" size={18} />
                {view.delivery.actionLabel}
              </span>
            </button>
          ) : (
            <div className="media-unavailable">
              {view.delivery.emptyText}
            </div>
          )}
        </section>

        <section className="panel next-work">
          <div className="section-heading">
            <div>
              <p className="eyebrow">接下来处理</p>
              <h2>按阻塞顺序继续</h2>
            </div>
          </div>
          <ol className="work-list">
            {view.nextWork.length ? view.nextWork.map((item, index) => (
              <li key={item.label}>
                <span className={`work-list__number work-list__number--${item.tone}`}>
                  {index + 1}
                </span>
                <div>
                  <strong>{item.label}</strong>
                  <small>{item.note}</small>
                </div>
                {"progress" in item && item.progress ? (
                  <strong>{item.progress}</strong>
                ) : null}
              </li>
            )) : (
              <li>
                <span className="work-list__number work-list__number--muted">0</span>
                <div>
                  <strong>没有待处理队列</strong>
                  <small>当前项目没有待审核候选或下一步工作。</small>
                </div>
              </li>
            )}
          </ol>
        </section>

        <section className="panel recent-changes">
          <div className="section-heading">
            <div>
              <p className="eyebrow">最近变化</p>
              <h2>可追溯的项目决定</h2>
            </div>
          </div>
          {view.changes.length ? (
            <ul className="change-list">
              {view.changes.map((item) => (
                <li key={`${item.label}-${item.time}`}>
                  {item.tone === "done" ? (
                    <IconCircleCheck aria-hidden="true" size={19} />
                  ) : item.tone === "risk" ? (
                    <IconShieldExclamation aria-hidden="true" size={19} />
                  ) : (
                    <IconClock aria-hidden="true" size={19} />
                  )}
                  <span>{item.label}</span>
                  <time>{item.time}</time>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-inline">
              当前项目尚未形成最近变化摘要。
            </p>
          )}
        </section>
      </div>
    </section>
  );
}

export function overviewView(data: SurfaceProps["data"]) {
  if (data.source === "fixture") {
    const fixture = data.fixture;
    const adoptedAssets = fixture.assets.filter(
      (item) => item.mediaStatus === "adopted"
    ).length;
    const adoptedVideos = fixture.shots.filter(
      (item) => item.videoStatus === "adopted"
    ).length;
    return {
      episode: fixture.project.episodeName,
      projectStatus: "制作中",
      targetDuration: fixture.project.targetDurationSeconds,
      primaryAction: {
        label: "继续审核镜头 03",
        surface: fixture.project.resumeTarget.surface as AppSurface,
        candidate: fixture.project.resumeTarget.entityRef,
        entity: "shot-03",
        enabled: true,
        help: "前往当前最重要的待决策"
      },
      decision: {
        title: "镜头 03 · 灯塔远景",
        status: "待审核",
        tone: "warning",
        description: "候选版本二存在 06–08 秒灯塔光束轻微跳变，需要决定采用或预览局部返工。",
        actionLabel: "查看候选与影响",
        disabledTitle: "当前没有待审核候选回执",
        enabled: true,
        surface: "review" as AppSurface,
        candidate: fixture.project.resumeTarget.entityRef,
        entity: "shot-03"
      },
      delivery: {
        title: "合成版本三",
        playableDuration: fixture.delivery.playableDurationSeconds,
        mediaUrl: fixture.shots[2]?.imageUrl ?? "",
        mediaAlt: "当前合成版本预览",
        actionLabel: "播放当前版本",
        emptyText: "当前项目尚无可预览媒体"
      },
      coverage: [
        { label: "资产覆盖", value: `${adoptedAssets}/${fixture.assets.length}`, note: "1 项待审核" },
        { label: "关键画面", value: "6/7", note: "镜头 05 制作中" },
        { label: "视频采用", value: `${adoptedVideos}/7`, note: "镜头 03 待决策" },
        { label: "交付状态", value: `${fixture.delivery.blockers.length} 项受阻`, note: "当前可播放 47 秒" }
      ],
      nextWork: [
        { label: "镜头 03 候选待审核", note: "预计 1 分钟", tone: "warning" },
        { label: "镜头 05 关键画面制作中", note: "可以离开页面", progress: "46%", tone: "active" },
        { label: "镜头 07 视频尚未开始", note: "等待前序决定", tone: "muted" }
      ],
      changes: [
        { label: "镜头 04 已采用视频版本一", time: "今天 14:10", tone: "done" },
        { label: "阿岚角色设定已确认", time: "今天 13:48", tone: "done" }
      ]
    } as const;
  }

  const envelope = data.envelope;
  const summary = envelope.surface_summary;
  const pending = envelope.review_queue.filter((item) => item.state === "pending").length;
  const pendingItem =
    envelope.review_queue.find((item) => item.state === "pending") ??
    envelope.review_queue[0];
  const primaryCandidate =
    envelope.resume_target.surface === "review"
      ? envelope.resume_target.entity_id
      : pendingItem?.target_entity_id ?? "";
  const primaryEntity = envelope.resume_target.entity_id || pendingItem?.target_entity_id || "";
  const primarySurface = firstAvailableSurface(
    envelope.resume_target.surface,
    pendingItem ? "review" : "canvas"
  );
  const primaryLabel = pendingItem
    ? `继续审核${entityLabel(envelope, pendingItem.target_entity_id, "候选对象")}`
    : "查看制作画布";
  const delivery = envelope.delivery_summary;
  const hasDelivery = delivery.playable;
  const playableDuration = 0;
  const targetDuration =
    numberFrom(envelope.entities.find((item) => item.metadata.target_duration_seconds)?.metadata.target_duration_seconds);
  return {
    episode: projectTypeLabel(envelope.project.project_type),
    projectStatus: stateLabel(envelope.project.status),
    targetDuration,
    primaryAction: {
      label: primaryLabel,
      surface: primarySurface,
      candidate: primaryCandidate,
      entity: primaryEntity,
      enabled: envelope.resume_target.available,
      help: envelope.resume_target.reason || (pendingItem ? "前往审核队列中的候选" : "当前没有审核候选，先查看制作画布")
    },
    decision: pendingItem
      ? {
          title: entityLabel(envelope, pendingItem.target_entity_id, "当前候选"),
          status: pendingItem.state,
          tone: "warning",
          description: pendingItem.evidence_refs.length
            ? "候选已有可追溯证据；前往审核工作面查看。"
            : "当前候选尚无结构化质量说明；只能查看候选身份，不能采用或返工。",
          actionLabel: "查看候选与影响",
          disabledTitle: "当前没有待审核候选回执",
          enabled: true,
          surface: "review" as AppSurface,
          candidate: pendingItem.target_entity_id,
          entity: pendingItem.target_entity_id
        }
      : {
          title: "当前没有待审核候选",
          status: "只读",
          tone: "muted",
          description: "当前没有审核队列。页面不会编造镜头、秒数或候选说明。",
          actionLabel: "等待审核回执",
          disabledTitle: "当前没有待审核候选回执",
          enabled: false,
          surface: "review" as AppSurface,
          candidate: "",
          entity: ""
        },
    delivery: {
      title: hasDelivery && delivery.delivery_version_id
          ? "当前交付版本"
        : "尚未形成可播放交付",
      playableDuration,
      mediaUrl: "",
      mediaAlt: "当前交付媒体预览",
      actionLabel: "播放当前版本",
      emptyText: hasDelivery
        ? "当前交付还没有可预览媒体地址"
        : "当前真实项目没有已采用视频或交付记录，尚未形成可播放交付"
    },
    coverage: [
      { label: "工作面对象", value: String(summary.entity_count), note: publicCopy(summary.headline) },
      { label: "待审核", value: String(pending), note: "不在前端推断采用数量" },
      { label: "制作任务", value: String(envelope.task_summaries.length), note: "当前任务摘要" },
      {
        label: "交付状态",
        value: stateLabel(delivery.state),
        note: delivery.playable ? "当前版本可播放" : "当前没有可播放交付"
      }
    ],
    nextWork: envelope.review_queue.length
      ? envelope.review_queue.slice(0, 3).map((item) => ({
          label: entityLabel(envelope, item.target_entity_id, "当前候选"),
          note: item.state,
          tone: "warning"
        }))
      : envelope.resume_target.available
        ? [{
            label: entityLabel(envelope, envelope.resume_target.entity_id, "继续当前位置"),
            note: envelope.resume_target.reason,
            tone: summary.state === "attention" || summary.state === "blocked" ? "warning" : "muted"
          }]
        : [],
    changes: []
  } as const;
}
