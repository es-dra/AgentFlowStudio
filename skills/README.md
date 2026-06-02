# AgentFlow Studio Agent Skills

This directory contains agent-readable task contracts. They are not runtime
agents and do not call models by themselves. A skill tells an agent when to use
a AgentFlow Studio workflow, which inputs are required, which artifacts to read, and
which quality gates must pass before treating a result as usable.

Current recommended product skills:

- `short_highlight_package.skill.yaml`: video-only local-first short highlight
  package generation.
- `video_script_highlight_package.skill.yaml`: video plus script local-first
  short highlight package generation.
- `agentflow_production_handoff.skill.yaml`: production-side local-first
  structured handoff generation from a creative brief.

Agents should prefer these skill files over guessing from the full `workflows/`
directory.
