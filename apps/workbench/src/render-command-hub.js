import { badge, el, sectionTitle } from "./dom.js";
import { displayList, displayStatus, displayText } from "./display-labels.js";
import { statusTone } from "./workbench-state.js";

export function renderCommandHub(commandHub) {
  const value = commandHub || { commands: [], non_claims: [] };
  const commands = Array.isArray(value.commands) ? value.commands : [];
  return el("section", { className: "command-hub" }, [
    sectionTitle("下一步操作", displayStatus(value.status)),
    renderPrimaryCommand(value.primary_command, value.summary),
    commands.length
      ? el("div", { className: "command-grid" }, commands.map(renderCommandCard))
      : el("p", { className: "muted", text: "当前没有可执行操作。" }),
    value.non_claims && value.non_claims.length ? el("div", { className: "chips" }, displayList(value.non_claims).map((item) => badge(item, "quiet"))) : null,
  ]);
}

function renderPrimaryCommand(command, summary) {
  const value = command || {};
  const tone = value.blocked_reason ? "blocked" : statusTone(value.enabled ? "running" : "ready_not_run");
  return el("article", { className: `primary-command ${tone}` }, [
    el("div", { className: "primary-command-copy" }, [
      badge(displayText(value.view, "创作画布"), tone),
      el("h3", { text: displayText(value.label, "继续") }),
      el("p", { text: displayText(summary || value.summary, "继续当前制作步骤。") }),
    ]),
    value.blocked_reason
      ? badge(displayText(value.blocked_reason), "blocked")
      : commandButton(value, "primary"),
  ]);
}

function renderCommandCard(command) {
  const tone = command.blocked_reason ? "blocked" : statusTone(command.enabled ? "running" : "ready_not_run");
  return el("article", { className: `command-card ${tone}` }, [
    el("div", { className: "command-card-head" }, [
      el("strong", { text: displayText(command.label, "继续") }),
      badge(displayText(command.view, "创作画布"), tone),
    ]),
    el("p", { className: "card-summary", text: displayText(command.summary, "继续这个阶段。") }),
    command.requires_input && command.requires_input.length
      ? el("div", { className: "command-inputs" }, displayList(command.requires_input).map((item) => badge(item, "quiet")))
      : null,
    command.blocked_reason ? badge(displayText(command.blocked_reason), "blocked") : commandButton(command, "ghost"),
  ]);
}

function commandButton(command, variant) {
  if (!command.enabled || !command.ui_action) {
    return el("button", { className: `btn ${variant} disabled`, text: "等待输入", attrs: { disabled: "disabled" } });
  }
  return el("button", {
    className: `btn ${variant}`,
    text: "执行",
    dataset: {
      action: command.ui_action,
      commandId: command.command_id || "",
    },
  });
}
