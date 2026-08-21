# Workflow Installation

Use this procedure only to install the already-bootstrapped workflow into the
current project. Do not manually copy or merge workflow files, and do not
modify or reinstall anything under `~/.codex/`.

Codex 0.147.0 or newer and Python 3.11 or newer are required. On Windows, use
the equivalent `py -3.11` invocation and native paths. Before any mutation,
run and require `"compatible": true`:

```text
python3 ~/.codex/codex_workflow/workflow.py check-compatibility --json
```

## Existing project installation

The CLI validates the current project's active `AGENTS.md` and disabled
`.codex_workflow_hidden_resources/.AGENTS.md` entry points before reporting an
existing installation. If any framework document is missing or still carries
its bootstrap marker, the CLI safely recreates only missing templates and
returns the required documentation recovery action; complete that action using
the procedure below. Otherwise, a valid active entry is reported as `already
enabled` and needs no action. A valid hidden entry is reported as `already
disabled`; then tell the user to run:

```text
codex_workflow --enable
```

If both entry points exist, or a recognized entry is stale, malformed, or
disagrees with its personalization resource, stop and report the CLI's recovery
instruction. Do not misreport those states as an ordinary disabled installation.

## Install the current project

Use the installed CLI:

```text
python3 ~/.codex/codex_workflow/workflow.py install \
  --project <project>
```

The command reads templates from the existing user-level bootstrap but changes
only the current project. It creates the project `AGENTS.md`, missing files in
the `agent_docs/` documentation scaffold, the hidden personalization and state
files, and other project-level assets. It imports an existing unrecognized
project `AGENTS.md` verbatim into the project-local marker region and adds a
marked workflow-owned block to `.gitignore` without changing unrelated rules.

It does not rewrite the shared user-level runtime, fixed definitions, user
instructions, source backup, or worker TOMLs under `~/.codex/`. Stop and report
the error if the initial user-level bootstrap is missing.

## Required documentation action

Every new installation or documentation-recovery result contains one required
`doc-writer` action. A healthy `already enabled` or `already disabled` no-op
does not. Spawn a returned action with
`agent_type="doc-writer"`, `task_name="install_docs"`, and
`fork_turns="none"`. Pass the project root and returned `files`, `created_files`,
`recovery_files`, `framework`, and `required_context_files` lists. Initialize
only documents in `files`: these are newly created or still-template-marked
recovery documents. Remove their bootstrap markers and preserve every other
existing document. Populate listed `project_structure.md`, `project_overview.md`,
and `project_core_tech.md` files with verified project evidence. If `files` is
empty, perform only a read-only framework completeness check. An empty project
is valid; explicitly record that project context was unavailable and leave
deployment status empty when no plan exists.

Installation is incomplete if the required worker cannot run or fails. Do not
silently perform its work in the main thread.
