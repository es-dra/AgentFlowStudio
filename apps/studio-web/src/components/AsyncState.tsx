import type { ReactNode } from "react";
import {
  IconAlertTriangle,
  IconCloudOff,
  IconFolderOff,
  IconLock,
  IconRefresh
} from "@tabler/icons-react";

import type { ScreenState } from "../api/studioTypes";

interface AsyncStateProps {
  status: ScreenState;
  message: string;
  onRetry: () => void;
  onReturn: () => void;
  children: ReactNode;
}

export function AsyncState({
  status,
  message,
  onRetry,
  onReturn,
  children
}: AsyncStateProps) {
  if (status === "ready") return children;
  if (status === "loading") {
    return (
      <section className="loading-state" aria-live="polite" aria-busy="true">
        <div className="loading-line loading-line--short" />
        <div className="loading-panel" />
        <div className="loading-grid">
          <div />
          <div />
          <div />
        </div>
        <span className="sr-only">{message}</span>
      </section>
    );
  }

  const content = stateContent(status);
  const Icon = content.icon;
  return (
    <section className="surface-state" aria-live="assertive">
      <Icon aria-hidden="true" size={30} stroke={1.6} />
      <p className="eyebrow">{content.eyebrow}</p>
      <h1>{content.title}</h1>
      <p>{message}</p>
      <div className="button-row">
        {status === "empty" || status === "forbidden" ? (
          <button className="button button--primary" type="button" onClick={onReturn}>
            返回项目概览
          </button>
        ) : (
          <button className="button button--primary" type="button" onClick={onRetry}>
            <IconRefresh aria-hidden="true" size={18} />
            重新读取
          </button>
        )}
      </div>
    </section>
  );
}

function stateContent(status: ScreenState) {
  switch (status) {
    case "empty":
      return { icon: IconFolderOff, eyebrow: "暂无内容", title: "这个工作面还是空的" };
    case "forbidden":
      return { icon: IconLock, eyebrow: "没有权限", title: "无法查看当前项目" };
    case "stale":
      return {
        icon: IconAlertTriangle,
        eyebrow: "内容已更新",
        title: "先重新检查，再继续处理"
      };
    default:
      return {
        icon: IconCloudOff,
        eyebrow: "连接中断",
        title: "项目内容没有被覆盖"
      };
  }
}
