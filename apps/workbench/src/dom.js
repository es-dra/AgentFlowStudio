export function el(tag, options = {}, children = []) {
  const node = ["svg", "path", "circle", "line", "polyline", "defs", "marker"].includes(tag)
    ? document.createElementNS("http://www.w3.org/2000/svg", tag)
    : document.createElement(tag);
  for (const [key, value] of Object.entries(options)) {
    if (key === "className") {
      if (node.namespaceURI === "http://www.w3.org/2000/svg") node.setAttribute("class", value);
      else node.className = value;
    }
    else if (key === "text") node.textContent = value;
    else if (key === "dataset") {
      for (const [dataKey, dataValue] of Object.entries(value)) node.dataset[dataKey] = dataValue;
    } else if (key === "attrs") {
      for (const [attrKey, attrValue] of Object.entries(value)) node.setAttribute(attrKey, attrValue);
    }
  }
  for (const child of children) {
    if (child) node.append(child);
  }
  return node;
}

export function button(label, action, variant = "secondary", dataset = {}) {
  return el("button", { className: `btn ${variant}`, text: label, dataset: { action, ...dataset } });
}

export function badge(text, tone = "quiet") {
  return el("span", { className: `badge ${tone}`, text: String(text || "") });
}

export function field(label, id, value, attrs = {}) {
  const input = el("input", { attrs: { id, value, autocomplete: "off", spellcheck: "false", ...attrs } });
  return el("label", { className: "field" }, [el("span", { text: label }), input]);
}

export function textareaField(label, id, value, attrs = {}) {
  const textarea = el("textarea", { attrs: { id, spellcheck: "false", ...attrs } });
  textarea.value = value || "";
  return el("label", { className: "field" }, [el("span", { text: label }), textarea]);
}

export function selectField(label, id, value, options = []) {
  const select = el("select", { attrs: { id } });
  for (const option of options) {
    const node = el("option", { text: option.label || option.value, attrs: { value: option.value } });
    if (option.value === value) node.selected = true;
    select.append(node);
  }
  return el("label", { className: "field" }, [el("span", { text: label }), select]);
}

export function sectionTitle(title, meta = "") {
  const children = [el("h2", { text: title })];
  if (meta) children.push(el("span", { className: "section-meta", text: meta }));
  return el("div", { className: "section-title" }, children);
}
