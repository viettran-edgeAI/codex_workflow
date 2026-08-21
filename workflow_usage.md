# codex_workflow — Workflow Usage Guide

> This is the maintained user-facing overview. The lifecycle guides and installed
> CLI are authoritative for exact commands and safety behavior.

`codex_workflow` is a modular Codex workflow with explicit responsibility
boundaries, persistent project documentation, shared user-level runtime files,
and conservative lifecycle operations.

This guide is organized into five parts:

1. command prompts and route selection;
2. the installed-file map;
3. built-in definitions and project customization;
4. the shared investigation and Heavy execution model;
5. the component hierarchy and ownership model.

## Part 1 — Command prompts and everyday use

### First-time bootstrap

Open Codex from the project directory and send this prompt:

```text
Download and extract the latest `codex_workflow-<version>.zip` asset (not GitHub's Source code archive) from https://github.com/viettran-edgeAI/codex_workflow/releases. Verify it against `SHA256SUMS`, then read the bundled `codex_workflow/bootstrap.md` and follow it exactly.
```

The release package is a universal ZIP for Linux, macOS, and Windows. Its
installation guide invokes the bundled lifecycle CLI, which owns validation,
rendering, backups, project initialization, and rollback. After the first
installation, start a new Codex session so the newly installed user
instructions are loaded. Codex 0.147.0 or newer and Python 3.11 or newer are
required. The bootstrap, installation, and update guides require the user to run
the explicit compatibility preflight before mutation. The CLI exposes
`check-compatibility` for that purpose but does not implicitly run it inside a
mutating command; callers following another integration path must run the check
themselves. This is the workflow's tested subagent-support baseline.

The bootstrap installs the user-level workflow and the current project with the
release's built-in definitions. Project personalization remains an explicit follow-up
command. Bootstrap also adds a marked workflow-owned block to `.gitignore` and
removes a project-level `Codex_Workflow/` extraction directory
once the installation transaction succeeds. Bootstrap then requires one
`doc-writer` action to initialize new or still-template-marked `agent_docs/`
files, or perform a read-only completeness check when the framework is already
healthy. Installation is incomplete until that action succeeds. For listed
context documents, the worker must populate `project_structure.md`,
`project_overview.md`, and `project_core_tech.md` from verified project evidence.

### Exact command prompts

Send each command as its own prompt. The installed lifecycle CLI performs the
validated filesystem operation directly.

#### `codex_workflow --personal`

Interactively personalize the current project. The three supported areas are:

1. Frontend Project Profile, including a project-specific verification profile
   such as reduced frontend testing when that is an intentional decision;
2. Design Principles;
3. Additional Workflow Decisions.

Confirmed decisions are stored in the hidden project resource and materialized
inside the personalization marker in the project's workflow entry point. A
missing or invalid resource is only staged as a recovery proposal until
confirmation; cancellation changes no file. This command does not modify fixed
worker settings or the Project Documentation Framework.

#### `codex_workflow --install`

Install the workflow in the current project after the user-level workflow has
already been bootstrapped:

- creates or preserves the project `AGENTS.md` entry point;
- imports a pre-existing project `AGENTS.md` into the dedicated project-local
  region instead of semantically merging it;
- creates missing files in `agent_docs/` from the six project-document
  templates;
- invokes `doc-writer` to initialize new or still-template-marked documentation,
  while healthy existing installations are a no-op;
- requires listed `project_structure.md`, `project_overview.md`, and
  `project_core_tech.md` recovery or new files to be populated from verified
  project evidence;
- creates the default hidden personalization resource when missing;
- reuses the installed fixed user-level settings.

It does not reinstall or modify any user-level payload under `~/.codex/`, reset
existing project documents, or ask settings and personalization
questions. If the workflow already has an active or disabled project entry
point, the command first validates its state. A healthy active installation is
a no-op; a healthy disabled installation points to `codex_workflow --enable`.
If framework documents are missing or retain bootstrap markers after a failed
documentation action, rerunning `--install` recreates only missing templates
and returns the required recovery action again. Stale, malformed, or conflicted
entry points stop with an actionable error.

