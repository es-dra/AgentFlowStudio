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
    '<svg class="sprite-tuantuan-cat" aria-hidden="true" viewBox="0 0 360 210" focusable="false">',
    "  <defs>",
    '    <linearGradient id="tuantuanBody" x1="44" y1="20" x2="322" y2="182" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#18334a" />',
    '      <stop offset="0.3" stop-color="#0d1b29" />',
    '      <stop offset="0.68" stop-color="#081018" />',
    '      <stop offset="1" stop-color="#020408" />',
    "    </linearGradient>",
    '    <linearGradient id="tuantuanEar" x1="52" y1="12" x2="210" y2="96" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#274962" />',
    '      <stop offset="0.46" stop-color="#111f2d" />',
    '      <stop offset="1" stop-color="#03060a" />',
    "    </linearGradient>",
    '    <radialGradient id="tuantuanEye" cx="38%" cy="28%" r="72%">',
    '      <stop offset="0" stop-color="#ffffff" />',
    '      <stop offset="0.2" stop-color="#ffffff" />',
    '      <stop offset="0.28" stop-color="#a8b6ff" />',
    '      <stop offset="0.4" stop-color="#00e5ff" />',
    '      <stop offset="0.54" stop-color="#06233a" />',
    '      <stop offset="0.68" stop-color="#03070d" />',
    '      <stop offset="1" stop-color="#000204" />',
    "    </radialGradient>",
    '    <linearGradient id="tuantuanSprout" x1="0" y1="0" x2="0" y2="46" gradientUnits="userSpaceOnUse">',
    '      <stop offset="0" stop-color="#d8ff78" />',
    '      <stop offset="0.54" stop-color="#7cff82" />',
    '      <stop offset="1" stop-color="#244a34" />',
    "    </linearGradient>",
    '    <radialGradient id="tuantuanSoftGlow" cx="50%" cy="50%" r="72%">',
    '      <stop offset="0" stop-color="#00e5ff" stop-opacity="0.3" />',
    '      <stop offset="1" stop-color="#00e5ff" stop-opacity="0" />',
    "    </radialGradient>",
    "  </defs>",
    '  <ellipse class="sprite-cat-ground-glow" cx="178" cy="182" rx="155" ry="20" />',
    '  <g class="sprite-cat-resting-silhouette">',
    '    <g class="sprite-cat-tail">',
    '      <path class="sprite-cat-tail-shape" d="M244 143 C292 143 334 116 323 78 C316 51 282 43 266 68 C249 96 282 115 301 91" />',
    '      <path class="sprite-tail-panel one" d="M318 76 C322 93 315 109 301 119" />',
    '      <path class="sprite-tail-panel two" d="M262 76 C276 91 286 107 290 126" />',
    '      <path class="sprite-tail-panel three" d="M236 141 C255 144 274 151 288 164" />',
    "    </g>",
    '    <path class="sprite-cat-body sprite-cat-outline" d="M124 139 C141 97 189 76 242 80 C303 84 338 117 331 150 C323 189 253 194 188 171 C151 158 116 164 93 150 C81 142 97 138 124 139 Z" />',
    '    <path class="sprite-cat-body-shade" d="M145 102 C188 76 267 83 310 126 C264 110 210 111 163 125 C130 135 106 148 90 153 C86 129 106 112 145 102 Z" />',
    '    <path class="sprite-cat-back-glow" d="M155 94 C207 68 290 91 317 143" />',
    '    <path class="sprite-cat-tabby-mark body one" d="M184 91 C203 101 217 118 224 138" />',
    '    <path class="sprite-cat-tabby-mark body two" d="M232 91 C251 108 260 126 262 146" />',
    '    <path class="sprite-cat-tabby-mark body three" d="M272 147 C246 162 211 163 174 150" />',
    '    <path class="sprite-cat-rear-paw sprite-cat-outline" d="M232 153 C252 136 285 140 294 158 C289 181 249 183 227 170 C219 164 223 158 232 153 Z" />',
    '    <g class="sprite-cat-head">',
    '      <path class="sprite-cat-ear left sprite-cat-outline" d="M62 88 C51 42 73 19 111 52 C122 66 111 91 91 98 Z" />',
    '      <path class="sprite-cat-ear-rim left" d="M68 82 C64 51 77 32 105 56" />',
    '      <path class="sprite-cat-inner-ear left" d="M75 77 C71 52 82 40 101 59 C103 71 92 82 80 83 Z" />',
    '      <path class="sprite-cat-ear right sprite-cat-outline" d="M167 83 C188 38 218 28 217 78 C213 96 191 105 173 95 Z" />',
    '      <path class="sprite-cat-ear-rim right" d="M177 78 C193 48 207 43 207 73" />',
    '      <path class="sprite-cat-inner-ear right" d="M179 76 C193 53 204 47 204 72 C201 84 189 90 180 86 Z" />',
    '      <path class="sprite-cat-face sprite-cat-outline" d="M55 101 C68 55 111 34 153 47 C198 60 216 100 194 140 C176 174 125 187 82 165 C49 149 41 120 55 101 Z" />',
    '      <path class="sprite-cat-cheek-glow" d="M57 132 C88 157 148 157 188 128 C178 166 126 186 82 165 C61 154 48 141 46 126 Z" />',
    '      <g class="sprite-cat-sprout">',
    '        <path d="M134 48 C132 30 130 17 126 6" />',
    '        <ellipse cx="116" cy="10" rx="15" ry="8" transform="rotate(24 116 10)" />',
    '        <ellipse cx="142" cy="11" rx="16" ry="8" transform="rotate(-24 142 11)" />',
    "      </g>",
    '      <path class="sprite-cat-face-ridge" d="M135 56 C120 69 124 83 141 91 C129 75 151 68 135 56 Z" />',
    '      <path class="sprite-cat-face-mark forehead" d="M128 55 C110 69 119 85 136 91 C125 75 145 67 128 55 Z" />',
    '      <path class="sprite-cat-face-mark forehead-side left" d="M96 65 C83 71 75 83 72 96" />',
    '      <path class="sprite-cat-face-mark forehead-side right" d="M157 65 C173 73 181 86 181 101" />',
    '      <path class="sprite-cat-face-mark cheek left" d="M57 117 C77 112 94 117 106 127" />',
    '      <path class="sprite-cat-face-mark cheek right" d="M158 126 C173 116 187 114 199 119" />',
    '      <g class="sprite-cat-eye left"><ellipse class="sprite-cat-eye-base" cx="96" cy="116" rx="17" ry="25" /><ellipse class="sprite-cat-pupil" cx="98" cy="119" rx="9" ry="16" /><circle class="sprite-cat-eye-shine" cx="90" cy="105" r="5.8" /><circle class="sprite-cat-eye-shine small" cx="104" cy="130" r="3.6" /></g>',
    '      <g class="sprite-cat-eye right"><ellipse class="sprite-cat-eye-base" cx="154" cy="116" rx="17" ry="25" /><ellipse class="sprite-cat-pupil" cx="156" cy="119" rx="9" ry="16" /><circle class="sprite-cat-eye-shine" cx="148" cy="105" r="5.8" /><circle class="sprite-cat-eye-shine small" cx="162" cy="131" r="3.6" /></g>',
    '      <path class="sprite-cat-nose" d="M124 138 C131 132 138 134 142 139 C138 146 128 146 124 138 Z" />',
    '      <path class="sprite-cat-mouth" d="M133 145 C125 153 115 151 111 144 M134 145 C142 153 152 151 158 144" />',
    '      <g class="sprite-cat-whiskers left"><path d="M113 136 C86 129 66 130 45 137" /><path d="M114 145 C87 146 67 155 49 167" /></g>',
    '      <g class="sprite-cat-whiskers right"><path d="M153 137 C181 130 202 132 220 139" /><path d="M153 146 C181 149 201 158 219 170" /></g>',
    "    </g>",
    '    <g class="sprite-cat-forepaws">',
    '      <path class="sprite-cat-paw left sprite-cat-outline" d="M67 165 C82 150 109 152 119 167 C116 185 77 187 64 176 C59 172 62 168 67 165 Z" />',
    '      <path class="sprite-cat-paw right sprite-cat-outline" d="M150 165 C165 150 193 152 201 169 C195 187 156 187 144 176 C140 172 145 167 150 165 Z" />',
    "    </g>",
    '    <g class="sprite-cat-story-panel">',
    '      <rect x="110" y="151" width="44" height="24" rx="10" />',
    '      <circle cx="122" cy="160" r="2.6" />',
    '      <circle cx="139" cy="160" r="2.6" />',
    '      <path d="M122 169 C128 173 136 173 142 169" />',
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
