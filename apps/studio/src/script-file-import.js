export const SCRIPT_UPLOAD_ACCEPT = [
  ".txt",
  ".md",
  ".markdown",
  ".doc",
  ".docx",
  ".ppt",
  ".pptx",
  "text/plain",
  "text/markdown",
  "application/msword",
  "application/vnd.ms-powerpoint",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
].join(",");

export async function readScriptFileText(file) {
  const ext = scriptFileExtension(file?.name);
  if (["txt", "md", "markdown"].includes(ext) || /^text\//i.test(String(file?.type || ""))) {
    return nonEmptyScriptText(await file.text(), file?.name);
  }
  const buffer = await file.arrayBuffer();
  if (ext === "docx") return nonEmptyScriptText(await extractOfficeOpenXmlText(buffer, "docx"), file?.name);
  if (ext === "pptx") return nonEmptyScriptText(await extractOfficeOpenXmlText(buffer, "pptx"), file?.name);
  if (ext === "doc" || ext === "ppt") return nonEmptyScriptText(extractLegacyOfficeBinaryText(buffer), file?.name);
  if (typeof file?.text === "function") return nonEmptyScriptText(await file.text(), file?.name);
  throw new Error("不支持的剧本文件格式");
}

export function scriptFileExtension(name) {
  return String(name || "").split(".").pop()?.toLowerCase() || "";
}

export function safeFileName(name) {
  return String(name || "").replace(/[\\/:*?"<>|]+/g, "-").slice(0, 120);
}

async function extractOfficeOpenXmlText(buffer, kind) {
  const entries = await readZipTextEntries(buffer);
  const paths = kind === "pptx"
    ? Object.keys(entries).filter((path) => /^ppt\/slides\/slide\d+\.xml$/i.test(path)).sort(compareSlidePath)
    : ["word/document.xml"];
  const text = paths
    .map((path) => entries[path])
    .filter(Boolean)
    .map(xmlBodyText)
    .filter(Boolean)
    .join("\n\n");
  if (text) return text;
  throw new Error(kind === "pptx" ? "PPT 中没有找到可读取的幻灯片文字" : "Word 中没有找到可读取的正文");
}

async function readZipTextEntries(buffer) {
  const bytes = new Uint8Array(buffer);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const eocd = findZipEndOfCentralDirectory(view);
  if (eocd < 0) throw new Error("Office 文件不是有效的 OOXML zip 文档");
  const entryCount = view.getUint16(eocd + 10, true);
  const centralOffset = view.getUint32(eocd + 16, true);
  const decoder = new TextDecoder("utf-8");
  const entries = {};
  let offset = centralOffset;
  for (let index = 0; index < entryCount && offset + 46 <= bytes.length; index += 1) {
    if (view.getUint32(offset, true) !== 0x02014b50) break;
    const method = view.getUint16(offset + 10, true);
    const compressedSize = view.getUint32(offset + 20, true);
    const nameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const localHeaderOffset = view.getUint32(offset + 42, true);
    const name = decoder.decode(bytes.slice(offset + 46, offset + 46 + nameLength));
    if (isOfficeXmlTextPath(name)) {
      const fileBytes = await readZipFileBytes(bytes, view, localHeaderOffset, compressedSize, method);
      entries[name] = decoder.decode(fileBytes);
    }
    offset += 46 + nameLength + extraLength + commentLength;
  }
  return entries;
}

async function readZipFileBytes(bytes, view, localHeaderOffset, compressedSize, method) {
  if (view.getUint32(localHeaderOffset, true) !== 0x04034b50) throw new Error("Office 文件 zip 条目损坏");
  const nameLength = view.getUint16(localHeaderOffset + 26, true);
  const extraLength = view.getUint16(localHeaderOffset + 28, true);
  const dataOffset = localHeaderOffset + 30 + nameLength + extraLength;
  const compressed = bytes.slice(dataOffset, dataOffset + compressedSize);
  if (method === 0) return compressed;
  if (method !== 8) throw new Error("Office 文件使用了暂不支持的 zip 压缩方式");
  return inflateRaw(compressed);
}

async function inflateRaw(bytes) {
  if (typeof DecompressionStream === "function") {
    try {
      const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
      return new Uint8Array(await new Response(stream).arrayBuffer());
    } catch (error) {
      const nodeInflated = await inflateRawInNode(bytes);
      if (nodeInflated) return nodeInflated;
      throw error;
    }
  }
  const nodeInflated = await inflateRawInNode(bytes);
  if (nodeInflated) return nodeInflated;
  throw new Error("当前浏览器不支持本地解压 Word/PPT 文件，请先另存为 txt 或 markdown");
}

async function inflateRawInNode(bytes) {
  if (!globalThis.process?.versions?.node) {
    return null;
  }
  try {
    const { inflateRawSync } = await import("node:zlib");
    return new Uint8Array(inflateRawSync(bytes));
  } catch {
    return null;
  }
}

function findZipEndOfCentralDirectory(view) {
  for (let offset = view.byteLength - 22; offset >= 0 && offset >= view.byteLength - 65558; offset -= 1) {
    if (view.getUint32(offset, true) === 0x06054b50) return offset;
  }
  return -1;
}

function isOfficeXmlTextPath(path) {
  return path === "word/document.xml" || /^ppt\/slides\/slide\d+\.xml$/i.test(path);
}

function compareSlidePath(left, right) {
  return slideNumber(left) - slideNumber(right) || left.localeCompare(right);
}

function slideNumber(path) {
  return Number(path.match(/slide(\d+)\.xml/i)?.[1] || 0);
}

function xmlBodyText(xml) {
  const withBreaks = String(xml || "")
    .replace(/<\/(?:w|a):p>/g, "\n")
    .replace(/<\/(?:w|a):br>/g, "\n")
    .replace(/<[^>]+>/g, "");
  return normalizeImportedScriptText(decodeXmlEntities(withBreaks));
}

function decodeXmlEntities(value) {
  return String(value || "")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&");
}

function extractLegacyOfficeBinaryText(buffer) {
  const utf16 = new TextDecoder("utf-16le", { fatal: false }).decode(buffer);
  const latin = new TextDecoder("latin1", { fatal: false }).decode(buffer);
  return normalizeImportedScriptText(`${printableRuns(utf16)}\n${printableRuns(latin)}`);
}

function printableRuns(value) {
  return (String(value || "").match(/[\u4e00-\u9fa5A-Za-z0-9，。！？；：、,.!?;:'"()\[\]《》“”‘’\-\s]{4,}/g) || [])
    .map((item) => item.trim())
    .filter((item) => item.length >= 4)
    .join("\n");
}

function nonEmptyScriptText(value, name = "") {
  const text = normalizeImportedScriptText(value);
  if (text) return text;
  throw new Error(`${safeFileName(name) || "文件"} 没有可读取的剧本文字`);
}

function normalizeImportedScriptText(value) {
  return String(value || "")
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .map((line) => line.replace(/\s+/g, " ").trim())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
