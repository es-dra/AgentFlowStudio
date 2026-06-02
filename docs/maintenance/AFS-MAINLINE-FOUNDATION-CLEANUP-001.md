# AFS Mainline Foundation Cleanup 001

Status: in progress

Date: 2026-06-03

## Goal

Consolidate AgentFlow Studio after the Production Memory Asset Loop MVP:

```text
merge current PR head
-> establish local and remote mainline
-> audit Loulan evidence branch
-> adopt generic positioning evidence
-> clean merged feature branches and worktrees
```

## Mainline Decision

`master` is the repository mainline. The root checkout should be returned to a
clean `master` state before new maintenance or feature work continues.

Current product framing:

```text
Product: memory-driven AI content production workbench
Architecture: Production Memory Architecture
Long-term vision: Memory OS
```

## Loulan Branch Audit

`codex/loulan-memory-pilot` exposed useful AFS requirements, but it is not the
AFS main product branch.

The branch contains many project-specific modules, commands, Web inspectors,
tests, examples, and handoff records. They are useful as evidence but should
not be merged as one product line.

Generic evidence adopted into mainline:

- product positioning reset;
- Production Memory Architecture naming;
- pressure-sample boundary;
- candidate-only Company knowledge-base feedback loop;
- reminder that tests, provider smoke, human acceptance, and business
  validation are separate claim levels.

Not adopted:

- project-specific content-production flow;
- project-specific Web inspectors;
- project-specific commands and contracts;
- local media, provider routes, private paths, or approval assumptions.

## Cleanup Policy

Merged feature branches can be removed locally and remotely after verifying
they are contained in `origin/master`.

Unmerged evidence branches should be archived before deletion.

No Company knowledge-base files are written by this cleanup.

No provider is called by this cleanup.

## Follow-Up

After this cleanup, the next discussion should focus on project redundancy and
maintainability improvements before cutting a stable testing baseline.
