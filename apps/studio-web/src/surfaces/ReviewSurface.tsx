import { useMemo, useState } from "react";
import {
  IconArrowLeft,
  IconArrowsDiff,
  IconCircleCheck,
  IconClock,
  IconMovie,
  IconPhoto,
  IconZoomScan
} from "@tabler/icons-react";

import type { SurfaceProps } from "../App";
import {
  entityLabel,
  publicCopy,
  stateLabel,
  stateTone
} from "../api/studioAdapter";
import { MediaStage } from "../components/MediaStage";
import type { CanonicalShot } from "../data/canonicalFixture";
import { ReworkPreview } from "./ReworkPreview";

export default function ReviewSurface({
  data,
  urlState,
  onNavigate,
  onReload
}: SurfaceProps) {
  const view = useMemo(() => reviewView(data), [data]);
  const queueCandidateIds = view.queue.flatMap((group) =>
    group.items.map((item) => item.candidateId).filter(Boolean)
  );
  const candidateId = view.candidates.some((item) => item.id === urlState.candidate) ||
    queueCandidateIds.includes(urlState.candidate)
    ? urlState.candidate
    : view.candidates[0]?.id ?? queueCandidateIds[0] ?? "";
  const [reworkOpen, setReworkOpen] = useState(false);
  const candidate =
    view.candidates.find((item) => item.id === candidateId) ?? view.candidates[0];
  const queueTotal = view.queue.reduce((total, group) => total + group.items.length, 0);
  const canOpenRework = view.reworkAvailable;

  const focusCandidate = (id: string, entityId?: string) => {
    const nextCandidate = view.candidates.find((item) => item.id === id);
    onNavigate({ candidate: id, entity: entityId ?? nextCandidate?.entityId ?? id });
  };

  return (
    <section className="review surface">
      <aside className="review-queue" aria-label="审核队列">
        <div className="section-heading">
          <div>
            <p className="eyebrow">审核队列</p>
            <h2>需要你的决定</h2>
          </div>
        </div>
        {view.queue.map((group) => (
          <section key={group.label} className="queue-group">
            <header>
              <span>{group.label}</span>
              <strong>{group.items.length}</strong>
            </header>
            {group.items.map((item) => (
              <button
                key={item.id}
                className={item.candidateId === candidateId ? "queue-row is-active" : "queue-row"}
                type="button"
                onClick={() => {
                  if (item.candidateId) focusCandidate(item.candidateId, item.entityId);
                }}
              >
                {item.imageUrl ? <img src={item.imageUrl} alt="" /> : <IconMovie aria-hidden="true" />}
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.note}</small>
                </span>
                {item.tone === "success" ? (
                  <IconCircleCheck className="success-icon" aria-label="已采用" size={18} />
                ) : null}
              </button>
            ))}
          </section>
        ))}
        {queueTotal === 0 ? (
          <p className="empty-inline">当前服务端没有返回审核队列。</p>
        ) : null}
        <span className="queue-total">共 {queueTotal} 个待处理对象</span>
      </aside>

      <div className="review-workspace">
        <header className="object-header">
          <div>
            <p className="breadcrumb">{view.header.breadcrumb}</p>
            <div className="object-title">
              <h1>{candidate?.title ?? view.header.title}</h1>
              {candidate?.durationLabel ? <span>{candidate.durationLabel}</span> : null}
              <span className={`status status--${candidate?.tone ?? view.header.tone}`}>
                {candidate?.status ?? view.header.status}
              </span>
            </div>
          </div>
          <span>{candidate?.adoptionLabel ?? view.header.adoptionLabel}</span>
        </header>

        {candidate?.imageUrl ? (
          <MediaStage
            imageUrl={candidate.imageUrl}
            title={candidate.title}
            durationSeconds={candidate.duration}
            rangeStart={candidate.issueRange?.[0]}
            rangeEnd={candidate.issueRange?.[1]}
          />
        ) : (
          <div className="media-unavailable media-unavailable--large">
            <IconPhoto aria-hidden="true" size={28} />
            当前服务端尚未提供受控媒体地址
          </div>
        )}

        {view.candidates.length ? (
          <section className="candidate-strip" aria-label="候选版本">
            {view.candidates.map((item) => (
              <button
                key={item.id}
                type="button"
                className={candidateId === item.id ? "candidate-card is-focused" : "candidate-card"}
                aria-pressed={candidateId === item.id}
                onClick={() => focusCandidate(item.id)}
              >
                <span>{item.label}</span>
                {item.imageUrl ? <img src={item.imageUrl} alt="" /> : <IconMovie aria-hidden="true" />}
                <small>
                  {candidateId === item.id ? "当前查看" : item.note}
                </small>
              </button>
            ))}
          </section>
        ) : (
          <p className="empty-inline">当前真实投影没有候选版本，不补入未由服务端提供的候选。</p>
        )}

        <div className="review-detail-grid">
          <section>
            <p className="eyebrow">质量检查</p>
            {candidate?.qualityChecks.length ? (
              <ul className="quality-list">
                {candidate.qualityChecks.map((item) => (
                  <li key={item.label}>
                    {item.tone === "success" ? (
                      <IconCircleCheck aria-hidden="true" size={17} />
                    ) : (
                      <IconClock aria-hidden="true" size={17} />
                    )}
                    {item.label} <strong>{item.state}</strong>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-inline">服务端尚未提供结构化质量检查。</p>
            )}
          </section>
          <section>
            <p className="eyebrow">审核建议</p>
            <p>{candidate?.issue ?? "当前候选没有结构化质量建议。"}</p>
          </section>
        </div>

        <footer className="review-actions">
          <button
            className="button button--primary button--large"
            type="button"
            disabled
            title="服务端尚未提供候选采用确认路由"
          >
            确认采用
          </button>
          <span>当前仅可查看；不会写入采用结果</span>
          <button
            className="button button--quiet"
            type="button"
            disabled
            title="服务端尚未提供候选对比路由"
          >
            <IconArrowsDiff aria-hidden="true" size={18} />
            对比上一版
          </button>
          <button
            className="button button--quiet"
            type="button"
            disabled={!canOpenRework}
            title={view.reworkReason}
            onClick={() => setReworkOpen(true)}
          >
            <IconZoomScan aria-hidden="true" size={18} />
            {view.reworkActionLabel}
          </button>
          <button
            className="text-action"
            type="button"
            onClick={() => onNavigate({ surface: "overview" })}
          >
            <IconArrowLeft aria-hidden="true" size={17} />
            返回概览
          </button>
        </footer>
      </div>
      {reworkOpen ? (
        <ReworkPreview
          data={data}
          imageUrl={candidate?.imageUrl ?? ""}
          title={candidate?.title ?? view.header.title}
          durationSeconds={candidate?.duration ?? 1}
          range={candidate?.issueRange}
          onConfirmed={(receipt) => {
            onNavigate({
              surface: "review",
              entity: receipt.target_entity_id,
              candidate: "",
              expectedVersion: receipt.graph_version
            }, true);
            onReload();
          }}
          onClose={() => setReworkOpen(false)}
        />
      ) : null}
    </section>
  );
}

export function reviewView(data: SurfaceProps["data"]) {
  if (data.source === "fixture") {
    const fixture = data.fixture;
    const shotById = new Map(fixture.shots.map((shot) => [shot.shotRef, shot]));
    const reviewCandidates = fixture.candidates
      .filter((item) => item.entityRef === "shot-03")
      .map((item) => ({
        id: item.candidateRef,
        entityId: item.entityRef,
        label: item.sequence === 1 ? "上一版" : `版本${toChineseNumber(item.sequence)}`,
        note: item.reviewState === "pending" ? "待审核" : "已被后续版本替代",
        duration: item.durationSeconds ?? 8,
        durationLabel: `${item.durationSeconds ?? 8} 秒`,
        imageUrl: item.imageUrl,
        title: "灯塔远景",
        status: item.reviewState === "pending" ? "待审核" : "已替代",
        tone: item.reviewState === "pending" ? "warning" : "muted",
        adoptionLabel: item.reviewState === "pending" ? "尚未采用" : "不会覆盖当前查看",
        qualityChecks: item.qualityIssue
          ? [
              { label: "场景连续性", state: "通过", tone: "success" },
              { label: "运动稳定性", state: "需确认", tone: "warning" }
            ]
          : [],
        issueRange: item.qualityIssue
          ? [
              item.qualityIssue.rangeStartSeconds,
              item.qualityIssue.rangeEndSeconds
            ] as [number, number]
          : undefined,
        issue: item.qualityIssue
          ? `海浪运动自然；建议仅修复 ${item.qualityIssue.rangeStartSeconds}–${item.qualityIssue.rangeEndSeconds} 秒的灯塔光束，或直接采用当前版本。`
          : "上一版用于比较，不会覆盖当前查看。"
      }));
    return {
      header: {
        breadcrumb: "第二场 · 灯塔警示 / 镜头 03",
        title: "灯塔远景",
        status: "待审核",
        tone: "warning",
        adoptionLabel: "尚未采用"
      },
      candidates: reviewCandidates,
      queue: [
        {
          label: "需处理",
          items: [
            queueItem(shotById.get("shot-05"), "关键画面制作中", "", "warning")
          ]
        },
        {
          label: "待审核",
          items: [
            queueItem(
              shotById.get("shot-03"),
              "视频候选待决定",
              "candidate-shot-03-video-v2",
              "active",
              true
            ),
            {
              id: "asset-prop-letter",
              entityId: "asset-prop-letter",
              label: "油布包裹的信件",
              note: "图片候选待审核",
              candidateId: "",
              imageUrl: fixture.candidates[2]?.imageUrl ?? "",
              tone: "warning",
              active: false
            }
          ]
        },
        {
          label: "已采用",
          items: ["shot-01", "shot-04"].map((id) =>
            queueItem(shotById.get(id), "已采用视频", "", "success")
          )
        }
      ],
      reworkAvailable: true,
      reworkActionLabel: "预览局部返工",
      reworkReason: "预览局部返工"
    };
  }

  const envelope = data.envelope;
  const candidates = envelope.artifact_summaries.map((item) => ({
    id: item.artifact_id,
    entityId: item.artifact_id,
    label: `候选版本 ${item.version}`,
    note: item.selected ? "服务端标记为已采用" : stateLabel(item.state),
    duration: 0,
    durationLabel: "",
    imageUrl: "",
    title: `候选版本 ${item.version}`,
    status: stateLabel(item.state),
    tone: stateTone(item.state),
    adoptionLabel: item.selected ? "已采用" : "尚未采用",
    qualityChecks: [],
    issueRange: undefined,
    issue: ""
  }));
  const candidateByEntity = new Map(candidates.map((item) => [item.entityId, item.id]));
  const focused =
    envelope.focused_entity ??
    envelope.entities.find((item) => item.entity_id === envelope.resume_target.entity_id) ??
    null;
  return {
    header: {
      breadcrumb: publicCopy(envelope.surface_summary.headline, "生成审核"),
      title: focused?.label || "暂无待审核候选",
      status: envelope.review_queue.length ? "待审核" : "只读",
      tone: envelope.review_queue.length ? "warning" : "muted",
      adoptionLabel: envelope.review_queue.length ? "等待服务端决定" : "没有候选回执"
    },
    candidates,
    queue: [
      {
        label: "待审核",
        items: data.envelope.review_queue.map((item) => ({
          id: item.review_id,
          entityId: item.target_entity_id,
          label: entityLabel(envelope, item.target_entity_id, "服务端候选对象"),
          note: stateLabel(item.state),
          candidateId: candidateByEntity.get(item.target_entity_id) ?? item.target_entity_id,
          imageUrl: "",
          tone: "warning",
          active: false
        }))
      }
    ],
    reworkAvailable: envelope.rework_preview.available === true,
    reworkActionLabel: envelope.rework_preview.available
      ? "预览局部返工"
      : envelope.rework_preview.reason.includes("已有待执行")
        ? "已有待执行返工任务"
        : "等待局部返工预览",
    reworkReason:
      publicCopy(envelope.rework_preview.reason) ||
      "服务端尚未提供局部返工预览回执，不能展示影响、费用或耗时。"
  };
}

function queueItem(
  shot: CanonicalShot | undefined,
  note: string,
  candidateId: string,
  tone: string,
  active = false
) {
  return {
    id: shot?.shotRef ?? note,
    entityId: shot?.shotRef ?? "",
    label: shot
      ? `镜头 ${String(shot.sequence).padStart(2, "0")} · ${shot.displayName}`
      : note,
    note: shot ? `${shot.durationSeconds} 秒 · ${note}` : note,
    candidateId,
    imageUrl: shot?.imageUrl ?? "",
    tone,
    active
  };
}

function toChineseNumber(value: number) {
  return ["零", "一", "二", "三"][value] ?? String(value);
}