#### `codex_workflow --update`

Update the installed workflow and the recognized current project from a GitHub
Release asset. The command queries the GitHub Releases API, selects the latest
eligible semantic-versioned release with the matching ZIP and checksum,
downloads the asset, verifies it, and extracts it into a temporary directory.
It never clones or pulls the repository.

The update applies the incoming release's fixed definitions and regenerates
distributed worker TOMLs. It preserves
project personalization, project-local instructions, project documents,
unrelated Codex settings, source backups, the automatic-check preference, and
the project's enabled or disabled state. Projects on older workflow versions
are validated against their matching historical source backups. It stops on
marker drift, unavailable historical source, or legacy edits requiring a
one-time reviewed project-entry migration. Obsolete workflow-owned files and
worker roles are removed from the installed manifest.

#### `codex_workflow --check-update`

Run an explicit read-only release check. It always queries the available
installable releases, regardless of the automatic-check setting, and reports
every version newer than the installed one with a compact summary of each
release's notes. It does not download or change files.

#### `codex_workflow --remove`

Remove the installed workflow in two phases. The first invocation creates a
read-only destructive summary and warns the user. Only after one explicit
second confirmation does the lifecycle CLI remove the project workflow wrapper,
project workflow resource, user-managed workflow region, workflow-owned Codex
settings and workers, and the complete installed runtime including backups. It
restores the entry point's project-local instructions, removes marked
workflow-owned `.gitignore` rules, and preserves `agent_docs/` and unrelated
user-level content. A non-affirmative response performs no changes.

#### Automatic update check

The package default is disabled: `~/.codex/AGENTS.md` contains no session-start
check instruction, so new sessions make no automatic update-check call.

Send `codex_workflow --enable_auto_check_update` to explicitly enable the
session-start check. It updates only the independent preference and adds an
instruction that runs the read-only `auto-check-update` command once per new
session. When enabled, the command compares the installed version with the
highest usable GitHub Release and reports an available update; it stays quiet
when current. `codex_workflow --disable_auto_check_update` disables the setting
and removes that instruction. Both commands preserve unrelated user-level
content.
The former `--enable_auto_update` and `--disable_auto_update` prompts remain
compatibility aliases; no command automatically installs an update.

#### `codex_workflow --disable`

Disable the workflow for the current project by moving the active entry point:

```text
AGENTS.md -> .codex_workflow_hidden_resources/.AGENTS.md
```

The contents, personalization resource, project documents, and user-level
workflow remain intact. The operation is a safe no-op when the project is
already disabled.

#### `codex_workflow --enable`

Re-enable a disabled project by moving the entry point back:

```text
.codex_workflow_hidden_resources/.AGENTS.md -> AGENTS.md
```

This changes only the active/disabled entry-point state. It does not reapply
fixed definitions or personalization.

### Route selection and deployment closure

There are three execution routes:

- **Light route** — the default; the main agent works alone with minimal
  workflow overhead.
- **Medium route** — the main agent performs root-cause analysis,
  implementation, and verification without delegated production executor or
  tester packages. Companion acts as the workflow-mode secretary and office
  wrapper. An explicitly requested read-only evidence wave may assist, but it
  never owns implementation, verification, or the root-cause decision.
- **Heavy route** — a Sol or Terra main agent with subagent support orchestrates fixed
  worker subagents for larger deployment-state tasks. This is the current
  session's user-selected model; the workflow never pins the main model in
  persistent settings.

For ordinary questions and small tasks, no route command is needed. To select
a route for a task or plan, include one of these instructions in the prompt:

```text
use medium route. [task description]
use heavy route. [task description]
```

The selected route is session-scoped: it remains active until the user changes it
or the session ends. New sessions default to Light unless a route is selected
again. Each substantive Medium or Heavy deployment automatically creates a
workflow-owned documentation handoff before its final response. Its fresh Luna
xhigh worker receives the fixed finite handoff context and alone reconciles the
complete `agent_docs/` framework, reports read-only Git status and handoff
information, and returns the final three-column worker-statistics table. It does
not stage or commit automatically. No manual closure prompt, main-agent summary,
usage ledger, or second documentation worker is required. Questions and small or
odd bounded tasks use the direct worker-free path and emit no table.

