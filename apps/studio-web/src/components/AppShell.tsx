import { useEffect, useState, type ReactNode } from "react";
import {
  IconArrowBackUp,
  IconChevronLeft,
  IconChevronRight,
  IconClipboardCheck,
  IconFolder,
  IconLibraryPhoto,
  IconPlayerPlayFilled,
  IconSettings,
  IconSparkles,
  IconUpload,
  IconUsers,
  IconUserCircle
} from "@tabler/icons-react";

import {
  liveNotice,
  projectCheckpoint,
  projectName,
  type StudioData
} from "../api/studioAdapter";
import {
  studioSurfaces,
  surfaceLabel,
  type AppSurface
} from "../api/studioTypes";
import type { StudioUrlState } from "../state/urlState";

interface AppShellProps {
  children: ReactNode;
  data: StudioData | null;
  surface: AppSurface;
  onNavigate: (patch: Partial<StudioUrlState>) => void;
}

const globalItems = [
  { label: "项目", icon: IconFolder, active: true },
  { label: "素材库", icon: IconLibraryPhoto, active: false },
  { label: "制作任务", icon: IconClipboardCheck, active: false },
  { label: "团队", icon: IconUsers, active: false },
  { label: "设置", icon: IconSettings, active: false }
];

export function AppShell({
  children,
  data,
  surface,
  onNavigate
}: AppShellProps) {
  const [agentOpen, setAgentOpen] = useState(false);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAgentOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  const name = data ? projectName(data) : "正在读取项目";
  const checkpoint = data ? projectCheckpoint(data) : "读取检查点";

  return (
    <div className={`app-shell ${agentOpen ? "agent-is-open" : ""}`}>
      <a className="skip-link" href="#surface-content">跳到当前工作面</a>
      <header className="global-bar">
        <strong className="brand-mark">AFS</strong>
        <span className="global-bar__project">项目：{name}</span>
        <span className="checkpoint">已保存至 {checkpoint}</span>
        {data ? (
          <span className="source-banner">
            <span>{liveNotice(data)}</span>
            {data.source === "fixture" ? (
              <span>仅用于界面检查，不会写入项目</span>
            ) : null}
          </span>
        ) : null}
        <span className="global-bar__spacer" />
        <button
          className="toolbar-button"
          type="button"
          disabled
          title="当前信封没有撤销入口"
        >
          <IconArrowBackUp aria-hidden="true" size={18} />
          撤销
        </button>
        <button
          className="toolbar-button"
          type="button"
          disabled
          title="当前信封没有恢复入口"
        >
          恢复
        </button>
        <button
          className="toolbar-button"
          type="button"
          onClick={() => onNavigate({ surface: "delivery" })}
        >
          <IconPlayerPlayFilled aria-hidden="true" size={17} />
          播放
        </button>
        <button
          className="toolbar-button"
          type="button"
          onClick={() => onNavigate({ surface: "delivery" })}
        >
          <IconUpload aria-hidden="true" size={18} />
          交付
        </button>
        <button className="icon-button account-button" type="button" aria-label="账户">
          <IconUserCircle aria-hidden="true" size={28} stroke={1.4} />
        </button>
      </header>

      <nav className="global-rail" aria-label="全局导航">
        {globalItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              className={item.active ? "global-rail__item is-active" : "global-rail__item"}
              type="button"
              aria-current={item.active ? "page" : undefined}
              aria-disabled={!item.active}
              title={item.active ? item.label : `${item.label}未包含在当前切片`}
            >
              <Icon aria-hidden="true" size={23} stroke={1.6} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <nav className="surface-nav" aria-label="项目工作面">
        <button
          className={surface === "overview" ? "surface-tab is-active" : "surface-tab"}
          type="button"
          aria-current={surface === "overview" ? "page" : undefined}
          onClick={() => onNavigate({ surface: "overview", candidate: "", blocker: "" })}
        >
          项目概览
        </button>
        <span className="surface-nav__divider" aria-hidden="true" />
        {studioSurfaces.map((item) => (
          <button
            key={item}
            className={surface === item ? "surface-tab is-active" : "surface-tab"}
            type="button"
            aria-current={surface === item ? "page" : undefined}
            onClick={() =>
              onNavigate({ surface: item, candidate: "", blocker: "", entity: "" })
            }
          >
            {surfaceLabel(item)}
          </button>
        ))}
      </nav>

      <main id="surface-content" className="surface-content" tabIndex={-1}>
        {children}
      </main>

      <aside className="agent-rail" aria-label="创作助手">
        <button
          className="agent-rail__toggle"
          type="button"
          aria-expanded={agentOpen}
          aria-label={agentOpen ? "收起创作助手" : "打开创作助手"}
          title={agentOpen ? "收起创作助手" : "打开创作助手"}
          onClick={() => setAgentOpen((value) => !value)}
        >
          {agentOpen ? (
            <IconChevronRight aria-hidden="true" size={20} />
          ) : (
            <IconChevronLeft aria-hidden="true" size={20} />
          )}
          <IconSparkles aria-hidden="true" size={20} />
        </button>
        {agentOpen ? <AgentContent surface={surface} data={data} /> : null}
      </aside>
      {agentOpen ? (
        <button
          className="agent-backdrop"
          type="button"
          aria-label="收起创作助手"
          onClick={() => setAgentOpen(false)}
        />
      ) : null}
    </div>
  );
}

function AgentContent({
  surface,
  data
}: {
  surface: AppSurface;
  data: StudioData | null;
}) {
  const content = agentCopy(surface);
  return (
    <div className="agent-panel">
      <div>
        <p className="eyebrow">创作助手</p>
        <h2>{surfaceLabel(surface)}</h2>
      </div>
      <section>
        <span>当前对象</span>
        <strong>{content.object}</strong>
      </section>
      <section>
        <span>为什么现在处理</span>
        <p>{content.reason}</p>
      </section>
      <section>
        <span>建议</span>
        <p>{content.suggestion}</p>
      </section>
      <section>
        <span>依据</span>
        <p>
          {data?.source === "live"
            ? `基于服务端版本 ${data.envelope.project_version}`
            : "基于界面样例版本 32，不会直接执行操作"}
        </p>
      </section>
    </div>
  );
}

function agentCopy(surface: AppSurface) {
  switch (surface) {
    case "overview":
      return {
        object: "项目 · 雾港来信",
        reason: "镜头 03 的候选决定会影响下一次合成。",
        suggestion: "先完成镜头 03 审核，再检查镜头 05 的制作任务。"
      };
    case "canvas":
      return {
        object: "第二场 · 灯塔警示",
        reason: "一个镜头待审核，一个镜头仍在制作。",
        suggestion: "查看镜头 03 与镜头 05 的下游影响。"
      };
    case "review":
      return {
        object: "镜头 03 · 候选版本二",
        reason: "结尾 06–08 秒的灯塔光束需要确认。",
        suggestion: "先比较上一版，再决定采用或预览局部返工。"
      };
    case "delivery":
      return {
        object: "合成版本三",
        reason: "当前有三个阻塞项，暂时不能创建交付版本。",
        suggestion: "先处理镜头 03，完成后再检查下一次合成。"
      };
    default:
      return {
        object: "当前工作面",
        reason: "服务端已保留项目上下文。",
        suggestion: "查看当前对象摘要，或返回制作画布继续。"
      };
  }
}
