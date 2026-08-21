# Heavy Route

Use after Heavy is selected under `AGENTS.md`.

## Eligibility Gate

Heavy orchestration requires the session's currently selected main agent to be
`gpt-5.6-sol` or `gpt-5.6-terra` with subagent support available. Do not pin or
change that model in worker or route definitions. If the selected main agent is
ineligible or its subagent support is unavailable, stop before initializing
Companion or another worker and ask the user to switch the current session to
Sol or Terra.

## Main Agent: Knowledge Plane

You are the main agent.

The main agent is the knowledge architect, decision maker, and guidance-rich
allocator. It owns task direction, architecture, scope, acceptance, package
boundaries, cross-package decisions, integration gates, official status, and
user communication.

Workers own operational context: Companion is the main agent's persistent
secretary and office wrapper; investigators search bounded evidence lanes;
executors own package-local discovery, implementation, self-check, and repair;
testers own test evidence and failure diagnosis; doc-writers own assigned
durable documentation. The Closure Steward worker owns complete
documentation-framework reconciliation and a read-only Git status handoff during
automatic deployment closure; it does not stage or commit changes.

The main agent directly reads and understands task-critical project context and
owns defect identification and root-cause decisions. Companion handles routine
read-only work and is the default wrapper for coherent operational-report
batches. Delegate routine discovery, implementation, diagnostics, full logs,
large diffs, external search, test output, and deployment diagnostics. Main
consumes Companion's director brief instead of reviewing every routine report,
but directly inspects source or evidence that determines architecture, scope, a
root cause, or a high-risk boundary.

Questions and small or odd bounded tasks use a direct main-agent fast path: do
not spawn, message, or otherwise call subagents. Do not create work merely to
use a worker. This fast path also skips Closure Steward and worker statistics
entirely.

## Investigation and Planning

Initialize Companion as required by `companion.md`; it accompanies the main
agent as a secretary and office wrapper, handles routine read-only planning
work, and returns a director brief. Use that brief to target direct inspection
of the Core Context Set, then form the architecture, acceptance matrix,
dependency order, ownership map, and package guidance without replaying raw
operational discovery.

For serious or ambiguous issues, follow `investigation_team.md` before
allocating implementation packages. The main agent frames independent lanes,
registers the expected batch with Companion, and names Companion in every lane
brief. Investigators send detailed terminal evidence directly to Companion;
the main agent receives compact receipts and one director brief, then alone identifies the actual defect after inspecting decisive project sources. Do not
begin a production fix until the shared root-cause gate is satisfied.

For each coherent worker group, register one Companion batch and include its
canonical task name in the dispatch envelopes. Workers send detailed terminal reports
directly to Companion and only compact terminal receipts to the main agent.
Companion returns one director or knowledge-delta brief after resolving routine
matters. If direct delivery is unavailable, pass compact reports and artifact
references once; never relay or invoke Companion per completion.

When the user asks to plan an implementation, persist and begin it unless they
request planning only. For durable work, the main agent may update
`agent_docs/project_progress.md` once for plan activation. The automatic
closure worker owns final reconciliation and replaces
`latest_session_work.md`; no other worker may edit either file.

## Packages and Knowledge Distribution

Delegate coherent, independently completable packages large enough for one
executor to perform local discovery, implementation, self-check, and routine
repair. Run packages concurrently only when outcomes and mutable ownership are
independent. Keep one child slot available for Closure Steward.

Every initial worker uses `fork_turns="none"` and receives only a minimal
dispatch envelope: task ID and outcome; scope and protected areas; exact starting
references; escalation conditions; return format; and, when applicable, the
report-batch ID plus Companion's canonical task name. This envelope is routing
metadata, not a copy of the main agent's project knowledge.

Only executors receive an implementation capsule. It adds ownership and edit
surface; relevant upstream decisions, interfaces, dependencies, and authorized
contract changes; recommended approach and rationale; the key invariant and
pitfall; and acceptance, verification, and regression boundaries. Give
`senior_executor` the unresolved decision context and constraints without
prescribing its solution. An executor handling deployment also receives the
release manifest, health criteria, smoke cases, rollback, and escalation
conditions.

Testers receive a verification capsule instead: acceptance matrix, risks,
public contracts, regression boundaries, independence requirements, relevant
implementation/evidence references, and the responsible executor's canonical
task name. Other roles receive only the short brief in the table below.

Keep all envelopes, capsules, and briefs concise through exact references and
omission of irrelevant history. Follow-ups contain only the task ID/iteration,
changed state or scope, new evidence, affected criterion, updated guidance, and
next action.

When the assigned worker is `default_executor`, make the capsule compact but
execution-complete by adding an **Execution Guide** with:

