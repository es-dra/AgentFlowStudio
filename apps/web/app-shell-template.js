import { memoryShellTemplate } from "./app-shell-memory-template.js";
import { productionShellTemplate } from "./app-shell-production-template.js";
import { reviewShellTemplate } from "./app-shell-review-template.js";

export function mountAppShell() {
  const root = document.querySelector("#app-root");
  if (!root) throw new Error("Missing #app-root");
  root.innerHTML = `
    <main class="app-shell" aria-label="NarratoCut static artifact viewer">
      ${reviewShellTemplate()}
      ${productionShellTemplate()}
      ${memoryShellTemplate()}
    </main>
  `;
}
