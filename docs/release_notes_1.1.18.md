# codex_workflow 1.1.18 — User-level project updates

Version 1.1.18 changes `codex_workflow --update` from a current-project
operation into one user-level operation for every installed project.

## Highlights

- Bootstrap and project install register canonical project roots in the shared
  installation state.
- One update validates, backs up, and updates the shared runtime and all
  registered projects in one compensating transaction.
- The first update from an older installation asks the user for the complete
  project list in a fresh reply; the agent must not infer or scan for it.
- Update acquisition now stages the verified package and hands control to that
  package's `operate/update.md`, allowing future releases to provide their own
  migration instructions.
- Installation documentation capsules now include an explicit
  `documentation_root`, avoiding ambiguous worker write paths.

## Compatibility

The 1.1.17 launcher can delegate directly to the incoming 1.1.18 runtime. That
runtime stops before writing, requests the one-time project list, and resumes
the update after the list is supplied.
