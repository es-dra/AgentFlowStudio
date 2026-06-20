export const SPRITE_AGENT_STATES = {
  observe: "观察",
  think: "思考",
  suggest: "提案",
  preview: "预览",
  execute: "执行",
  complete: "完成",
  sleep: "休息",
};

// TuanTuan visualizes the AFS Agent sequence: Observe → Suggest → Execute.
const IDLE_AGENT_STATES = ["observe", "observe", "think", "observe", "sleep"];
let spriteTickerBound = false;
let idleStateIndex = 0;
let temporaryState = "";
let temporaryStateTimer = 0;

export function spriteStoryLayers() {
  return [
    '<span class="sprite-story-orbit" aria-hidden="true">',
    '  <i data-orbit-node="observe"></i>',
    '  <i data-orbit-node="suggest"></i>',
    '  <i data-orbit-node="preview"></i>',
    '  <i data-orbit-node="execute"></i>',
    '  <i data-orbit-node="complete"></i>',
    "</span>",
    '<span class="sprite-preview-ghost" aria-hidden="true"></span>',
    '<span class="sprite-suggestion-bubble" aria-hidden="true"><i></i><b></b><i></i></span>',
    '<span class="sprite-complete-sparks" aria-hidden="true"><i></i><i></i><i></i></span>',
    '<span class="sprite-sleep-mark" aria-hidden="true">zZ</span>',
    '<svg class="sprite-tuantuan-cat" aria-hidden="true" viewBox="0 0 390 230" focusable="false">',
    "  <defs>",
    '    <linearGradient id="tuantuanBody" x1="56" y1="32" x2="335" y2="210" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#172b3b" />',
    '      <stop offset="0.28" stop-color="#0e1b28" />',
    '      <stop offset="0.72" stop-color="#071018" />',
    '      <stop offset="1" stop-color="#020509" />',
    "    </linearGradient>",
    '    <linearGradient id="tuantuanEar" x1="63" y1="20" x2="206" y2="118" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#254259" />',
    '      <stop offset="0.48" stop-color="#101d2a" />',
    '      <stop offset="1" stop-color="#03060b" />',
    "    </linearGradient>",
    '    <linearGradient id="tuantuanStripe" x1="70" y1="55" x2="315" y2="178" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#02070d" stop-opacity="0.9" />',
    '      <stop offset="1" stop-color="#000307" stop-opacity="0.44" />',
    "    </linearGradient>",
    '    <radialGradient id="tuantuanEye" cx="38%" cy="26%" r="76%">',
    '      <stop offset="0" stop-color="#ffffff" />',
    '      <stop offset="0.2" stop-color="#ffffff" />',
    '      <stop offset="0.29" stop-color="#b7c3ff" />',
    '      <stop offset="0.42" stop-color="#36e8ff" />',
    '      <stop offset="0.56" stop-color="#063356" />',
    '      <stop offset="0.76" stop-color="#020812" />',
    '      <stop offset="1" stop-color="#000204" />',
    "    </radialGradient>",
    '    <linearGradient id="tuantuanSprout" x1="0" y1="0" x2="0" y2="54" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#d9ff7d" />',
    '      <stop offset="0.54" stop-color="#7cff82" />',
    '      <stop offset="1" stop-color="#25523a" />',
    "    </linearGradient>",
    '    <radialGradient id="tuantuanSoftGlow" cx="50%" cy="50%" r="72%">',
    '      <stop offset="0" stop-color="#00e5ff" stop-opacity="0.28" />',
    '      <stop offset="1" stop-color="#00e5ff" stop-opacity="0" />',
    "    </radialGradient>",
    "  </defs>",
    '  <ellipse class="sprite-cat-ground-glow" cx="196" cy="201" rx="168" ry="23" />',
    '  <g class="sprite-cat-resting-silhouette">',
    '    <g class="sprite-cat-tail">',
    '      <path class="sprite-cat-tail-shape sprite-cat-outline" d="M251 160 C304 160 352 130 349 88 C346 55 314 38 288 57 C260 78 274 125 313 116 C336 111 343 88 326 77 C344 101 331 130 303 139 C274 148 247 132 246 105 C244 81 262 56 287 47 C326 34 363 60 366 96 C371 147 317 181 260 187 C249 183 245 169 251 160 Z" />',
    '      <path class="sprite-tail-panel one" d="M342 77 C354 102 345 130 322 147" />',
    '      <path class="sprite-tail-panel two" d="M288 66 C305 91 310 120 303 145" />',
    '      <path class="sprite-tail-panel three" d="M253 161 C276 165 300 177 314 194" />',
    "    </g>",
    '    <path class="sprite-cat-body sprite-cat-outline" d="M129 151 C145 106 197 80 257 85 C318 90 355 124 347 161 C339 202 271 209 204 187 C160 173 125 179 99 161 C87 153 99 148 129 151 Z" />',
    '    <path class="sprite-cat-body-shade" d="M148 112 C195 85 282 93 323 137 C278 119 218 121 167 136 C133 146 106 160 91 163 C90 139 110 124 148 112 Z" />',
    '    <path class="sprite-cat-back-glow" d="M157 105 C215 75 306 96 335 153" />',
    '    <path class="sprite-cat-tabby-mark body one" d="M199 96 C215 111 225 130 228 152" />',
    '    <path class="sprite-cat-tabby-mark body two" d="M246 94 C263 113 271 136 269 158" />',
    '    <path class="sprite-cat-tabby-mark body three" d="M290 151 C263 169 222 171 181 158" />',
    '    <path class="sprite-cat-tabby-mark body four" d="M315 128 C300 142 294 159 296 176" />',
    '    <path class="sprite-cat-rear-paw sprite-cat-outline" d="M242 165 C261 147 297 151 307 170 C300 194 260 195 236 181 C228 175 232 169 242 165 Z" />',
    '    <g class="sprite-cat-head">',
    '      <path class="sprite-cat-ear left sprite-cat-outline" d="M55 106 C43 40 76 8 124 58 C136 80 116 112 90 116 Z" />',
    '      <path class="sprite-cat-ear-rim left" d="M65 96 C61 56 81 31 113 64" />',
    '      <path class="sprite-cat-inner-ear left" d="M74 89 C72 56 88 40 108 66 C110 82 94 97 80 97 Z" />',
    '      <path class="sprite-cat-ear right sprite-cat-outline" d="M166 101 C195 34 235 22 241 91 C234 119 199 124 177 109 Z" />',
    '      <path class="sprite-cat-ear-rim right" d="M179 92 C199 51 220 45 225 84" />',
    '      <path class="sprite-cat-inner-ear right" d="M184 89 C201 59 216 51 220 82 C216 99 199 105 187 99 Z" />',
    '      <path class="sprite-cat-face sprite-cat-outline" d="M54 113 C68 61 116 36 163 51 C211 66 231 112 204 154 C183 187 127 198 83 172 C51 153 41 128 54 113 Z" />',
    '      <path class="sprite-cat-cheek-glow" d="M57 141 C92 169 153 168 197 136 C184 177 128 199 83 172 C62 160 49 146 47 131 Z" />',
    '      <g class="sprite-cat-sprout">',
    '        <path d="M141 52 C140 34 136 20 130 8" />',
    '        <ellipse cx="121" cy="12" rx="17" ry="9" transform="rotate(22 121 12)" />',
    '        <ellipse cx="149" cy="13" rx="18" ry="9" transform="rotate(-24 149 13)" />',
    "      </g>",
    '      <path class="sprite-cat-face-ridge" d="M142 59 C122 76 128 94 147 100 C135 82 160 72 142 59 Z" />',
    '      <path class="sprite-cat-face-mark forehead" d="M134 58 C114 73 121 92 141 100 C129 82 151 72 134 58 Z" />',
    '      <path class="sprite-cat-face-mark brow left" d="M92 76 C78 83 69 96 67 111" />',
    '      <path class="sprite-cat-face-mark brow right" d="M164 75 C181 84 190 100 189 116" />',
    '      <path class="sprite-cat-face-mark cheek left" d="M58 126 C80 121 99 127 111 139" />',
    '      <path class="sprite-cat-face-mark cheek right" d="M163 139 C181 126 195 124 208 130" />',
    '      <g class="sprite-cat-eye left"><ellipse class="sprite-cat-eye-base" cx="97" cy="126" rx="18" ry="27" /><ellipse class="sprite-cat-pupil" cx="99" cy="129" rx="10" ry="17" /><circle class="sprite-cat-eye-shine" cx="91" cy="114" r="6.2" /><circle class="sprite-cat-eye-shine small" cx="105" cy="140" r="3.8" /></g>',
    '      <g class="sprite-cat-eye right"><ellipse class="sprite-cat-eye-base" cx="160" cy="126" rx="18" ry="27" /><ellipse class="sprite-cat-pupil" cx="162" cy="129" rx="10" ry="17" /><circle class="sprite-cat-eye-shine" cx="154" cy="114" r="6.2" /><circle class="sprite-cat-eye-shine small" cx="168" cy="141" r="3.8" /></g>',
    '      <path class="sprite-cat-nose" d="M128 150 C135 144 143 146 147 151 C143 159 132 159 128 150 Z" />',
    '      <path class="sprite-cat-mouth" d="M137 157 C129 166 117 164 113 156 M138 157 C146 166 158 164 163 156" />',
    '      <g class="sprite-cat-whiskers left"><path d="M117 148 C88 140 65 142 43 151" /><path d="M118 157 C89 159 69 169 51 181" /></g>',
    '      <g class="sprite-cat-whiskers right"><path d="M158 149 C188 142 211 144 232 153" /><path d="M158 158 C188 162 211 172 229 184" /></g>',
    "    </g>",
    '    <g class="sprite-cat-forepaws">',
    '      <path class="sprite-cat-paw left sprite-cat-outline" d="M68 178 C84 160 112 162 124 179 C120 199 79 200 65 188 C59 183 62 180 68 178 Z" />',
    '      <path class="sprite-cat-paw right sprite-cat-outline" d="M153 178 C170 160 199 163 208 181 C202 199 160 200 147 188 C142 183 147 180 153 178 Z" />',
    "    </g>",
    '    <g class="sprite-cat-story-panel">',
    '      <rect x="113" y="164" width="51" height="28" rx="12" />',
    '      <circle cx="127" cy="174" r="2.8" />',
    '      <circle cx="148" cy="174" r="2.8" />',
    '      <path d="M127 184 C134 188 143 188 150 184" />',
    "    </g>",
    "  </g>",
    "</svg>",
    '<span class="sprite-tuantuan-shadow" aria-hidden="true"></span>',
  ];
}