## Part 2 — Installed-file map

The release ZIP contains only one top-level directory, `codex_workflow/`. It
does not contain the repository README, README images, development documents,
`.git/`, release scripts, or other repository-only files. On Windows, `~/.codex`
means the current user's profile directory and the platform's normal path
separator is used.

After installation, the runtime is distributed between the user environment
and the current project as follows:

```text
~/.codex/
├── AGENTS.md                              # user-level command interface
├── config.toml                            # existing Codex config; only workflow-owned keys are managed
├── agents/                                # all distributed workflow worker TOMLs
│   ├── default_executor.toml
│   ├── senior_executor.toml
│   ├── tester.toml
│   ├── doc-writer.toml
│   ├── companion.toml
│   ├── investigator.toml
│   └── closure_steward.toml
└── codex_workflow/
    ├── VERSION                             # installed workflow version
    ├── user_AGENTS.md                      # managed commands and optional-check placeholder
    ├── workflow.py                         # validated lifecycle CLI
    ├── runtime/                            # validation, rendering, release, and transaction modules
    ├── resources/                          # immutable package defaults
    │   ├── auto_check_update.md
    │   └── personalization.md
    ├── install_state.json                  # ownership, version, and automatic-check preference
    ├── heavy_route.md                      # Heavy-route orchestration rules
    ├── medium_route.md                     # Medium-route rules
    ├── companion.md                        # persistent secretary/office-wrapper contract
    ├── investigation_team.md               # Heavy or explicitly requested Medium evidence and root-cause gates
    ├── closure_steward.md                   # shared closure spawn contract
    ├── bootstrap.md                        # initial user/project bootstrap procedure
    ├── install.md                          # project-only installation procedure
    ├── update.md                           # Release-based update procedure
    ├── check_update.md                     # explicit read-only release check
    ├── remove.md                            # two-phase removal procedure
    ├── enable_auto_check_update.md         # enable automatic session check
    ├── disable_auto_check_update.md        # disable automatic session check
    ├── enable_auto_update.md               # legacy enable alias
    ├── disable_auto_update.md              # legacy disable alias
    ├── personalization_guide.md            # --personal procedure
    ├── disable.md                          # --disable procedure
    ├── enable.md                            # --enable procedure
    ├── templates/
    │   ├── AGENTS.md                       # project entry-point template
    │   ├── agents/*.toml                    # all distributed worker templates
    │   └── project_docs/*.md                # six Project Documentation templates
    ├── .source_backup/<version>/            # complete installed release source backup
    └── .backups/<old-version>-<timestamp>/ # update backups, created when needed

<project>/
├── AGENTS.md                               # active project workflow entry point
├── .gitignore                               # marked workflow-owned paths are ignored
├── agent_docs/
│   ├── project_overview.md
│   ├── project_core_tech.md
│   ├── project_structure.md
│   ├── project_progress.md
│   ├── project_diary.md
│   └── latest_session_work.md
└── .codex_workflow_hidden_resources/
    ├── personalization.md                  # project-scoped private resource
    ├── state.json                          # project entry-format and activation state
    └── .AGENTS.md                          # disabled entry point; mutually exclusive with root AGENTS.md
```

The last two project entry-point files are mutually exclusive: an enabled
project has `AGENTS.md`; a disabled project has the hidden `.AGENTS.md`. The
hidden directory is also where project personalization is kept so it is not
mistaken for ordinary project documentation.

The six files under `agent_docs/` have different ownership and purposes:

- `project_overview.md` — goals, architecture, workflow, and major decisions;
- `project_core_tech.md` — important technologies and architectural constraints;
- `project_structure.md` — layout, modules, ownership, and boundaries;
- `project_progress.md` — concise overall progress and current milestone;
- `project_diary.md` — durable decisions, discarded approaches, and lessons;
- `latest_session_work.md` — the latest deployment state, evidence, outcome,
  unfinished work when present, and continuation point.

## Part 3 — Built-in definitions and customization

