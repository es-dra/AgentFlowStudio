function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function normalizeCommandHub(value) {
  const source = asObject(value);
  return {
    status: String(source.status || "not_started"),
    title: String(source.title || "Command hub"),
    summary: String(source.summary || ""),
    primary_command: normalizeCommand(source.primary_command),
    commands: asArray(source.commands).map(normalizeCommand),
    non_claims: asArray(source.non_claims).map(String),
  };
}

export function normalizeCommand(value) {
  const source = asObject(value);
  return {
    command_id: String(source.command_id || ""),
    label: String(source.label || "Continue"),
    backend_action: String(source.backend_action || ""),
    ui_action: String(source.ui_action || ""),
    view: String(source.view || "Create"),
    summary: String(source.summary || ""),
    enabled: source.enabled === true,
    blocked_reason: String(source.blocked_reason || ""),
    requires_input: asArray(source.requires_input).map(String),
  };
}
