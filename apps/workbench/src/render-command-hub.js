import { badge, el, sectionTitle } from "./dom.js";
import { statusTone } from "./workbench-state.js";

export function renderCommandHub(commandHub) {
  const value = commandHub || { commands: [], non_claims: [] };
  const commands = Array.isArray(value.commands) ? value.commands : [];
  return el("section", { className: "command-hub" }, [
    sectionTitle("Command Hub", value.status || "not_started"),
    renderPrimaryCommand(value.primary_command, value.summary),
    commands.length
      ? el("div", { className: "command-grid" }, commands.map(renderCommandCard))
      : el("p", { className: "muted", text: "No command available." }),
    value.non_claims && value.non_claims.length ? el("div", { className: "chips" }, value.non_claims.map((item) => badge(item, "quiet"))) : null,
  ]);
}

function renderPrimaryCommand(command, summary) {
  const value = command || {};
  const tone = value.blocked_reason ? "blocked" : statusTone(value.enabled ? "running" : "ready_not_run");
  return el("article", { className: `primary-command ${tone}` }, [
    el("div", { className: "primary-command-copy" }, [
      badge(value.view || "Create", tone),
      el("h3", { text: value.label || "Continue" }),
      el("p", { text: summary || value.summary || "Continue the current production step." }),
    ]),
    value.blocked_reason
      ? badge(value.blocked_reason, "blocked")
      : commandButton(value, "primary"),
  ]);
}

function renderCommandCard(command) {
  const tone = command.blocked_reason ? "blocked" : statusTone(command.enabled ? "running" : "ready_not_run");
  return el("article", { className: `command-card ${tone}` }, [
    el("div", { className: "command-card-head" }, [
      el("strong", { text: command.label || "Continue" }),
      badge(command.view || "Create", tone),
    ]),
    el("p", { className: "card-summary", text: command.summary || "Continue this stage." }),
    command.requires_input && command.requires_input.length
      ? el("div", { className: "command-inputs" }, command.requires_input.map((item) => badge(item, "quiet")))
      : null,
    command.blocked_reason ? badge(command.blocked_reason, "blocked") : commandButton(command, "ghost"),
  ]);
}

function commandButton(command, variant) {
  if (!command.enabled || !command.ui_action) {
    return el("button", { className: `btn ${variant} disabled`, text: "Pending", attrs: { disabled: "disabled" } });
  }
  return el("button", {
    className: `btn ${variant}`,
    text: "Run",
    dataset: {
      action: command.ui_action,
      commandId: command.command_id || "",
    },
  });
}
