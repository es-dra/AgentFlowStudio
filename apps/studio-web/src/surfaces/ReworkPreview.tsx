import { useEffect, useRef, useState } from "react";
import {
  IconClock,
  IconCoinYuan,
  IconAlertTriangle,
  IconRestore,
  IconShieldCheck,
  IconTargetArrow,
  IconVideo,
  IconX
} from "@tabler/icons-react";

import type { StudioData } from "../api/studioAdapter";
import { entityLabel, publicCopy } from "../api/studioAdapter";
import {
  confirmLocalRework,
  isStudioRequestError,
  previewLocalRework
} from "../api/studioClient";
import type {
  StudioReworkConfirmReceipt,
  StudioReworkPreviewReceipt
} from "../api/studioTypes";
import { MediaStage } from "../components/MediaStage";

interface ReworkPreviewProps {
  data: StudioData;
  imageUrl: string;
  title: string;
  durationSeconds: number;
  range?: [number, number];
  onConfirmed: (receipt: StudioReworkConfirmReceipt) => void;
  onClose: () => void;
}

export function ReworkPreview({
  data,
  imageUrl,
  title,
  durationSeconds,
  range,
  onConfirmed,
  onClose
}: ReworkPreviewProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [preview, setPreview] = useState<StudioReworkPreviewReceipt | null>(null);
  const [receipt, setReceipt] = useState<StudioReworkConfirmReceipt | null>(null);
  const [commandState, setCommandState] = useState<"idle" | "loading" | "ready" | "confirming" | "confirmed" | "error" | "stale">(
    data.source === "fixture" ? "idle" : "loading"
  );
  const [message, setMessage] = useState("");
  const view = reworkPreviewModel(data, {
    imageUrl,
    title,
    durationSeconds,
    range,
    preview
  });

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    previousFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
        ) ?? []
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      previousFocusRef.current?.focus();
    };
  }, []);

  useEffect(() => {
    if (data.source === "fixture") return;
    if (receipt) return;
    const targetEntityId = data.envelope.rework_preview.target_entity_id;
    if (!data.envelope.rework_preview.available || !targetEntityId) {
      setCommandState("error");
      setMessage(publicCopy(data.envelope.rework_preview.reason));
      return;
    }
    const controller = new AbortController();
    setCommandState("loading");
    setPreview(null);
    setReceipt(null);
    setMessage("正在生成绑定当前版本的影响预览…");
    previewLocalRework({
      projectId: data.envelope.project_id,
      targetEntityId,
      expectedGraphVersion: data.envelope.project_version,
      expectedGraphDigest: data.envelope.graph_digest,
      signal: controller.signal
    })
      .then((nextPreview) => {
        setPreview(nextPreview);
        setCommandState("ready");
        setMessage("影响范围已确认；当前尚未开始远端制作。");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (isStudioRequestError(error)) {
          setCommandState(error.kind === "stale" ? "stale" : "error");
          setMessage(error.message);
          return;
        }
        setCommandState("error");
        setMessage(error instanceof Error ? error.message : "局部返工预览失败。");
      });
    return () => controller.abort();
  }, [data, receipt]);

  const confirmEnabled =
    data.source === "live" &&
    commandState === "ready" &&
    confirmed &&
    preview !== null;

  const confirmRework = () => {
    if (data.source !== "live" || !preview || !confirmEnabled) return;
    setCommandState("confirming");
    setMessage("正在确认本地返工计划，不会派发远端制作…");
    confirmLocalRework({
      projectId: data.envelope.project_id,
      targetEntityId: preview.target_entity_id,
      expectedGraphVersion: preview.graph_version,
      expectedGraphDigest: preview.graph_digest,
      previewId: preview.preview_id,
      idempotencyKey: `studio-rework-${preview.preview_id}`,
    })
      .then((nextReceipt) => {
        setReceipt(nextReceipt);
        setCommandState("confirmed");
        setMessage("返工计划已保存；尚未开始远端制作。");
        onConfirmed(nextReceipt);
      })
      .catch((error: unknown) => {
        if (isStudioRequestError(error)) {
          setCommandState(error.kind === "stale" ? "stale" : "error");
          setMessage(error.message);
          return;
        }
        setCommandState("error");
        setMessage(error instanceof Error ? error.message : "局部返工确认失败。");
      });
  };

  return (
    <div className="rework-layer">
      <button
        className="rework-backdrop"
        type="button"
        tabIndex={-1}
        aria-label="关闭局部返工预览"
        onClick={onClose}
      />
      <section
        ref={dialogRef}
        className="rework-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rework-title"
        aria-describedby="rework-summary"
      >
        <header>
          <div>
            <p className="eyebrow">局部返工预览</p>
            <h2 id="rework-title">{view.title}</h2>
            <p id="rework-summary">{view.summary}</p>
          </div>
          <button
            ref={closeRef}
            className="icon-button"
            type="button"
            aria-label="关闭局部返工预览"
            onClick={onClose}
          >
            <IconX aria-hidden="true" size={20} />
          </button>
        </header>

        <div className="rework-compare">
          <section>
            <span>当前版本</span>
            {view.currentImageUrl ? (
              <MediaStage
                imageUrl={view.currentImageUrl}
                title="当前版本"
                durationSeconds={view.durationSeconds}
                rangeStart={view.range?.[0]}
                rangeEnd={view.range?.[1]}
              />
            ) : (
              <div className="media-unavailable media-unavailable--large">
                当前候选尚无可预览媒体
              </div>
            )}
          </section>
          <section>
            <span>返工预览</span>
            {view.previewImageUrl ? (
              <MediaStage
                imageUrl={view.previewImageUrl}
                title="返工预览"
                durationSeconds={view.durationSeconds}
                rangeStart={view.range?.[0]}
                rangeEnd={view.range?.[1]}
              />
            ) : (
              <div className="media-unavailable media-unavailable--large">
                返工计划尚无可预览媒体
              </div>
            )}
          </section>
        </div>

        {commandState === "loading" || commandState === "confirming" || commandState === "error" || commandState === "stale" ? (
          <div className={`rework-command-state rework-command-state--${commandState}`} role="status">
            {commandState === "stale" || commandState === "error" ? (
              <IconAlertTriangle aria-hidden="true" size={18} />
            ) : null}
            <span>{message}</span>
          </div>
        ) : null}

        <div className="rework-facts">
          <Fact icon={IconVideo} label="影响对象" value={view.impact} />
          <Fact icon={IconShieldCheck} label="不会改变" value={view.keep} />
          <Fact icon={IconCoinYuan} label="费用状态" value={view.cost} />
          <Fact icon={IconClock} label="预计耗时" value={view.estimatedTime} />
          <Fact icon={IconTargetArrow} label="调整目标" value={view.goal} />
          <Fact icon={IconRestore} label="失败后恢复" value={view.recovery} />
        </div>

        {receipt ? (
          <div className="rework-receipt" role="status">
            <span>计划状态</span>
            <strong>返工计划已保存</strong>
            <small>当前仅创建计划，尚未开始远端制作。</small>
          </div>
        ) : null}

        <footer>
          <label className="confirm-check">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            我已检查影响范围与预计费用
          </label>
          <button
            className="button button--primary button--large"
            type="button"
            disabled={!confirmEnabled}
            title={confirmEnabled ? "确认创建本地返工计划" : "需先获得预览回执并勾选确认"}
            onClick={confirmRework}
          >
            确认局部返工
          </button>
          <small>
            {receipt
              ? "确认完成；任务仅为计划状态，未派发远端制作。"
              : confirmed
                ? "已完成本地检查；确认后只创建计划任务。"
                : "先检查范围。当前界面不会派发制作任务。"}
          </small>
          <button className="button button--quiet" type="button" onClick={onClose}>
            返回审核
          </button>
        </footer>
      </section>
    </div>
  );
}

