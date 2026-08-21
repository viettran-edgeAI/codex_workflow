# Investigation Team

Use this shared contract for Heavy, and for an explicitly requested Medium
evidence wave, when a serious or ambiguous issue has a search space that can be
divided into independent read-only lanes. Companion remains the single
persistent secretary and office wrapper; investigators are disposable evidence
gatherers and never replace or multiply Companion. Medium keeps implementation
and verification in the main agent even when this evidence support is used.

## Main-Agent Grounding

Before dispatch, the main agent directly reads and understands the task's
**Core Context Set**:

- applicable instructions, user requirements, and acceptance boundaries;
- relevant foundational or module project documentation;
- the source path, interfaces, invariants, and public contracts that own the
  failing behavior;
- the critical reproduction, trace, log excerpt, or other failure evidence.

Companion may locate, organize, solve routine read-only questions about, and
retain this material, but its director brief is not a substitute for the main
agent's direct understanding of decisive context. Delegation may filter
operational noise; it must not transfer authority over task-critical project
decisions.

## Dispatch Gate

Create a team when multiple plausible causes, cross-system behavior, flaky or
concurrent failure, security or performance risk, dependency/version
uncertainty, missing reproduction, or external prior art makes parallel search
materially useful. Skip it for the direct fast path, a known root cause, or a
small bounded question. Do not create duplicate lanes merely to use capacity.

For each orthogonal lane, spawn one worker with `agent_type="investigator"`, a
unique `task_name="investigator_<deployment_id>_<lane>"`, and
`fork_turns="none"`. Supply the question or hypothesis, boundaries, known facts,
preferred authoritative sources, useful exact references, forbidden scope, and
the evidence format. Useful lanes include execution paths and state, failure
reproduction and logs, tests and races, dependency or version behavior,
security or performance boundaries, official documentation and source history,
and clearly labeled technical-forum or prior-art searches.

Select the useful lanes before dispatch and treat them as one investigation
wave. Register one batch ID, the expected investigator task names, and the
escalation boundary with Companion. Include Companion's canonical task name and
the batch ID in each investigator lane brief. Investigators deliver detailed
terminal evidence directly to Companion and return only a compact terminal
receipt to the main agent. Wait once for Companion's brief; do not analyze,
acknowledge, or answer each completion separately.

Use investigators when the installed agent type is available. Keep Companion's
live slot and one slot for Closure Steward within the fixed concurrency ceiling.
Investigator quantity is driven by independent search breadth, not token-cost
minimization.

## Evidence and Root-Cause Gate

Companion receives the parent-defined terminal batch without becoming its
manager. It deduplicates evidence, reconciles routine discrepancies, identifies
conflicts and missing proof, resolves bounded factual questions, and returns one
director brief. If direct investigator-to-Companion delivery is unavailable,
the main agent passes the compact reports and artifact references once after the
wave. The main agent retains access to every underlying report and reference.

The main agent owns adjudication. It reviews the director brief, compares only
material competing hypotheses, directly opens the decisive local sources and
evidence, and records whether the cause is confirmed, probable, or unresolved.
Do not package or implement a production fix until the main agent can state the
causal chain, affected contract, fix boundary, residual uncertainty, and
acceptance test. If that gate is not met, reuse the relevant investigator thread
with one compact evidence delta or run an explicitly diagnostic experiment; do
not launch another broad wave by default.

After the gate, Medium keeps implementation and verification in the main agent;
Heavy creates executor and tester packages. If later testing contradicts the
causal model, return the decision to the main agent and dispatch only the newly
needed focused lanes before revising the fix.
