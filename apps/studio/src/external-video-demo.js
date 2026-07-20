import { icon } from "./icons.js";
import { el, showModal } from "./overlay.js";

export function openExternalVideoDemoPanel({ runtime, formatError }) {
  const modal = el("div", "modal external-video-modal");
  const head = el("div", "modal-head");
  head.appendChild(el("strong", "", "AI 漫剧任务"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(el("span", "head-spacer"));
  head.appendChild(closeBtn);

  const body = el("div", "modal-body external-video-body");
  const form = el("form", "external-video-form");
  const result = el("section", "external-video-result");
  body.append(form, result);
  modal.append(head, body);

  const fields = {
    title: textInput("标题", "", "输入本次漫剧任务名称"),
    engine: selectInput("引擎", [
      ["replay", "Replay"],
      ["libtv", "外部引擎"],
    ]),
    style: textInput("风格", "animated_comic", "例如 animated_comic"),
    aspectRatio: selectInput("比例", [
      ["9:16", "9:16"],
      ["16:9", "16:9"],
      ["1:1", "1:1"],
    ]),
    duration: numberInput("时长", "6", { min: "1", max: "180" }),
    scenes: numberInput("镜头", "3", { min: "1", max: "12" }),
    prompt: textareaInput("创作意图", "", "输入人物、冲突、场景、镜头节奏和结尾要求"),
  };
  form.append(
    fieldShell(fields.title),
    fieldShell(fields.engine),
    compactFieldRow([fields.style, fields.aspectRatio]),
    compactFieldRow([fields.duration, fields.scenes]),
    fieldShell(fields.prompt),
  );

  const actions = el("div", "external-video-actions");
  const submit = el("button", "primary-btn", "生成");
  submit.type = "submit";
  const poll = el("button", "ghost-btn", "轮询");
  poll.type = "button";
  poll.disabled = true;
  actions.append(submit, poll);
  form.append(actions);

  let lastResponse = null;
  let busy = false;
  let close = () => {};

  function render(response = lastResponse, statusText = "") {
    result.replaceChildren();
    if (!response) {
      result.appendChild(emptyResult());
      return;
    }
    const job = response.job || {};
    const status = String(job.status || response.status || "");
    const summary = el("div", `external-video-status ${statusTone(status)}`);
    summary.appendChild(el("strong", "", statusLabel(status)));
    summary.appendChild(el("span", "", `${response.engine || "external"} · ${shortId(job.job_id)}`));
    result.appendChild(summary);

    if (response.preview?.preview_url) {
      const video = document.createElement("video");
      video.className = "external-video-preview";
      video.controls = true;
      video.playsInline = true;
      video.src = runtime.toMediaUrl(response.preview.preview_url);
      result.appendChild(video);
      const download = el("a", "external-video-download");
      download.href = runtime.toMediaUrl(response.preview.download_url);
      download.download = "afs-external-video.mp4";
      download.textContent = "下载成片";
      result.appendChild(download);
    }

    const blocks = Array.isArray(response.safe_manifest?.blocks) ? response.safe_manifest.blocks : [];
    for (const block of blocks.slice(0, 2)) {
      result.appendChild(el("p", "external-video-block", safeBlockText(block)));
    }
    if (statusText) result.appendChild(el("p", "external-video-note", statusText));
    poll.disabled = !["submitted", "running"].includes(status) || busy;
  }

  async function runSubmit(event) {
    event.preventDefault();
    if (busy) return;
    busy = true;
    submit.disabled = true;
    poll.disabled = true;
    render(lastResponse, "提交中");
    try {
      const promptText = fields.prompt.input.value.trim();
      if (!promptText) throw new Error("请先填写创作意图。");
      lastResponse = await runtime.generateExternalVideo({
        title: fields.title.input.value.trim() || "AI comic video job",
        engine: fields.engine.input.value,
        style: fields.style.input.value.trim() || "animated_comic",
        aspect_ratio: fields.aspectRatio.input.value,
        duration_sec: Number(fields.duration.input.value || 6),
        scene_count: Number(fields.scenes.input.value || 3),
        prompt_text: promptText,
        generated_at: new Date().toISOString(),
      });
      render(lastResponse);
    } catch (error) {
      renderError(error);
    } finally {
      busy = false;
      submit.disabled = false;
      poll.disabled = !["submitted", "running"].includes(String(lastResponse?.job?.status || ""));
    }
  }

  async function runPoll() {
    const jobId = String(lastResponse?.job?.job_id || "");
    if (!jobId || busy) return;
    busy = true;
    poll.disabled = true;
    render(lastResponse, "轮询中");
    try {
      lastResponse = await runtime.pollExternalVideo(jobId);
      render(lastResponse);
    } catch (error) {
      renderError(error);
    } finally {
      busy = false;
      poll.disabled = !["submitted", "running"].includes(String(lastResponse?.job?.status || ""));
    }
  }

  function renderError(error) {
    result.replaceChildren();
    result.appendChild(el("div", "external-video-status failed", "失败"));
    result.appendChild(el("p", "external-video-block", formatError ? formatError(error) : String(error?.message || error || "请求失败")));
  }

  form.addEventListener("submit", runSubmit);
  poll.addEventListener("click", runPoll);
  closeBtn.addEventListener("click", () => close());
  close = showModal(modal, { ariaLabel: "AI comic video job" });
  render();
}

function textInput(label, value, placeholder = "") {
  const input = document.createElement("input");
  input.value = value;
  input.placeholder = placeholder;
  input.autocomplete = "off";
  return { label, input };
}

function numberInput(label, value, attrs) {
  const input = document.createElement("input");
  input.type = "number";
  input.value = value;
  for (const [key, item] of Object.entries(attrs || {})) input.setAttribute(key, item);
  return { label, input };
}

function selectInput(label, options) {
  const input = document.createElement("select");
  for (const [value, text] of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    input.appendChild(option);
  }
  return { label, input };
}

function textareaInput(label, value, placeholder = "") {
  const input = document.createElement("textarea");
  input.rows = 7;
  input.value = value;
  input.placeholder = placeholder;
  return { label, input };
}

function fieldShell(field) {
  const label = el("label", "external-video-field");
  label.appendChild(el("span", "", field.label));
  label.appendChild(field.input);
  return label;
}

function compactFieldRow(fields) {
  const row = el("div", "external-video-field-row");
  for (const field of fields) row.appendChild(fieldShell(field));
  return row;
}

function emptyResult() {
  const empty = el("div", "external-video-empty");
  empty.appendChild(el("strong", "", "待生成"));
  empty.appendChild(el("span", "", "暂无预览"));
  return empty;
}

function statusTone(status) {
  if (status === "succeeded") return "succeeded";
  if (["blocked", "failed", "needs_attention"].includes(status)) return "failed";
  return "running";
}

function statusLabel(status) {
  const labels = {
    succeeded: "已完成",
    submitted: "已提交",
    running: "生成中",
    blocked: "已阻断",
    failed: "失败",
    needs_attention: "需处理",
  };
  return labels[status] || status || "未知";
}

function shortId(value) {
  const text = String(value || "");
  if (!text) return "no job";
  return text.length > 22 ? `${text.slice(0, 10)}…${text.slice(-8)}` : text;
}

function safeBlockText(block) {
  return String(block?.reason || block?.block_id || "任务被阻断").replace(/\s+/g, " ").trim().slice(0, 180);
}