Command prompts select an operation. The lifecycle CLI validates and
materializes all generated surfaces from their source resources.

### Fixed workflow definitions

There is no workflow settings file or installed tuning surface. Behavior lives
directly in the release files that own it: worker TOMLs own models and report
contracts, route documents own orchestration limits, and
`runtime/platform_settings.py` owns the Codex platform keys. Install and update
copy those definitions exactly.

The current built-ins are `default_executor`, `senior_executor`, `tester`,
`doc-writer`, `companion`, `investigator`, and `closure_steward`. The first
three are Heavy production/verification roles. `doc-writer` and Closure
Steward own documentation updates, while Companion and investigator provide
read-only workflow support. The default executor uses `xhigh`; Heavy permits
at most one senior executor; and the Codex child-worker ceiling is twenty.

`auto_check_update` is not a workflow setting. It is an independent boolean in
`install_state.json`, disabled on first bootstrap and changed only by its
dedicated enable/disable commands. Project personalization and activation state
remain separate.

All listed roles are fixed built-in definitions. Companion is the single
persistent secretary and office wrapper: it handles routine read-only work,
retains operational context, and filters coherent report batches. Multiple
investigator task names may use the one read-only investigator definition for
Heavy evidence lanes or an explicitly requested Medium evidence wave.

Bootstrap and update enable the documented multi-agent settings under `[agents]`
and `[features]`. They remove workflow-owned legacy V2 keys instead of
generating an undocumented feature gate.

When worker definitions or platform settings change, open a new Codex session
so the updated settings are loaded.

Changing a built-in definition or worker requires changing the package source,
tests, and release together. Installed retuning is unsupported.

### Tuning project personalization

The private source resource is:

```text
.codex_workflow_hidden_resources/personalization.md
```

It contains the confirmed Frontend Project Profile, Design Principles, and
Additional Workflow Decisions. Its decisions are materialized only inside the
marked personalization block in `AGENTS.md` (or the hidden entry point while
the project is disabled).

Do not edit its materialized marker directly. `codex_workflow --personal`
validates a complete candidate and atomically updates the resource and generated
region while preserving project-local instructions.

Do not put personalization in `agent_docs/`: those six files are durable
project context and are intentionally available to the normal workflow.

### Customizing routes and documentation

Advanced route changes belong in a maintained source package or fork, not in an
installed generated copy that update will replace:

```text
~/.codex/codex_workflow/heavy_route.md
~/.codex/codex_workflow/medium_route.md
~/.codex/codex_workflow/investigation_team.md
```

Possible customizations include:

- replacing `project_progress.md` with a dedicated codebase navigation or
  management tool for a very large repository;
- adapting the `closure_steward` worker instruction to the project's
  documentation or review practice while retaining its read-only Git handoff
  and keeping `closure_steward.md` as the spawn contract.

Keep the route's ownership boundaries, fixed worker limits, verification gates, and
single-worker automatic-closure ownership of the complete documentation
framework. After a source change, verify that the settings resource, route
contracts, and worker definitions still agree.

## Part 4 — Workflow-mode support and Heavy execution

Medium keeps planning, root-cause analysis, implementation, and verification in
the main agent. Its workflow mode activates one persistent Companion
secretary/office wrapper for routine read-only context work and report
filtering; it does not create delegated production packages. If the user
explicitly requests independent evidence lanes, read-only investigators may
assist, but the main agent still opens decisive evidence and owns the root-cause
decision. Heavy adds the delegated production and testing packages after that
gate.

The Heavy route is an orchestrated deployment-state workflow. It is selected
explicitly by the user; Light remains the default for small tasks. The Heavy
route does not mean that every prompt must spawn workers: common questions and
small tasks use a direct main-agent fast path and must not call subagents. When
that fast path calls no subagent, its final response also omits the worker
statistics table.

### Roles and ownership

The fixed role set is:

