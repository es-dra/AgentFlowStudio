from __future__ import annotations

from html import escape

from narratostudio.posterflow.schemas import (
    NextRoundPrompt,
    PosterBrief,
    PosterCandidatesManifest,
    PosterFeedbackSignalLog,
    PosterMemoryCandidates,
    PosterPlan,
    PosterPreferenceProfile,
)


def render_poster_report(
    brief: PosterBrief,
    candidates: PosterCandidatesManifest,
    feedback: PosterFeedbackSignalLog,
    memory: PosterMemoryCandidates,
    profile: PosterPreferenceProfile,
    next_prompt: NextRoundPrompt,
) -> str:
    return "\n".join(
        [
            "# PosterFlow Memory Demo Report",
            "",
            "## Run Summary",
            f"- Project ID: {brief.project_id}",
            f"- Theme: {brief.theme}",
            "- Provider Mode: remote",
            "- Memory Runtime: not implemented",
            "",
            "## Candidates",
            *[f"- {item.candidate_id}: {item.image_path}" for item in candidates.candidates],
            "",
            "## Feedback",
            *[f"- {item.candidate_id}: {item.decision} ({', '.join(item.reason_tags)})" for item in feedback.signals],
            "",
            "## Memory Candidates",
            *[f"- {item.memory_candidate_id}: {item.claim}" for item in memory.candidates],
            "",
            "## Preference Profile",
            *[f"- {item}" for item in profile.visual_preferences + profile.negative_visual_preferences],
            "",
            "## Next Round Prompt",
            next_prompt.composed_positive_prompt,
            "",
        ]
    )


def render_poster_preview(
    brief: PosterBrief,
    plan: PosterPlan,
    candidates: PosterCandidatesManifest,
    feedback: PosterFeedbackSignalLog,
    memory: PosterMemoryCandidates,
    profile: PosterPreferenceProfile,
    next_prompt: NextRoundPrompt,
) -> str:
    cards = "\n".join(
        f"""
        <article class="candidate">
          <img src="{escape(candidate.image_path)}" alt="{escape(candidate.candidate_id)}">
          <h2>{escape(candidate.candidate_id)}</h2>
          <p>{escape(_feedback_for(candidate.candidate_id, feedback))}</p>
        </article>
        """
        for candidate in candidates.candidates
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PosterFlow Memory Demo</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #f6f5f2; color: #1d2525; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    header {{ display: grid; gap: 8px; margin-bottom: 24px; }}
    h1 {{ font-size: 28px; margin: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
    .candidate, section {{ background: #fff; border: 1px solid #d9d6cf; border-radius: 8px; padding: 14px; }}
    img {{ width: 100%; aspect-ratio: 2 / 3; object-fit: cover; border-radius: 6px; background: #ece8df; }}
    h2 {{ font-size: 16px; margin: 12px 0 6px; }}
    code, pre {{ white-space: pre-wrap; overflow-wrap: anywhere; }}
    .stack {{ display: grid; gap: 16px; margin-top: 16px; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>PosterFlow Memory Demo</h1>
      <div>{escape(brief.project_id)} · {escape(brief.platform)} · {escape(brief.theme)}</div>
      <p>{escape(plan.design_intent)}</p>
    </header>
    <div class="grid">{cards}</div>
    <div class="stack">
      <section><h2>Memory Candidates</h2><pre>{escape(_memory_text(memory))}</pre></section>
      <section><h2>Preference Profile</h2><pre>{escape(_profile_text(profile))}</pre></section>
      <section><h2>Next Round Prompt</h2><pre>{escape(next_prompt.composed_positive_prompt)}</pre></section>
    </div>
  </main>
</body>
</html>
"""


def _feedback_for(candidate_id: str, feedback: PosterFeedbackSignalLog) -> str:
    for item in feedback.signals:
        if item.candidate_id == candidate_id:
            return f"{item.decision}: {', '.join(item.reason_tags)}"
    return "pending"


def _memory_text(memory: PosterMemoryCandidates) -> str:
    return "\n".join(f"{item.memory_candidate_id}: {item.claim}" for item in memory.candidates)


def _profile_text(profile: PosterPreferenceProfile) -> str:
    lines = profile.visual_preferences + profile.negative_visual_preferences + profile.prompt_rules
    return "\n".join(lines)
