<!-- codex-workflow-id: viettran-edgeAI/codex_workflow -->
<!-- codex-workflow-managed-start -->
# AGENTS.md

## Project Context


## Design Principles

- Keep modules cohesive, interfaces explicit, coupling minimal, and behavior
  testable, replaceable, and reusable.
- Define proportionate acceptance and verification before implementation. Keep
  related tests cohesive; never weaken coverage, assertions, or failure
  visibility to save time or tokens.
- Preserve unrelated user work and use verified facts in durable documentation.

Project personalization and project-local instructions are in protected regions
at the end of this file. They override conflicting workflow defaults, but not
higher-level instructions.

## Working State

- `deployment state`: planning or executing a broad, possibly multi-session
  deployment plan.
- `leaf state`: work outside that plan, including general questions and small,
  bounded edits or operations.

## Project Documentation

The durable project documents are under `agent_docs/`:

- `project_overview.md`: goals, architecture, workflow, and major decisions.
- `project_core_tech.md`: concise special technology or architecture notes.
- `project_structure.md`: layout, modules, components, and ownership.
- `project_progress.md`: goal, overall progress, current position, next milestone.
- `project_diary.md`: lasting decisions, discarded approaches, and lessons.
- `latest_session_work.md`: detailed handoff evidence and continuation point.
- Module-specific documents, when present.

`project_progress.md` and `latest_session_work.md` may be edited only in
`deployment state` or when the user explicitly requests it. The main agent owns
them during normal execution. During automatic deployment closure, the single
`closure_steward` worker owns reconciliation of the complete documentation
framework; no other worker participates in that closure update.

Keep raw logs, temporary reasoning, and short-lived checkpoints out of durable
documents. Never delete a main project document without warning the user and
receiving a second explicit confirmation.

## Route Selection

There are three routes:

- **Light**: leaf-state work. The main agent works directly; no subagents.
- **Medium**: deployment-state work performed by the main agent, with no
  delegated production executor or tester. Companion provides workflow-mode
  secretary and context support; an optional read-only evidence wave and the
  documentation-only Closure Steward handoff never own implementation,
  verification, or root-cause decisions. Read
  `~/.codex/codex_workflow/medium_route.md`.
- **Heavy**: deployment-state work orchestrated through specialized workers.
  Read `~/.codex/codex_workflow/heavy_route.md`.

Heavy requires the session's currently selected main agent to be
`gpt-5.6-sol` or `gpt-5.6-terra` with subagent support available. This is a
session-model requirement, not a persistent workflow setting. If the selected
model is ineligible or its subagent support is unavailable, do not initialize
Companion or any other worker; ask the user to switch the current session to
Sol or Terra. Never pin or rewrite the main model in `config.toml`.

The user selects the route for the session. If unspecified, use Light; do not
infer Medium or Heavy. Light implies `leaf state`; Medium and Heavy imply
`deployment state` only for substantive work. Their direct fast path remains
`leaf state`. Keep the selected route until the user changes it or the session
ends.

## Context Loading

- In Light, inspect only material needed for the current task.
- Before initializing deployment state, classify the request. Questions and
  small or odd bounded tasks use the direct main-agent fast path even when
  Medium or Heavy is selected: call no worker, including Companion and
  `closure_steward`, and produce no worker statistics.
- For every substantive Medium or Heavy deployment, read the selected route and
  `companion.md`, then initialize or reuse the single persistent Companion.
  Read `investigation_team.md` before a Heavy evidence wave or an explicitly
  requested Medium evidence wave.
- Give Companion the session goal, known constraints, escalation boundaries,
  and evidence format. It is the main agent's secretary and office wrapper: it
  completes routine read-only work, retains context, filters coherent batches of
  operational reports, and returns the director brief defined in its contract.
- Do not spend main-agent turns reading or re-diagnosing every routine report.
  When a worker batch exists, register one coherent batch with Companion and
  name it in the dispatch envelopes; dispatched workers deliver detailed
  terminal reports directly to it and return compact receipts to the main agent.
  Companion resolves routine matters and escalates only material knowledge or
  decisions in one director brief. If direct delivery is unavailable, hand
  Companion the compact batch once.
- The main agent directly reads task-critical project documentation, relevant
  source paths and contracts, and decisive failure evidence. It owns defect
  identification, root-cause adjudication, architecture, scope, and final claims.
- For serious or ambiguous issues with independent search lanes, Heavy may use
  read-only investigators under `investigation_team.md`; Medium may use them
  only as explicitly requested evidence support. Investigators gather evidence;
  Companion filters their terminal report batch; the main agent opens decisive
  evidence and adjudicates the root cause.
- Resolve stale or conflicting project status with targeted evidence. Load only
  relevant module documentation and avoid replaying raw logs, large diffs,
  directory listings, or complete source files into the main context.
- Before the final response that completes, pauses, or blocks each substantive
  Medium or Heavy deployment, run the automatic handoff defined in
  `closure_steward.md` exactly once. Its worker inherits recent main-agent
  context and performs the complete documentation-framework update. The
  handoff is not a user command.

## Platform Paths

Workflow documents use `/` as a platform-neutral separator. Translate paths to
the current operating system and shell when running filesystem commands.
<!-- codex-workflow-managed-end -->

<!-- codex-workflow-project-personalization-start -->
<!-- codex-workflow-project-personalization-end -->

<!-- codex-workflow-project-local-instructions-start -->
<!-- codex-workflow-project-local-instructions-end -->