| Role | Responsibility | Can edit project source? |
| --- | --- | --- |
| Main agent | Knowledge architect: chooses scope and architecture, distributes guidance, integrates knowledge, and reviews decision-critical boundaries | Only for exceptional scoped takeover, not routine Heavy implementation |
| `default_executor` | Package discovery, production implementation, self-check, and routine repair | Yes, within its work package |
| `senior_executor` | Complex core reasoning or exceptionally difficult cross-cutting implementation | Yes, within its work package; fixed to at most one instance |
| `tester` | Independent focused tests and failure analysis | Test/fixture scope; production defects return to the executor |
| `doc-writer` | Assigned documentation during implementation and required installation initialization; not automatic deployment closure | Documentation scope; installation may authorize listed new or still-template-marked recovery files |
| Companion | Single persistent secretary and office wrapper that solves routine read-only tasks, retains operational context, filters coherent report batches, and returns director briefs | No |
| `investigator` | Disposable Luna leaf agent for one bounded code, evidence, dependency, documentation, log, or external-solution lane | No |
| `closure_steward` | Inherited-context reconciliation of the complete documentation framework, read-only Git status/handoff, and statistics | `agent_docs/` plus read-only Git inspection during automatic closure; no automatic staging or commit |

The role names are stable while their model bindings live only in the worker
TOMLs. The package settings, route contracts, and worker definitions jointly
encode the fixed role list and limits; no route block is generated.

### Context loading and work-package flow

When Heavy is selected for a deployment-state task, the main agent:

1. reads the project entry point, route instructions, and task-critical project
   documentation, source paths, contracts, and failure evidence directly;
2. initializes one read-only Companion secretary/office wrapper and asks it to
   solve routine planning work and filter wider operational context into a
   director brief;
3. for a serious or ambiguous issue, dispatches orthogonal read-only
   investigator lanes under the shared investigation contract;
4. registers their terminal batch with Companion; investigators deliver detailed
   reports there directly while the main receives compact receipts and one
   filtered director brief, then opens decisive sources and identifies the
   actual defect through the main-owned root-cause gate;
5. forms the architecture, bounded plan, acceptance matrix, ownership,
   dependencies, and verification gates without replaying raw discovery;
6. sends only the role-specific package needed by each worker.

Every worker gets a minimal dispatch envelope containing identity, outcome,
scope, starting references, escalation conditions, and return routing. Only
executors receive the main agent's implementation knowledge: relevant project
context, decisions, interfaces, dependencies, recommendation and rationale,
invariants, pitfalls, and acceptance boundaries. `senior_executor` receives the
unresolved decision context without a prescribed solution. Testers receive a
verification capsule containing the acceptance matrix, risks, public contracts,
regression boundaries, evidence references, and repair counterpart. Companion,
investigators, and doc-writers receive short role briefs rather than project-wide
knowledge capsules. Final reports use exact references and describe knowledge
changes rather than file activity.

The normal implementation and verification loop is:

```text
User selects Heavy route
        │
        ▼
Companion solves routine planning work and returns a director brief
        │
        ▼
Main reads the Core Context Set and frames independent search lanes
        │
        ▼
Investigator swarm tests hypotheses and sends terminal evidence to Companion
        │
        ▼
Companion filters and reconciles the coherent report batch
        │
        ▼
Main inspects decisive sources and passes the root-cause gate
        │
        ▼
Main forms architecture and distributes guidance-rich package(s)
        │
        ▼
Executor implements one coherent increment and self-validates
        │
        ▼
Tester independently runs focused checks when testing is warranted
        │
        ├── routine defect ──► direct executor repair ─► tester recheck
        ├── proof ─────────► compact knowledge report
        └── decision defect ─► main agent re-scopes or decides
        │
        ▼
Companion resolves routine report traffic and retains material knowledge deltas
        │
        ▼
Main integrates verified package outcomes
        │
        ▼
Fresh Luna xhigh worker automatically closes the deployment before the final response
```

The tester and responsible executor are identified by canonical task name and
exchange routine defect and repair packets directly, as in the previous Heavy
coordination design. The main agent is involved only for capsule conflict,
cross-package contract change, an invalidated decision, expanded ownership,
security or migration risk, or repeated failure. Test and fixture defects stay
with the tester.

