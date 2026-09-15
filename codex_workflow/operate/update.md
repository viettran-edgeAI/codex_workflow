# Workflow Update

Supported command form:

    codex_workflow --update

Use Python 3.11 or newer. On Windows, use the equivalent `py -3.11`
invocation and native paths. Never clone the repository.

## Acquire the incoming instructions

The installed guide owns only release selection, download, and verification.
Stage the newest release with the installed runtime:

```text
python3 ~/.codex/codex_workflow/runtime/workflow.py stage-update --json
```

The command queries GitHub Releases, selects the highest non-draft SemVer
release containing both the universal ZIP and `SHA256SUMS`, includes
prereleases, verifies the checksum, and extracts the package safely.

Read the complete `operate/update.md` at the returned `guide` path. Then stop
following this installed copy and follow `Apply this release` in that incoming
guide. Do not apply the package before reading it.

## Apply this release

This section is authoritative only when read from the verified incoming
package.

### Upgrade from the preceding release

The first registry-aware release follows 1.1.17, whose installed guide delegates
directly to incoming runtime code. That runtime must return `input_required`
before writing anything when no project registry exists. Stop that turn and ask
the returned `prompt`. Even if project paths appear known from context, do not
infer, confirm, or write the list yourself. After the user replies in a later
turn, write that answer to the returned `input_file` using the returned format
and rerun the original update command.

Read `~/.codex/codex_workflow/install_state.json`. If it has no `projects`
field, this installation predates the project registry. Ask the user to provide
the absolute root path of every project where the workflow is installed,
including disabled projects. Do not scan the filesystem. Write the supplied
paths, one per line, to:

```text
~/.codex/codex_workflow/project_registry_migration.txt
```

Run the incoming runtime reported as `package` by the staging command:

```text
python3 <package>/runtime/workflow.py update \
  --source <package> --project <current-project> --json
```

The incoming runtime validates every registered project before changing any
file. It then updates the user-level runtime and all registered projects in one
compensating transaction. The one-time migration file is removed after a
successful update.

If a registered project was moved, deleted, or no longer contains a recognized
workflow entry point, stop and ask the user for the complete corrected project
list. Write it to a temporary file and rerun the incoming command with
`--projects-file <corrected-list>`. Treat that file as a replacement registry,
not as an incremental addition.

Expect the update to preserve unrelated Codex settings and skills, project
documents, personalization, project-local instructions, source backups, and
each project's enabled or disabled state. It removes obsolete workflow-owned
files and the retired workflow-owned `agent_docs/` `.gitignore` rule. A
user-owned `agent_docs/` ignore rule outside the managed block remains intact.

If a legacy project entry contains merged local edits, stop and review that
project. Pass only its extracted project-local instructions with
`--legacy-local-instructions <reviewed-file>`. Add `--allow-downgrade` only for
an explicitly approved downgrade.

Report the installed version, updated project paths, backup location, and any
failure. Never describe a partial or rolled-back update as successful.
