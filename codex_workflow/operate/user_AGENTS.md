<!-- codex-workflow-user-id: viettran-edgeAI/codex_workflow -->
<!-- codex-workflow-version: 1.2.1 -->
<!-- codex-workflow-user-managed-start -->
# AGENTS.md

## Workflow Principles

- Keep modules cohesive, interfaces explicit, coupling minimal, and behavior
  testable, replaceable, and reusable.
- Define proportionate acceptance and verification before implementation. Never
  weaken coverage, assertions, or failure visibility to save time or tokens.
- Avoid unnecessary process or safeguards; preserve unrelated user work and use
  verified facts in durable documentation.

## Working State

- `deployment state`: planning or executing a broad, possibly multi-session
  deployment plan.
- `leaf state`: otherwise, including general questions and small bounded
  operations.

## Project Documentation

Use the durable project documents under `agent_docs/`:

- `project_overview.md`: goals, architecture, workflow, and major decisions.
- `project_core_tech.md`: concise special technology or architecture notes.
- `project_structure.md`: layout, modules, components, and ownership.
- `project_progress.md`: goal, overall progress, current position, next milestone.
- `project_diary.md`: distilled decisions, discarded approaches, mistakes, and
  reusable lessons.
- `latest_session_work.md`: detailed handoff evidence and continuation point.
- Module-specific documents, when present.

In deployment state, directly maintain `project_progress.md`,
`project_diary.md`, and `latest_session_work.md`. Before closure, record the
current goal and continuation state, concise lasting lessons, and the verified
deployment handoff in their canonical documents. Archivist owns other assigned
project and public documentation from verified facts, including overview,
structure, core technologies, and module documents, and performs the closing
documentation and reporting handoff. Require concise edits that remove stale or
redundant detail, assign module documents explicitly, and perform a direct
user-requested document edit outside deployment. During installation only, the
installer-assigned Archivist may initialize those three files when they are new
or still marked as templates.

Keep raw logs, temporary reasoning, and short-lived checkpoints out of durable
documents; give each fact one canonical home. Never delete a main project
document without warning. If the user has not explicitly requested or
authorized that deletion, obtain confirmation before deleting it.

## Route Selection

Select one route: **Light** works directly in leaf state without subagents;
**Medium** keeps planning, diagnosis, implementation, and verification with the
main agent and uses bounded read-only discovery, solution research, and
documentation support from `~/.codex/codex_workflow/medium_route.md`;
**Heavy** delegates bounded production, verification, documentation, context
exploration, and solution research under
`~/.codex/codex_workflow/heavy_route.md`.

Follow the user's route selection. Use Light when none is selected; do not infer
Medium or Heavy. Keep the route until the user changes it or the session ends.
Enter deployment state for Medium or Heavy only when the work is substantive.

When entering a substantive Medium or Heavy deployment, choose a unique ID
matching `[a-z0-9][a-z0-9_-]{0,63}`. Put
`<!-- codex-workflow-deployment-start: <deployment_id> -->`, with the placeholder
replaced by that ID, in the first commentary after entry. Emit it once and pass
the same ID to Archivist at closure.

## Rollout Efficiency

Batch independent reads, searches, metadata checks, and other known-input
operations. Keep dependencies and overlapping mutations sequential. In Medium
or Heavy, dispatch independent workers together, wait for the relevant set, and
synthesize their reports once. Workers return compact evidence-linked reports
through their parent-child result channel; Explorer owns bounded context
discovery.
For one bounded context task assigned to Explorer, start two independent
Explorer lanes together and compare both reports before deciding.
For one bounded problem assigned to Investigator, start three independent
Investigator lanes together and compare all three reports before deciding.

## Required Documentation Read

When entering a substantive Medium or Heavy deployment, if session-level
intake is not complete, directly read the complete current `agent_docs/`
framework exactly once: overview, core technology, structure, progress,
diary, latest session work, and every module-specific Markdown document.
This one direct read is shared across Medium and Heavy. Never repeat it later
in the session. Use retained context or assign two Explorers a bounded context
delta, module intake, or conflict check when detail or freshness matters.
Missing or unreadable required documents leave deployment entry incomplete;
report the intake blocker. In Light, read only the project documents needed
for the current task.

## Platform Paths

Interpret `/` as a platform-neutral separator and translate paths for the
current operating system and shell.

## Lifecycle Commands

When the user's trimmed message matches one of the following command forms,
read and follow the corresponding guide. Forms without placeholders must match
exactly.

- codex_workflow --install
  Guide:  ~/.codex/codex_workflow/operate/install.md.

- codex_workflow --update
  Guide:  ~/.codex/codex_workflow/operate/update.md.

- codex_workflow --check-update
  Guide:  ~/.codex/codex_workflow/operate/check_update.md.

- codex_workflow --remove
  Guide: ~/.codex/codex_workflow/operate/remove.md.
<!-- codex-workflow-user-managed-end -->