Workers keep raw logs, large diffs, reports, responses, and diagnostics in
artifacts or retained thread context. Upward reports give the outcome, contract
changes, new facts, invalidated assumptions, verification reference, residual
risk, decision required, and exact evidence location. The main agent may accept
routine operational proof without reopening its artifact, but it directly
inspects any project source or evidence that determines the root cause,
architecture, scope, or another high-risk decision.

### Concurrency and communication controls

The fixed platform and route definitions permit at most twenty concurrent child
workers and at most one `senior_executor` instance. Companion is a persistent
workflow companion rather than a production task worker, but its live thread
consumes capacity. Investigator quantity follows useful independent search
breadth rather than token-cost minimization and is a Heavy concern unless
Medium evidence support is explicitly requested. Both routes keep one
child-agent slot available for the fresh Closure Steward worker and must not
exceed the fixed role or worker limits.

Worker communication is event-driven and knowledge-aware. Named executor-tester
pairs exchange routine repair packets directly. For a parent-registered report
batch, workers send their detailed terminal packages directly to Companion and
only compact receipts to the main agent. A worker that returns no concrete
evidence gets one short retry; repeated evidence-free work triggers replacement
or a narrowly scoped, explicit main-agent takeover.

Task workers must not edit Git state or the shared status documents. Coherent
groups of routine worker reports flow directly into Companion's office wrapper
before main-agent integration; a single parent-to-Companion handoff is the
fallback when direct delivery is unavailable. Decision escalations and decisive
evidence remain available to the main agent. During
automatic closure, `closure_steward` alone reconciles the complete documentation
framework and reports Git status/handoff; it does not invoke another
documentation worker or mutate Git state. Companion and investigators remain
read-only. Companion is persistent and secretarial; investigators are disposable
leaf workers and do not direct one another or decide the root cause.

### Cross-session continuity

`project_progress.md` carries only the goal, overall progress, current position,
and next milestone. `latest_session_work.md` carries the most recent deployment
outcome, verification, blockers, and exact continuation point. A completed
deployment remains recorded concisely instead of clearing both files.

Before each substantive Medium or Heavy deployment returns its final response,
the route automatically creates a fresh, uniquely named `closure_steward` worker
with the handoff contract's finite context fork. This preserves its Luna xhigh
model while inheriting recent main-agent context. Without a parent-built capsule
or usage ledger, it reconciles every core and module-specific
`agent_docs/` file against verified deployment facts, performs compact closing
checks, reports Git status and any commit decision still requiring explicit user
authorization, and returns the final report. It never stages or commits
automatically. The report ends
with exactly three statistics columns:
`Worker name`, `Quantity` (distinct task names), and `Number of calls`
(turn-starting assignments and follow-ups). Companion has no closure
responsibility. Direct questions and small or odd bounded tasks create no
worker, handoff, or statistics table.

## Part 5 — Component hierarchy and ownership

The original design grouped the system into five logical blocks across two
geographical levels. That model remains useful, but some paths need a precise
distinction: `agent_docs/` is project documentation, while personalization is
private under `.codex_workflow_hidden_resources/`; worker TOMLs are materialized
runtime definitions, while `install_state.json` tracks lifecycle ownership,
version, and the independent automatic-check preference.

The five blocks are:

### 1. Workflow runtime — user level

Location: `~/.codex/`

- `~/.codex/agents/` contains all distributed worker TOMLs. The fixed role set
  is `default_executor`, `senior_executor`, `tester`, `doc-writer`,
  `companion`, `investigator`, and `closure_steward`.
- `companion.toml` gives the persistent Luna Companion a 1,050,000-token context
  window with automatic compaction at 900,000 tokens; the override is scoped to
  that role.
- `investigator.toml` defines the disposable read-only Luna xhigh leaf role used
  by Heavy, or by an explicitly requested Medium evidence wave.
- `~/.codex/codex_workflow/heavy_route.md` defines Heavy orchestration,
  delegation, limits, repair loops, and ownership.
- `~/.codex/codex_workflow/medium_route.md` defines main-agent execution with
  Companion workflow support, optional read-only evidence, and documentation
  closure; it does not delegate production implementation or verification.
