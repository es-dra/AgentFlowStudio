import { icon } from "./icons.js";
import { el, showModal } from "./overlay.js";
import { setRuntimeMediaSource } from "./runtime-media-source.js";

export function openMediaPreviewModal({ url, type = "image", title = "媒体预览", aspectRatio = "", downloadName = "" }) {
  if (!url) return;
  const modal = el("div", "modal media-preview-modal");
  const head = el("div", "modal-head");
  const titleEl = el("strong", "", title);
  const spacer = el("span", "head-spacer");
  const download = el("button", "media-preview-download");
  download.type = "button";
  download.innerHTML = `${icon("archive", 14)}<span>${type === "video" ? "下载视频" : "导出原图"}</span>`;
  const closeBtn = el("button", "modal-close");
  closeBtn.type = "button";
  closeBtn.setAttribute("aria-label", "Close media preview");
  closeBtn.innerHTML = icon("x", 15);
  head.append(titleEl, spacer, download, closeBtn);

  const body = el("div", "modal-body media-preview-body");
  if (type === "video") {
    const video = document.createElement("video");
    video.className = "media-preview-video";
    video.controls = true;
    video.playsInline = true;
    video.autoplay = true;
    video.preload = "metadata";
    setRuntimeMediaSource(video, url);
    body.appendChild(video);
  } else {
    const img = document.createElement("img");
    img.className = "media-preview-image";
    img.alt = title || "生成图片预览";
    if (aspectRatio) img.style.aspectRatio = aspectRatio;
    setRuntimeMediaSource(img, url);
    body.appendChild(img);
  }
  modal.append(head, body);
  const close = showModal(modal, { initialFocus: closeBtn });
  closeBtn.addEventListener("click", close);
  download.addEventListener("click", () => downloadResolvedMedia(url, downloadName || fallbackDownloadName(title, type), download));
}

export async function downloadResolvedMedia(url, filename, trigger = null) {
  const link = document.createElement("a");
  link.style.display = "none";
  if (trigger) trigger.disabled = true;
  try {
    await setRuntimeMediaSource(link, url);
    if (!link.href) return;
    link.download = filename || fallbackDownloadName("", "image");
    document.body.appendChild(link);
    link.click();
  } finally {
    link.remove();
    if (trigger) trigger.disabled = false;
  }
}

function fallbackDownloadName(title, type) {
  const base = String(title || (type === "video" ? "afs-video" : "afs-image"))
    .replace(/[\\/:*?"<>|]+/g, "-")
    .trim()
    .slice(0, 80) || (type === "video" ? "afs-video" : "afs-image");
  return `${base}.${type === "video" ? "mp4" : "png"}`;
}
