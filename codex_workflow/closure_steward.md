# Closure Steward

Use this automatic closure once after every substantive Medium or Heavy
deployment, immediately before the main agent's final response. It also applies
when a deployment pauses or blocks. Questions and small or odd bounded tasks on
the direct fast path do not use this handoff and produce no worker statistics.

Spawn one fresh worker with:

- `agent_type="closure_steward"`
- `task_name="closure_steward_<deployment_id>"`, where the suffix is a unique,
  lowercase, underscore-safe deployment identifier
- `fork_turns="200"`

Pass only the active route, deployment ID, and closure state (`complete`,
`paused`, or `blocked`). Do not summarize the session, build a task capsule, or
maintain a usage ledger. The automatic finite fork passes recent main-agent
turns so the worker inherits the deployment context while retaining its Luna
xhigh model; its TOML contains the full procedure.

The worker alone reconciles the complete `agent_docs/` framework, performs
compact closing checks, inspects and reports relevant Git status, and returns the
final handoff report and statistics table. It never stages or commits
automatically; any commit remains a separate, explicitly authorized user action.
Do not call a second documentation worker or duplicate these steps. Wait for the
worker, then relay its result. Create a fresh uniquely named worker for every
later substantive deployment in the same session.

If the worker cannot be created or is blocked, report that limitation. Do not
silently transfer the handoff to Companion or another role.
