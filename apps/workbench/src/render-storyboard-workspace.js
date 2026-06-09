import { badge, button, el, sectionTitle } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";
import { statusTone } from "./workbench-state.js";

export function renderStoryboardWorkspace(studioWorkspace, creationWorkspace, state) {
  const studio = studioWorkspace || { canvas: { cards: [] }, filmstrip: [], side_rail: {} };
  const creation = creationWorkspace || {};
  const cards = Array.isArray(studio.canvas?.cards) ? studio.canvas.cards : [];
  const shots = storyboardItems(studio, creation, cards);
  const selectedId = selectedStoryboardId(shots, state.selectedCardId);
  const selected = shots.find((item) => item.card_id === selectedId) || shots[0] || null;
  return el("section", { className: "storyboard-workspace" }, [
    renderStoryboardTimeline(shots, selectedId),
    renderShotStage(selected),
    renderShotInspector(selected, studio.side_rail || {}),
  ]);
}

function storyboardItems(studio, creation, cards) {
  const filmstrip = Array.isArray(studio.filmstrip) && studio.filmstrip.length
    ? studio.filmstrip
    : Array.isArray(creation.filmstrip)
      ? creation.filmstrip
      : [];
  if (filmstrip.length) {
    return filmstrip.map((item, index) => {
      const card = cards.find((candidate) => candidate.card_id === item.card_id) || {};
      return {
        ...card,
        ...item,
        title: item.title || card.title || `镜头 ${index + 1}`,
        summary: item.summary || card.summary || "",
        status: card.status || item.status || "ready_not_run",
        refs: card.refs || [],
        blockers: card.blockers || [],
        primary_artifact_id: card.primary_artifact_id || "",
      };
    });
  }
  return cards.map((card, index) => ({ ...card, title: card.title || `镜头 ${index + 1}` }));
}

function selectedStoryboardId(items, selectedCardId) {
  if (items.some((item) => item.card_id === selectedCardId)) return selectedCardId;
  return items[0]?.card_id || "";
}

function renderStoryboardTimeline(items, selectedId) {
  return el("div", { className: "storyboard-timeline" }, [
    sectionTitle("镜头序列", `${items.length} 个镜头`),
    items.length
      ? el("div", { className: "storyboard-strip" }, items.map((item, index) => renderTimelineItem(item, index, selectedId)))
      : el("p", { className: "muted", text: "生成画布草稿或添加分镜卡后，这里会出现镜头序列。" }),
  ]);
}

function renderTimelineItem(item, index, selectedId) {
  const tone = statusTone(item.status);
  return el("button", { className: `storyboard-shot ${tone}${item.card_id === selectedId ? " selected" : ""}`, dataset: { cardId: item.card_id } }, [
    el("span", { text: String(index + 1).padStart(2, "0") }),
    el("strong", { text: displayText(item.title || "未命名镜头") }),
    el("small", { text: displayText(item.summary || item.status || "等待制作") }),
  ]);
}

function renderShotStage(item) {
  if (!item) {
    return el("section", { className: "storyboard-stage" }, [
      sectionTitle("当前镜头", "empty"),
      el("p", { className: "muted", text: "还没有可检查的镜头。" }),
    ]);
  }
  const tone = statusTone(item.status);
  return el("section", { className: "storyboard-stage" }, [
    el("div", { className: "storyboard-stage-head" }, [
      badge(displayStatus(item.status || "ready_not_run"), tone),
      item.primary_artifact_id ? button("打开镜头产物", "open-artifact-ref", "ghost", { artifactId: item.primary_artifact_id }) : null,
    ]),
    el("h3", { text: displayText(item.title || "当前镜头") }),
    item.summary ? el("p", { className: "card-summary", text: displayText(item.summary) }) : null,
    el("div", { className: "storyboard-preview" }, [
      badge("安全预览", "quiet"),
      el("strong", { text: "媒体字节未进入浏览器" }),
      el("span", { text: "当前视图只展示 safe summary 与 artifact ref。" }),
    ]),
    item.blockers?.length ? el("div", { className: "chips" }, item.blockers.map((blocker) => badge(displayText(blocker.message || blocker.blocker_id), "blocked"))) : null,
  ]);
}

function renderShotInspector(item, sideRail) {
  const assets = Array.isArray(sideRail.assets) ? sideRail.assets : [];
  const refs = item && Array.isArray(item.refs) ? item.refs : [];
  return el("aside", { className: "storyboard-inspector" }, [
    sectionTitle("镜头检查", displayStatus(item?.status || "empty", "空")),
    item ? renderShotFacts(item, refs, assets) : el("p", { className: "muted", text: "选择一个镜头查看引用、阻塞和审片入口。" }),
    item ? renderShotActions(item) : null,
  ]);
}

function renderShotFacts(item, refs, assets) {
  return el("div", { className: "storyboard-facts" }, [
    badge(`${refs.length} 个镜头引用`, refs.length ? "ready" : "quiet"),
    badge(`${assets.length} 个项目素材`, assets.length ? "active" : "quiet"),
    badge(`${item.blockers?.length || 0} 个阻塞`, item.blockers?.length ? "blocked" : "quiet"),
    refs.length ? el("div", { className: "ref-list" }, refs.map(renderRef)) : el("p", { className: "muted", text: "当前镜头没有安全引用。" }),
  ]);
}

function renderRef(ref) {
  return el("div", { className: "ref-row" }, [
    el("span", { text: displayText(ref.label || "ref") }),
    el("code", { text: displayText(ref.artifact_type || "artifact") }),
    el("code", { text: ref.artifact_id || "pending" }),
  ]);
}

function renderShotActions(item) {
  return el("div", { className: "storyboard-actions" }, [
    button("进入审片室", "set-review-intent", "primary", { decision: "keep", nextView: "Review", cardId: item.card_id }),
    button("标记需修改", "set-review-intent", "secondary", { decision: "revise", nextView: "Review", cardId: item.card_id }),
  ]);
}
