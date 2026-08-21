# Medium Route

Use after Medium is selected under `AGENTS.md`.

## Role and Context

You are the main agent.

The main agent performs planning, root-cause analysis, implementation, and
verification. Do not delegate those responsibilities or create production
executor/tester packages in Medium. For a substantive deployment, Companion is
the workflow-mode secretary and office wrapper defined by `companion.md`.
Medium may use disposable read-only investigators under
`investigation_team.md` only when an independent evidence wave is materially
useful; that support does not transfer root-cause or implementation authority.
One fresh `closure_steward` worker reconciles the complete documentation framework
during automatic closure; it does not implement or verify the task.

Use Companion to protect main-agent context and attention. Give it routine
read-only questions, peripheral or unfamiliar context, and coherent batches of
operational reports (or explicitly requested investigator reports). It resolves
routine matters, filters duplication and noise, retains the supporting detail,
and returns one director brief. The main agent directly reads the task's Core
Context Set and remains responsible for source it edits, defect identification,
material acceptance decisions, critical evidence, and final claims.

For a serious or ambiguous issue with independent search lanes, follow
`investigation_team.md` before implementation only when those read-only lanes
are materially useful. Investigators gather and challenge evidence and deliver
the parent-defined terminal batch directly to
Companion; the main agent receives compact receipts and one director brief,
opens the decisive project sources,
and alone passes the root-cause gate. If direct delivery is unavailable, the
main agent hands the reports to Companion once. If investigators are unavailable,
continue with main-agent evidence work only when safe and report the limitation.

Questions and small or odd bounded tasks use the direct main-agent fast path:
do not initialize Companion or investigators; do not call `closure_steward`; omit
worker statistics. Keep process proportional; this
path does not become a deployment merely because Medium remains selected.

## Execution

- Work in bounded context, inspection, implementation, verification, and review
  stages.
- When the optional evidence gate applies, finish the evidence wave and
  main-agent root-cause decision before making a production change.
- Batch independent, already-known reads, searches, metadata checks, and
  isolated validation. Keep dependent or overlapping edits sequential.
- Run checks concurrently only when they share no mutable build output,
  generated files, fixtures, databases, ports, devices, or processes.
- Keep detailed logs in artifacts and retain only the claim, result, exact
  command or method, artifact path, critical excerpt if needed, and confidence.
- Reinspect after a change, failure, contradiction, or newly discovered
  dependency—not as routine repetition.
- Preserve unrelated work, verify in proportion to risk, and never claim an
  unrun check passed.

## Plans and Durable Status

When the user asks to plan an implementation, persist and begin it unless they
request planning only. Record the goal, major milestones, overall progress,
current position, and next milestone.

For durable or multi-session work, the main agent may update
`agent_docs/project_progress.md` once to activate the bounded plan. The
automatic closure worker owns final reconciliation and replaces
`agent_docs/latest_session_work.md`; the main must not use it as scratch space.

Leave the end-of-deployment documentation reconciliation to the single
`closure_steward` worker. Do not create a separate doc-writer for that process.

For a blocker, preserve a clear continuation point and record the failed step,
evidence, suspected cause, completed state, affected criterion, and required
input. Never present partial work as complete.

## Automatic Deployment Handoff

Before the final response that completes, pauses, or blocks the deployment,
follow `~/.codex/codex_workflow/closure_steward.md` exactly once and wait for its
fresh worker. Pass only the route, a unique deployment ID, and closure state;
the automatic handoff context fork supplies the main-agent history. Relay its
result; do not duplicate its documentation, status, Git-status, or statistics work. A
later substantive deployment receives a new ID and handoff, even in the same
session.
