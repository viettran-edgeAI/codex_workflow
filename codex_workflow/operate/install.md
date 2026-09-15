# Workflow Installation

Use this procedure only to install the already-bootstrapped workflow into the
current project. Do not manually copy or merge workflow files, and do not
modify or reinstall anything under `~/.codex/`.

Use Python 3.11 or newer. On Windows, use the equivalent `py -3.11` invocation
and native paths.

## Existing project installation

Let the CLI validate the current project's active `AGENTS.md` and disabled
`.codex_workflow_hidden_resources/.AGENTS.md` entry points before reporting an
existing installation. Expect it to apply pending repairs before reporting a
no-op when the project has a missing or stale state file, a recoverable missing
personalization resource, missing or stale workflow-owned `.gitignore` rules,
or leftover package staging. A repair removes the retired workflow-owned
`agent_docs/` ignore rule so project documentation can be tracked. If any
framework document is missing or still carries its bootstrap marker, let the
CLI recreate only missing templates and return the required documentation
recovery action; complete that action
using the procedure below. Accept an empty documentation `files` list when the
repair still applies non-document mutations. Treat a valid active entry
reported as `already enabled` as complete. For a valid hidden entry reported as
`already disabled`, tell the user to run:

```text
codex_workflow --enable
```

If both entry points exist, or a recognized entry is stale, malformed, or
disagrees with its personalization resource, stop and report the CLI's recovery
instruction. Do not misreport those states as an ordinary disabled installation.

## Install the current project

Use the installed CLI:

```text
python3 ~/.codex/codex_workflow/runtime/workflow.py install \
  --project <project>
```

Use the command to read templates from the existing user-level bootstrap and
change only the current project. Expect it to create the project `AGENTS.md`,
missing files in the `agent_docs/` documentation scaffold, hidden
personalization and state files, and other project-level assets. Preserve an
existing unrecognized project `AGENTS.md` through its verbatim import into the
project-local marker region, and preserve unrelated `.gitignore` rules when the
command adds its marked workflow-owned block. That block ignores only the
generated `AGENTS.md` wrapper and `.codex_workflow_hidden_resources/`; it must
not ignore `agent_docs/`.

The command also registers the canonical project root in the user-level
installation state so one future `codex_workflow --update` can update every
installed project.

Keep the shared user-level runtime, fixed definitions, user instructions,
source backup, and worker TOMLs under `~/.codex/` unchanged. Stop and report the
error if the initial user-level bootstrap is missing.

## Required documentation action

For every new installation or documentation-recovery result, run the required
`archivist` action. Skip it for a healthy `already enabled` or `already
disabled` no-op. Spawn the returned action with
`agent_type="archivist"`, `task_name="install_docs"`, and
`fork_turns="none"`. Use Task ID `install_docs` and the Documentation Context +
Audience, Documentation Task + Goal, and Main-Agent Documentation Guidance
capsule. Pass the project root and returned `documentation_root`, `files`,
`created_files`, `recovery_files`, `framework`, and `required_context_files`
lists. Initialize
only documents in `files` under `documentation_root`: these are newly created
or still-template-marked recovery documents. Remove their bootstrap markers
and preserve every other existing document. Populate listed
`project_structure.md`, `project_overview.md`, and `project_core_tech.md` files
with verified project evidence. If `files` is empty, perform only a read-only
framework completeness check. An empty project is valid; explicitly record
that project context was unavailable and leave deployment status empty when no
plan exists.

Treat installation as incomplete if the required worker cannot run or fails.
Do not silently perform its work in the main thread.
