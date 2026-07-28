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
import { MediaStage } from "../components/MediaStage";
import type { CanonicalShot } from "../data/canonicalFixture";
import { ReworkPreview } from "./ReworkPreview";

export default function ReviewSurface({
  data,
  urlState,
  onNavigate
}: SurfaceProps) {
  const view = useMemo(() => reviewView(data), [data]);
  const initialCandidate = view.candidates.some(
    (item) => item.id === urlState.candidate
  )
    ? urlState.candidate
    : view.candidates[0]?.id ?? "";
  const [candidateId, setCandidateId] = useState(initialCandidate);
  const [reworkOpen, setReworkOpen] = useState(false);
  const candidate =
    view.candidates.find((item) => item.id === candidateId) ?? view.candidates[0];

  const focusCandidate = (id: string) => {
    const nextCandidate = view.candidates.find((item) => item.id === id);
    setCandidateId(id);
    onNavigate({ candidate: id, entity: nextCandidate?.entityId ?? "" });
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
                className={item.active ? "queue-row is-active" : "queue-row"}
                type="button"
                onClick={() => {
                  if (item.candidateId) focusCandidate(item.candidateId);
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
        <span className="queue-total">共 7 个镜头</span>
      </aside>

      <div className="review-workspace">
        <header className="object-header">
          <div>
            <p className="breadcrumb">第二场 · 灯塔警示 / 镜头 03</p>
            <div className="object-title">
              <h1>灯塔远景</h1>
              <span>8 秒</span>
              <span className="status status--warning">待审核</span>
            </div>
          </div>
          <span>尚未采用</span>
        </header>

        {candidate?.imageUrl ? (
          <MediaStage
            imageUrl={candidate.imageUrl}
            title="镜头 03 灯塔远景"
            durationSeconds={candidate.duration}
            rangeStart={candidate.issueRange?.[0]}
            rangeEnd={candidate.issueRange?.[1]}
          />
        ) : (
          <div className="media-unavailable media-unavailable--large">
            <IconPhoto aria-hidden="true" size={28} />
            当前服务信封尚未提供受控媒体地址
          </div>
        )}

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

        <div className="review-detail-grid">
          <section>
            <p className="eyebrow">质量检查</p>
            <ul className="quality-list">
              <li><IconCircleCheck aria-hidden="true" size={17} />场景连续性 <strong>通过</strong></li>
              <li><IconClock aria-hidden="true" size={17} />运动稳定性 <strong>需确认</strong></li>
            </ul>
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
          <button className="button button--quiet" type="button">
            <IconArrowsDiff aria-hidden="true" size={18} />
            对比上一版
          </button>
          <button
            className="button button--quiet"
            type="button"
            onClick={() => setReworkOpen(true)}
          >
            <IconZoomScan aria-hidden="true" size={18} />
            预览局部返工
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
      {reworkOpen && candidate?.imageUrl ? (
        <ReworkPreview
          data={data}
          imageUrl={candidate.imageUrl}
          onClose={() => setReworkOpen(false)}
        />
      ) : null}
    </section>
  );
}

function reviewView(data: SurfaceProps["data"]) {
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
        imageUrl: item.imageUrl,
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
      ]
    };
  }

  const candidates = data.envelope.artifact_summaries.map((item) => ({
    id: item.artifact_id,
    entityId: item.artifact_id,
    label: `候选版本 ${item.version}`,
    note: item.selected ? "服务端标记为已采用" : item.state,
    duration: 0,
    imageUrl: "",
    issueRange: undefined,
    issue: ""
  }));
  return {
    candidates,
    queue: [
      {
        label: "待审核",
        items: data.envelope.review_queue.map((item) => ({
          id: item.review_id,
          label: item.target_entity_id,
          note: item.state,
          candidateId: item.target_entity_id,
          imageUrl: "",
          tone: "warning",
          active: false
        }))
      }
    ]
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
