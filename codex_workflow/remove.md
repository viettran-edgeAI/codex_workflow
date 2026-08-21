# Remove codex_workflow

Run this procedure only for the exact command:

    codex_workflow --remove

This is a destructive operation. It uses two phases: the first phase is a
read-only plan, and the second phase is allowed only after one clear second
confirmation from the user. Do not ask any other questions.

First run the lifecycle CLI without `--confirm`:

```text
python3 ~/.codex/codex_workflow/workflow.py \
  remove --project <project> --json
```

Use the equivalent `py -3.11` invocation and native paths on Windows. Report the
plan and explicitly warn that the confirmed phase will permanently delete:

- the workflow wrapper around the recognized project-level `AGENTS.md` (active
  or disabled), project personalization, and project workflow state;
- the workflow-managed region in the user-level `~/.codex/AGENTS.md` (the
  user file itself is deleted only when no unrelated content remains);
- workflow-owned keys in `~/.codex/config.toml`;
- worker TOMLs carrying a matching `codex-workflow-worker` ownership marker;
- every file under `~/.codex/codex_workflow/`, including source and update
  backups.

Also report that project-local instructions imported into the workflow entry
point are restored to the root `AGENTS.md`, and that workflow-owned marked
`.gitignore` rules are removed. `agent_docs/`, unrelated user-level
AGENTS/config content, and unrelated worker TOMLs are preserved. Do not claim
that anything has been removed during this first phase.

Then ask exactly one confirmation, for example:

    This will permanently remove codex_workflow and its workflow-owned files. Confirm removal? (yes/no)

If the reply is not an explicit affirmative, stop without running the second
phase. After an affirmative reply, run:

```text
python3 ~/.codex/codex_workflow/workflow.py \
  remove --project <project> --confirm --json
```

Report the final JSON result. If the command fails, reports an error, or rolls
back, do not describe the removal as successful.