export function currentSpritePose(state = {}) {
  return currentSpriteState(state);
}

export function currentSpriteState(state = {}) {
  if (temporaryState) return temporaryState;
  if (state.sending) return "think";
  if (state.settingsOpen) return "think";
  if (state.open) return "suggest";
  return IDLE_AGENT_STATES[idleStateIndex] || "observe";
}

export function setSpritePose(button = document.querySelector(".afs-sprite-avatar"), state = currentSpriteState()) {
  if (!button) return;
  const nextState = SPRITE_AGENT_STATES[state] ? state : "observe";
  button.dataset.spriteState = nextState;
  button.dataset.spritePose = nextState;
}

export function applySpritePose(root = document.getElementById("sprite-root"), state = {}) {
  setSpritePose(root?.querySelector(".afs-sprite-avatar"), currentSpriteState(state));
}

export function bindSpritePoseTicker(getState, onTick) {
  if (spriteTickerBound || typeof window === "undefined") return;
  spriteTickerBound = true;
  window.setInterval(() => {
    const state = getState?.() || {};
    if (state.open || state.settingsOpen || state.sending || temporaryState) return;
    const root = document.getElementById("sprite-root");
    if (root?.classList.contains("is-dragging")) return;
    idleStateIndex = (idleStateIndex + 1) % IDLE_AGENT_STATES.length;
    onTick?.();
  }, 9000);
}

export function setTemporarySpritePose(state, duration = 1500, onExpire) {
  if (!SPRITE_AGENT_STATES[state] || typeof window === "undefined") return;
  temporaryState = state;
  window.clearTimeout(temporaryStateTimer);
  temporaryStateTimer = window.setTimeout(() => {
    temporaryState = "";
    onExpire?.();
  }, duration);
}
