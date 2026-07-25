import { icon } from "./icons.js";
import { el, showModal } from "./overlay.js";

export function requestProjectName(existingProjects = []) {
  return new Promise((resolve) => {
    const modal = el("div", "modal compact project-create-modal");
    const head = el("div", "modal-head");
    head.appendChild(el("strong", "", "新建视频项目"));
    const closeBtn = el("button", "modal-close");
    closeBtn.innerHTML = icon("x", 15);
    head.appendChild(el("span", "head-spacer"));
    head.appendChild(closeBtn);

    const body = el("div", "modal-body project-create-body");
    const field = el("label", "modal-field");
    field.appendChild(el("span", "", "项目名称"));
    const input = document.createElement("input");
    input.type = "text";
    input.value = uniqueProjectName("未命名项目", existingProjects);
    input.maxLength = 80;
    field.appendChild(input);
    const error = el("div", "modal-error");
    error.hidden = true;
    body.append(field, error);

    const actions = el("div", "modal-actions");
    const cancel = el("button", "ghost-btn", "取消");
    const confirm = el("button", "primary-btn", "创建并切换");
    actions.append(cancel, confirm);
    modal.append(head, body, actions);

    let settled = false;
    const close = showModal(modal, { onClose: () => { if (!settled) resolve(null); } });
    const finish = () => {
      if (settled) return;
      const name = input.value.trim();
      if (!name) {
        error.textContent = "请先填写项目名称。";
        error.hidden = false;
        input.focus();
        return;
      }
      if (isDuplicateProjectName(name, existingProjects)) {
        error.textContent = `项目名称“${name}”已存在，请换一个名称。`;
        error.hidden = false;
        input.focus();
        input.select();
        return;
      }
      settled = true;
      close();
      resolve(name);
    };

    confirm.addEventListener("click", finish);
    cancel.addEventListener("click", () => finishCancel());
    closeBtn.addEventListener("click", () => finishCancel());
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") finish();
      if (event.key === "Escape") finishCancel();
    });
    requestAnimationFrame(() => {
      input.focus();
      input.select();
    });

    function finishCancel() {
      if (settled) return;
      settled = true;
      close();
      resolve(null);
    }
  });
}

export function projectDisplayName(project) {
  return project?.studio_state_meta?.projectName || project?.goal || "未命名项目";
}

function isDuplicateProjectName(name, projects) {
  const normalized = normalizeProjectName(name);
  if (!normalized) return false;
  return (Array.isArray(projects) ? projects : [])
    .some((project) => normalizeProjectName(projectDisplayName(project)) === normalized);
}

function uniqueProjectName(baseName, projects) {
  const base = String(baseName || "未命名项目").trim() || "未命名项目";
  if (!isDuplicateProjectName(base, projects)) return base;
  for (let index = 2; index < 1000; index += 1) {
    const candidate = `${base} ${index}`;
    if (!isDuplicateProjectName(candidate, projects)) return candidate;
  }
  return `${base} ${Date.now()}`;
}

function normalizeProjectName(name) {
  return String(name || "").replace(/\s+/g, " ").trim().toLowerCase();
}
