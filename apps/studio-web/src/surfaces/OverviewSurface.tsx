import {
  IconArrowRight,
  IconCircleCheck,
  IconClock,
  IconPlayerPlayFilled,
  IconProgress,
  IconShieldExclamation
} from "@tabler/icons-react";

import type { SurfaceProps } from "../App";
import { projectName, projectVersion } from "../api/studioAdapter";
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
            <span><IconProgress aria-hidden="true" size={16} />制作中</span>
            <span>目标总时长 {formatSeconds(view.targetDuration)}</span>
            <span>项目版本 {projectVersion(data)}</span>
          </div>
        </div>
        <div className="primary-action-block">
          <button
            className="button button--primary button--large"
            type="button"
            onClick={() =>
              onNavigate({
                surface: view.primarySurface,
                candidate: view.primaryCandidate
              })
            }
          >
            继续审核镜头 03
            <IconArrowRight aria-hidden="true" size={19} />
          </button>
          <span>前往当前最重要的待决策</span>
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
              <h2>镜头 03 · 灯塔远景</h2>
            </div>
            <span className="status status--warning">待审核</span>
          </div>
          <p>候选版本二存在 06–08 秒灯塔光束轻微跳变，需要决定采用或预览局部返工。</p>
          <button
            className="text-action"
            type="button"
            onClick={() =>
              onNavigate({
                surface: "review",
                candidate: view.primaryCandidate
              })
            }
          >
            查看候选与影响
            <IconArrowRight aria-hidden="true" size={17} />
          </button>
        </section>

        <section className="panel current-cut">
          <div className="section-heading">
            <div>
              <p className="eyebrow">当前成片</p>
              <h2>合成版本三</h2>
            </div>
            <span>{formatSeconds(view.playableDuration)} 可播放</span>
          </div>
          {view.mediaUrl ? (
            <button
              className="current-cut__media"
              type="button"
              onClick={() => onNavigate({ surface: "delivery" })}
            >
              <img src={view.mediaUrl} alt="当前合成版本预览" />
              <span>
                <IconPlayerPlayFilled aria-hidden="true" size={18} />
                播放当前版本
              </span>
            </button>
          ) : (
            <div className="media-unavailable">
              当前服务信封尚未提供受控媒体地址
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
            {view.nextWork.map((item, index) => (
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
            ))}
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
              当前服务信封尚未提供最近变化摘要。
            </p>
          )}
        </section>
      </div>
    </section>
  );
}

function overviewView(data: SurfaceProps["data"]) {
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
      targetDuration: fixture.project.targetDurationSeconds,
      playableDuration: fixture.delivery.playableDurationSeconds,
      primarySurface: fixture.project.resumeTarget.surface,
      primaryCandidate: fixture.project.resumeTarget.entityRef,
      mediaUrl: fixture.shots[2]?.imageUrl ?? "",
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
  const pending = envelope.review_queue.filter((item) => item.state === "pending").length;
  return {
    episode: envelope.project.project_type || "当前项目",
    targetDuration: 0,
    playableDuration: 0,
    primarySurface: pending ? "review" : "canvas",
    primaryCandidate: envelope.review_queue[0]?.target_entity_id ?? "",
    mediaUrl: "",
    coverage: [
      { label: "工作面对象", value: String(envelope.entities.length), note: "来自当前服务投影" },
      { label: "待审核", value: String(pending), note: "不在前端推断采用数量" },
      { label: "制作任务", value: String(envelope.task_summaries.length), note: "服务端任务摘要" },
      {
        label: "恢复状态",
        value: envelope.recovery_summary.attention_required ? "需要核对" : "只读安全",
        note: envelope.recovery_summary.message
      }
    ],
    nextWork: envelope.review_queue.slice(0, 3).map((item) => ({
      label: item.target_entity_id,
      note: item.state,
      tone: "warning"
    })),
    changes: []
  } as const;
}
