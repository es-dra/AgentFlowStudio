from __future__ import annotations

import json
import subprocess


def test_web_readiness_uses_input_check_after_plan_passes() -> None:
    script = """
import { renderReadinessWizard } from "./apps/web/production-render.js";

globalThis.document = {
  createElement(tagName) {
    return {
      tagName,
      className: "",
      children: [],
      _text: "",
      set textContent(value) {
        this._text = value;
      },
      get textContent() {
        return [this._text, ...this.children.map((child) => child.textContent || "")].join("");
      },
      append(...children) {
        this.children.push(...children);
      },
    };
  },
};

const elements = {
  readinessChecklist: {
    children: [],
    replaceChildren(...children) {
      this.children = children;
    },
    append(...children) {
      this.children.push(...children);
    },
  },
};

const workflow = {
  name: "video_script_to_finished_package_local_asr",
  web_profile: {
    kind: "product",
    display_name: "完整成品包：视频脚本",
    next_step_hint: "Local Alpha 0.4: prepare the ignored local media.",
    requirements: ["ffmpeg", "local_asr"],
    local_setup_blockers: [
      "data/raw/demo_real_video/input.mp4",
      "data/raw/demo_bgm/bgm.wav",
    ],
  },
};

renderReadinessWizard(
  elements,
  {
    bridge: {
      status: "ready",
      python: { version: "3.12.12" },
      media: { status: "ready" },
      local_asr: { status: "ready" },
    },
    plan: {
      input_check: {
        status: "pass",
        summary: "输入引用可用",
        next_action: "运行 workflow",
      },
    },
  },
  workflow,
  { nextAction: "运行 workflow", blocker: "" },
);

const text = elements.readinessChecklist.children.map((node) => node.textContent).join("\\n");
console.log(JSON.stringify({ text }));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    payload = json.loads(result.stdout)

    assert "输入引用可用" in payload["text"]
    assert "运行 workflow" in payload["text"]
    assert "local_setup_blockers" not in payload["text"]
    assert "prepare the ignored local media" not in payload["text"]

def test_web_production_run_feedback_event_shape() -> None:
    script = """
import { buildRunFeedbackEvent } from "./apps/web/feedback-event.js";

const event = buildRunFeedbackEvent({
  run: {
    run_dir: "data/processed/runs/web_bridge/mock_text_to_slices",
      run_id: "mock_text_to_slices",
      manifest_path: "data/processed/runs/web_bridge/mock_text_to_slices/manifest.json",
      review_status: "passed",
      review_artifacts: {
        quality_report: "data/processed/runs/web_bridge/mock_text_to_slices/quality_report.json",
        review_report: "data/processed/runs/web_bridge/mock_text_to_slices/review_report.json",
      },
    },
  workflow: { name: "mock_text_to_slices" },
  decision: "needs_changes",
  riskCategory: "video_review",
  note: "需要补完整成品素材。",
  videoTimeSec: "12.5",
});
console.log(JSON.stringify(event));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    event = json.loads(result.stdout)

    assert event["event_type"] == "run_feedback_event"
    assert event["source"] == "agentflow_studio_web_production_mode"
    assert event["run_dir"] == "data/processed/runs/web_bridge/mock_text_to_slices"
    assert event["workflow"] == "mock_text_to_slices"
    assert event["review_status"] == "passed"
    assert event["quality_report"].endswith("quality_report.json")
    assert event["review_report"].endswith("review_report.json")
    assert event["decision"] == "needs_changes"
    assert event["risk_category"] == "video_review"
    assert event["video_time_sec"] == 12.5

def test_web_run_feedback_wiring_uses_review_state_when_run_polling_overwrites_review_refs() -> None:
    script = """
import { attachFeedbackHandlers } from "./apps/web/feedback-wiring.js";

function button() {
  return {
    listeners: {},
    addEventListener(name, handler) {
      this.listeners[name] = handler;
    },
  };
}

function valueNode(value = "") {
  return {
    value,
    textContent: "",
    focus() {},
    select() {},
  };
}

const elements = {
  feedbackCopy: button(),
  feedbackArtifact: valueNode(""),
  feedbackDecision: valueNode("accepted"),
  feedbackRisk: valueNode("general_review"),
  feedbackTime: valueNode(""),
  feedbackNote: valueNode(""),
  feedbackOutput: valueNode(""),
  feedbackStatus: valueNode(""),
  runFeedbackCopy: button(),
  runFeedbackDecision: valueNode("needs_changes"),
  runFeedbackRisk: valueNode("video_review"),
  runFeedbackTime: valueNode("12.5"),
  runFeedbackNote: valueNode("review state should survive polling"),
  runFeedbackOutput: valueNode(""),
  runFeedbackStatus: valueNode(""),
};

const productionState = {
  selectedWorkflowPath: "workflows/mock_text_to_slices.yaml",
  workflows: [{ path: "workflows/mock_text_to_slices.yaml", name: "mock_text_to_slices" }],
  run: {
    run_dir: "data/processed/runs/web_bridge/mock_text_to_slices",
    run_id: "mock_text_to_slices",
    manifest_path: "data/processed/runs/web_bridge/mock_text_to_slices/manifest.json",
  },
  review: {
    status: "passed",
    artifacts: {
      quality_report: "data/processed/runs/web_bridge/mock_text_to_slices/quality_report.json",
      review_report: "data/processed/runs/web_bridge/mock_text_to_slices/review_report.json",
    },
  },
};

let captured = null;
attachFeedbackHandlers(elements, {
  getCopyForLanguage: () => ({ feedbackCopied: "copied", feedbackCopyFallback: "fallback" }),
  productionState,
  onRunFeedbackCaptured: (event) => {
    captured = event;
  },
});

await elements.runFeedbackCopy.listeners.click();
const event = JSON.parse(elements.runFeedbackOutput.value);
console.log(JSON.stringify({ event, captured }));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    payload = json.loads(result.stdout)
    event = payload["event"]

    assert event["review_status"] == "passed"
    assert event["quality_report"].endswith("quality_report.json")
    assert event["review_report"].endswith("review_report.json")
    assert payload["captured"]["quality_report"] == event["quality_report"]