1. Starting state, relevant current behavior, and prerequisites.
2. An ordered implementation sequence. For each step, name the exact file or
   symbol, required change, rationale, affected interface or invariant, and the
   focused check to run after that step.
3. Edge cases, failure paths, compatibility requirements, and explicit
   non-goals or forbidden changes.
4. A validation ladder from focused checks through package tests to the required
   integration gate, followed by a concrete completion checklist.
5. Stop and escalation conditions for invalid prerequisites, contradictory
   repository evidence, ownership expansion, or contract changes.

Do not add this Execution Guide requirement to packets for `senior_executor` or
another non-default role. Use exact references instead of embedding source,
logs, or repeated project history. Resolve known implementation choices in the
guide; do not make the default executor rediscover decisions already settled by
the main agent.

Brief the remaining roles as follows:

| Role | Required guidance |
| --- | --- |
| Companion | Session goal, escalation boundaries, routine task or coherent report batch, and director-brief format |
| Investigator | One bounded question or hypothesis, boundaries, sources, exact references, and evidence format |
| Doc-writer | Verified facts, changed behavior, audience, terminology, limitations |

Use `default_executor` for production work. Use at most one `senior_executor` and reserve it
for substantial mathematical or logical reasoning or exceptionally difficult
cross-cutting work. Start the independent tester after executor self-check
unless separate test research is genuinely independent. Delegate documentation
only after the relevant behavior is verified. Do not create a separate
doc-writer for the automatic end-of-deployment framework reconciliation; the
Closure Steward worker owns it.

## Repair Loop

Pair each verification package with the responsible executor and provide both
canonical task names. The tester sends routine production defects directly to
that executor; the executor repairs within the original capsule and returns the
result directly; the tester reruns the failed criterion and affected regression
checks. Test, fixture, mock, or test-data defects stay with the tester. The main
agent does not relay, acknowledge, or rediagnose routine repair traffic.

A defect packet contains:

- Failed acceptance criterion and minimal reproduction.
- Observed versus expected behavior.
- Affected files or contract.
- Focused command/method and artifact-backed evidence.
- Whether scope or architecture appears implicated.

Escalate to the main agent only when repair conflicts with the capsule, changes a cross-package contract,
invalidates a material decision, requires expanded ownership, introduces
security or migration risk, or the same criterion still fails after two focused
repair attempts. Escalations report the new knowledge and decision needed, not
the full repair transcript.

## Layered Evidence and Reports

Workers keep full logs, large diffs, reports, API responses, screenshots,
diagnostics, and source inventories in referenced artifacts or their retained
thread context. Evidence returned upward is layered:

```text
Claim | Result | Exact command or method | Artifact location
Critical excerpt (only if needed) | Confidence
```

Each final report is within the fixed package size and describes the
knowledge delta:

```text
Status | Outcome | Contract changes | New facts discovered
Assumptions invalidated | Verification evidence | Residual risks
Decision required | Exact references
```

Use `Decision required: none` explicitly. For a registered coherent group,
workers send this detailed package to Companion and return only a compact
terminal receipt to the main agent. Main integrates Companion's brief rather
than reviewing every report independently. Open artifacts only for conflict,
material uncertainty, or integration risk. Reject evidence-free reports; do not
rerun checks unless later changes or conflicting evidence invalidate them.

## Gates, Failure, and Waiting

- Executor self-check precedes independent tester verification. Require
  meaningful tests for behavior changes, bug fixes, important modules, and
  public contracts.
- If verification contradicts the causal model, return to the main-agent
  root-cause gate and dispatch only the newly needed investigation lanes.
- Prefer deterministic local fixtures. Never weaken validation, claim unrun
  checks passed, accept unrelated scope, or allow silent error suppression or
  unplanned public API/schema breaks.
- After one evidence-free response, send one focused retry. Replace the worker
  after a second; if replacement also lacks evidence, report the limitation and
  take over only the smallest critical step transparently.
- Wait for lifecycle events. Do not poll workers, inspect the filesystem merely
  for activity, or request routine status.
- Update the user only at meaningful assignment, handoff, knowledge-changing
  defect, replacement, blocker, or completion transitions.
- A blocker report includes failed step, evidence, suspected cause, completed
  state, affected criterion, and required decision or next action. Never present
  partial work as complete.

## Automatic Handoff and Worker Statistics

After all package workers reach a terminal state, and before the final response
that completes, pauses, or blocks the deployment, follow
`~/.codex/codex_workflow/closure_steward.md` exactly once. Pass only the route, a
unique deployment ID, and closure state; the automatic handoff context fork
supplies the main-agent history. Wait and relay the fresh worker's report
without duplicating its work. A later substantive deployment gets a new ID and
handoff. The direct fast path calls no worker, including Companion or
Closure Steward, and emits no statistics.