export function reworkPreviewModel(
  data: StudioData,
  candidate: {
    imageUrl: string;
    title: string;
    durationSeconds: number;
    range?: [number, number];
    preview?: StudioReworkPreviewReceipt | null;
  }
) {
  if (data.source === "fixture") {
    const cost = data.fixture.tasks[0]?.estimatedCostCny ?? 0;
    return {
      title: "镜头 03 · 灯塔远景",
      summary: "只处理 06–08 秒灯塔光束轻微跳变",
      currentImageUrl: candidate.imageUrl,
      previewImageUrl: candidate.imageUrl,
      durationSeconds: candidate.durationSeconds,
      range: candidate.range,
      impact: "仅镜头 03",
      keep: "剧本、分镜、资产设定；镜头 01–02 与 04–07",
      cost: `约 ${cost.toFixed(1)} 元`,
      estimatedTime: "约 4 分钟",
      goal: "稳定灯塔光束，保留海浪与镜头运动",
      recovery: "保留当前候选，可从检查点继续"
    };
  }

  const envelope = data.envelope;
  const availability = envelope.rework_preview;
  const receipt = candidate.preview;
  const targetId = receipt?.target_entity_id || availability.target_entity_id || candidate.title;
  const cost = receipt?.cost_available || availability.cost_available
    ? "费用信息尚未完整提供"
    : "费用待确认";

  return {
    title: entityLabel(envelope, targetId, candidate.title),
    summary: receipt
      ? `影响范围已绑定项目版本 ${receipt.graph_version}；尚未开始远端制作。`
      : publicCopy(availability.reason) || "当前项目尚未提供局部返工说明。",
    currentImageUrl: candidate.imageUrl,
    previewImageUrl: "",
    durationSeconds: Math.max(candidate.durationSeconds, 1),
    range: undefined,
    impact: receipt
      ? labelsForRefs(envelope, receipt.impact_refs, "影响对象待补充")
      : "完成影响计算后展示",
    keep: receipt
      ? labelsForRefs(envelope, receipt.keep_refs, "保留对象待补充")
      : "完成影响计算后展示",
    cost,
    estimatedTime: "预计耗时暂不可用",
    goal: "调整目标待补充",
    recovery: "发生问题时保留当前候选"
  };
}

function labelsForRefs(
  envelope: Extract<StudioData, { source: "live" }>["envelope"],
  refs: string[],
  fallback: string
): string {
  if (!refs.length) return fallback;
  return refs
    .map((ref) => entityLabel(envelope, ref, "当前对象"))
    .join("；");
}

function Fact({
  icon: Icon,
  label,
  value
}: {
  icon: typeof IconVideo;
  label: string;
  value: string;
}) {
  return (
    <div>
      <Icon aria-hidden="true" size={22} stroke={1.5} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
