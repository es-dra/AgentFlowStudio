import { useEffect, useRef, useState } from "react";
import {
  IconClock,
  IconCoinYuan,
  IconRestore,
  IconShieldCheck,
  IconTargetArrow,
  IconVideo,
  IconX
} from "@tabler/icons-react";

import type { StudioData } from "../api/studioAdapter";
import { MediaStage } from "../components/MediaStage";

interface ReworkPreviewProps {
  data: StudioData;
  imageUrl: string;
  onClose: () => void;
}

export function ReworkPreview({ data, imageUrl, onClose }: ReworkPreviewProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const [confirmed, setConfirmed] = useState(false);
  const cost = data.source === "fixture"
    ? data.fixture.tasks[0]?.estimatedCostCny ?? 0
    : data.envelope.cost_summary.available
      ? data.envelope.cost_summary.reserved
      : null;

  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="rework-layer" role="dialog" aria-modal="true" aria-labelledby="rework-title">
      <button className="rework-backdrop" type="button" aria-label="关闭局部返工预览" onClick={onClose} />
      <section className="rework-panel">
        <header>
          <div>
            <p className="eyebrow">局部返工预览</p>
            <h2 id="rework-title">镜头 03 · 灯塔远景</h2>
            <p>只处理 06–08 秒灯塔光束轻微跳变</p>
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
            <MediaStage
              imageUrl={imageUrl}
              title="当前版本"
              durationSeconds={8}
              rangeStart={6}
              rangeEnd={8}
            />
          </section>
          <section>
            <span>返工预览</span>
            <MediaStage
              imageUrl={imageUrl}
              title="返工预览"
              durationSeconds={8}
              rangeStart={6}
              rangeEnd={8}
            />
          </section>
        </div>

        <div className="rework-facts">
          <Fact icon={IconVideo} label="影响对象" value="仅镜头 03" />
          <Fact icon={IconShieldCheck} label="不会改变" value="剧本、分镜、资产设定；镜头 01–02 与 04–07" />
          <Fact icon={IconCoinYuan} label="预计新增费用" value={cost === null ? "费用信封尚未提供" : `约 ${cost.toFixed(1)} 元`} />
          <Fact icon={IconClock} label="预计耗时" value="约 4 分钟" />
          <Fact icon={IconTargetArrow} label="调整目标" value="稳定灯塔光束，保留海浪与镜头运动" />
          <Fact icon={IconRestore} label="失败后恢复" value="保留当前候选，可从检查点继续" />
        </div>

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
            disabled
            title="服务端尚未提供局部返工确认路由"
          >
            确认局部返工
          </button>
          <small>
            {confirmed
              ? "已完成本地确认；服务端确认入口尚未接入。"
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