- `~/.codex/codex_workflow/companion.md` defines the read-only Companion
  secretary/office wrapper's lifecycle, routine-task boundary, report-filtering
  role, memory, and director-brief contracts.
- `~/.codex/codex_workflow/investigation_team.md` defines the shared dispatch,
  evidence, main-agent context, and root-cause gates.
- `~/.codex/codex_workflow/closure_steward.md` defines the shared spawn contract;
  `closure_steward.toml` contains the complete handoff procedure.

This block is the reusable execution machinery. It is shared by projects and
does not contain project-specific decisions.

### 2. Workflow integration — project level

Location: the current project directory

- `AGENTS.md` is the active project entry point and contains the workflow
  instructions materialized for this project.
- `agent_docs/` contains the six-document Project Documentation Framework.
- `.codex_workflow_hidden_resources/.AGENTS.md` is the same entry point in its
  disabled state and must not coexist with root `AGENTS.md`.

This block connects the shared runtime to one project. Its project documents
are durable context, not private configuration.

### 3. Fixed definitions — user level

The release-owned surfaces are:

- `~/.codex/agents/*.toml`: materialized definitions for all distributed workers;
- `~/.codex/config.toml`: workflow-owned Codex platform settings, merged into
  the user's existing configuration without replacing unrelated settings;
- `~/.codex/codex_workflow/heavy_route.md` and the other contracts: orchestration
  limits and role interaction rules;
- `~/.codex/codex_workflow/templates/agents/`: all distributed worker
  templates, with model bindings isolated inside their semantic role files.

No aggregate workflow-settings document is generated. Update replaces these
release-owned definitions and carries forward the independent automatic-check
preference from `install_state.json`.

### 4. Personalization — project level

Private resource:

```text
.codex_workflow_hidden_resources/personalization.md
```

It contains the confirmed project-scoped decisions:

1. **Frontend Project Profile** — for example, a deliberate reduced frontend
   verification profile;
2. **Design Principles** — project-specific design and engineering rules;
3. **Additional Workflow Decisions** — other confirmed project instructions.

The resource is intentionally hidden from ordinary project context. Its
effective instructions are materialized between the personalization markers
in `AGENTS.md` or in the hidden disabled entry point. It is not stored in
`agent_docs/`, and `agent_docs/` should not be used as a substitute for it.

### 5. Guidance and lifecycle control — user level

Location: `~/.codex/codex_workflow/`

- `user_AGENTS.md` contains the workflow marker, installed version marker,
  optional-check placeholder, and exact command prompts for
  `--install`, `--update`, `--remove`, `--enable_auto_check_update`,
  `--disable_auto_check_update`, `--personal`, `--disable`, and
  `--enable`, plus the former automatic-check naming aliases.
- `bootstrap.md`, `install.md`, and `personalization_guide.md` describe initial
  bootstrap, project installation, and personalization.
- `update.md`, `disable.md`, and `enable.md` describe update and activation
  lifecycle operations.
- `remove.md` describes the destructive two-phase removal procedure.
- `enable_auto_check_update.md` and `disable_auto_check_update.md` describe the
  explicit update-check controls; `resources/auto_check_update.md` supplies the
  optional session instruction. `enable_auto_update.md` and
  `disable_auto_update.md` retain the former names as compatibility aliases.
- `workflow.py` and `runtime/` implement validated lifecycle operations.
- `VERSION` identifies the installed workflow version.
- `templates/` stores the project entry-point, worker, and project-document
  templates used for installation and update.
- `.source_backup/` keeps a complete release source copy for repair and
  recovery; update-time `.backups/` preserve replaced installed state.

This block is the command and lifecycle control plane. Guides define intent and
the runtime performs deterministic mutations. It is not project context or the
worker execution layer.

These five blocks are logical ownership boundaries, not five disjoint
directories. For example, `~/.codex/codex_workflow/` hosts routes, guidance,
fixed definitions, templates, and backups. The distinction is about who owns the
data and how it is consumed:

```text
User level:    shared runtime + fixed definitions + lifecycle guidance
                    │
                    │ materialized into the current project
                    ▼
Project level: entry point + six durable documents + private personalization
```
