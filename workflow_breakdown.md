# codex_workflow — Architecture and Operational Analysis

This document is a focused analysis of the design lessons behind
`codex_workflow`, followed by its agent roles, installed topology, lifecycle
commands, deployment token reporting, and release boundaries. It analyzes the source
package represented by `codex_workflow/`; it is not an additional executable
instruction surface.

For exact behavior, use the source that owns the relevant contract:

- `codex_workflow/AGENTS.md` for shared project behavior, route selection, and
  first deployment-state entry;
- `codex_workflow/medium_route.md` and `codex_workflow/heavy_route.md` for
  route-specific orchestration;
- `codex_workflow/agents/*.toml` for worker models, permissions, and role
  boundaries;
- `codex_workflow/archivist.md` for documentation assignments and deployment
  closure;
- `codex_workflow/operate/*.md` for user-facing lifecycle procedures;
- `codex_workflow/runtime/*.py` for deterministic lifecycle mutations; and
- `codex_workflow/skills/deployment-token-report/` for deployment usage
  reporting.

This revision was reviewed against packaged version `1.1.18`, read from
`codex_workflow/operate/VERSION`. Version markers, package validation, and
release tests prevent that value from drifting from the distributed user
instruction block.

## 0. A Deep Dive into Codex Orchestration

We can't simply tell the main agent:

> "Hey Sol, make a plan for this task and delegate the implementation to Luna subagents."

There are several aspects that need to be balanced carefully.

### 1.Main-agent control vs. context savings and task completion

- How much of the codebase should the main agent load itself?
- Should it personally review the output of tests performed by testers?
- Should it inspect logs and reports to understand what the subagents are doing, or let them work independently and simply accept their final results?

### 2.Main-agent rollouts vs. worker rollouts

In Codex, every time a model stops to call a tool, coordinate a subagent, etc., it consumes another rollout.
And each rollout reloads the model's entire context, although most of that will usually be cached input tokens.
So every time the main agent calls or coordinates a worker, that also costs a main-agent rollout.

This means that overly fine-grained coordination with workers, repeatedly retrieving context reports from the Companion, and similar operations can sometimes become counterproductive from a token-cost perspective.

You may successfully move some work to a worker, but in exchange, the main agent has to reload its entire context.
In practice, you're basically trading **cached input tokens from the main agent** for **input/output tokens from workers**.
And the main agent is roughly **40x/100x more expensive than the workers** depending on whether you're using Sol/Astra vs. Luna.

==> Thats also why the Companion Is Initialized Immediately after Deployment State Entry

Creating the Companion also costs a Main Agent rollout, so the workflow does it at the first
`deployment state` entry while the Main Agent's context is still small and cheaper to replay.
That persistent Companion is then reused; Light and the direct fast path skip this overhead.

This is why I apply **batching guidelines** to reduce the number of main-agent rollouts. I'll explain them later in the `codex_workflow` design section.
AI isn't going to naturally balance all of these trade-offs for you. You have to experiment, measure, observe, and optimize the workflow yourself.

That's also why I added end-of-session token statistics through the built-in workflow skill:

![End-of-session token report](token_report.png)

---

### Why Not Just Ask Codex to Design an Efficient Orchestration Framework?

Why not simply ask Codex to propose an orchestration architecture that is both efficient and actually feasible on the platform?
There are several problems.

#### 1. Perspective and awareness

There are three different levels of perspective:

- the workflow designer
- the main agent
- the workers

The AI doesn't naturally distinguish these perspectives correctly when writing instructions.
When you ask it to write the instructions itself, it tends to write them from the **workflow designer's perspective**.
For example, an older revision of `archivist.toml` contained instructions like:

> “For bootstrap or installation, initialize only the listed new or still-template-marked documents... This initialization authority ends with that assignment.”

That's written from the perspective of the workflow designer.
But the worker — the Archivist in this case — doesn't actually know the surrounding context implied by those instructions.

The instruction needs to be written from the worker's point of view and provide the necessary context, such as explaining the install/bootstrap process and the main task being assigned to it.

#### 2. "Optimization" has no fixed finish line

If you tell the Codex:

> "Optimize this orchestration workflow to minimize cost while still ensuring that tasks can be completed reliably."

and then give it a few test projects so it can repeatedly evaluate and improve itself, it will keep optimizing endlessly.

Eventually, the workflow starts becoming **over-optimized for the test cases**, while the orchestration framework becomes increasingly rigid and formulaic.
I've already gone through this. At one point, it proposed this design:

- `wave_barrier` as an LLM lifecycle parent

The idea was to introduce an intermediary subagent.

The Main Agent would send it the manifest for an entire wave. The barrier would spawn the workers, absorb their completion wakeups, wait for the entire child tree to finish, and then return a single terminal bundle to the Main Agent.

In theory, this would reduce the number of times the Main Agent gets woken up.

But in practice, it added another layer of LLM orchestration, made the topology more complicated, forced the architecture around explicit waves, and wasn't even feasible on the platform because `wave_barrier` couldn't directly communicate with those workers.

Eventually, I had to tear the whole thing down myself and return to a much simpler design philosophy:

**Describe the workers, let the Main Agent control the orchestration itself, and provide a set of optimization guidelines.**

#### 3. Accumulated patches in instructions

Another issue is the accumulation of revisions.
For example, when an old guideline becomes obsolete, the AI tends to add something like:
> "Do not use XYZ."
instead of restructuring the instructions and removing the outdated part entirely.
Over time, these patches accumulate.
There are plenty of other small problems like this that I don't remember anymore, but these are the major ones that stood out.

### The Rigidity Trap After Hundreds of Trial Runs

After hundreds of trial runs and refinement passes, a subtler failure mode
appears. Every failed experiment creates pressure to add another rule, like:

- always investigate before planning;
- always wait for a complete wave;
- always use the same repair sequence;
- never inspect a delegated surface;
....

Over time, they turn orchestration into a rigid state machine.
`codex_workflow` now simply provides specialized resources and practical guidelines
accumulated through those experiments. The Main Agent decides how to use and combine
them for each task.
---

### Platform Feasibility

There were also several ideas that I came up with myself that sounded great in theory but simply weren't feasible on the platform.

#### 1. The original Explorer Companion idea

The original idea behind the Explorer Companion — now just called the **Companion** — was for it to handle miscellaneous work, receive reports from workers, consolidate them, and send the result back to the Main Agent.

But it turns out that it can't directly receive reports from those workers because they're all subagents.

#### 2. Inheriting the Main Agent's context

Some roles benefit greatly from seeing the Main Agent's recent context.

For example, the Archivist closing a deployment needs to know what changes were verified, the current state of the project, and the next entry point so it can update the documentation correctly.

But using a different model doesn't mean you can infinitely copy the entire conversation history into it.
In the current implementation, workers normally start with:

`fork_turns="none"`

and receive explicit context capsules.
For closure, the Archivist can instead be created with a finite recent-context fork, currently:

`fork_turns="200"`

if that recent history is useful as documentation context.

--------------------

There have been many times when I thought:

*"Okay, this version is done. Everything makes sense now."*

Then I tested it, watched how the workflow actually behaved, looked at the statistics...
...and ended up changing it again.
And again.
And again.

Until the design actually worked well in practice, rather than only making sense in my imagination.

---

The coordination process roughly works like this:

**Main Agent receives the task**  
→ reads `agent_docs/` to build a comprehensive understanding of the project's context, architecture, and timeline  
→ identifies critical parts of the codebase and reads them itself, while deploying the `Companion` and `Investigator` workers when needed  
→ plans the work and divides it into bounded tasks  
→ each worker receives a work package containing the context scope, task, goal, and a knowledge package with project-specific guidance  
→ at substantive deployment closure, `agent_docs/` is updated, the Git handoff is completed, and the integrated `$deployment-token-report` is generated.

Here's an example of the token-usage report generated at the end of each Heavy-route deployment:

![End-of-session token report](token_report.png)

In this design, the **Companion** helps reduce context pressure on the Main Agent.

Together with the **Investigators**, it offloads work that does not require the Main Agent's high intelligence, allowing the Main Agent to remain focused on orchestration, high-level reasoning, and critical decisions without being distracted by lower-value operational work.

Each work package contains instructions enriched with knowledge distilled from the Main Agent, benefiting from its broad understanding of the overall task and project context.

Each **Default Executor** can therefore focus on a compact, well-scoped package of work.

**Luna is very powerful for this kind of bounded work.**

The **Senior Executor** acts as a fallback for exceptionally difficult problems where stronger reasoning is required.

### Batching Guidelines

The workflow's **batching guidelines** came from extensive experimentation.

They are designed to group related coordination and execution work more efficiently, significantly reducing the number of Main Agent rollouts and the repeated context replay associated with them.

Basically, they're scheduling rules:

- Independent workers that contribute to the same decision should be dispatched together.
- The Main Agent waits for the relevant group of results and synthesizes them once.
- The next batch should only be opened when evidence from the previous batch actually changes the next question.
- Independent implementation packages without overlapping write ownership can run in parallel.
- Dependencies, overlapping mutations, uncertainty, or high-risk work should still run sequentially.
- Don't poll workers, request status-only updates, or ask for evidence that has already been provided.
- Normal operational failures should go back to the appropriate owner for repair. The Main Agent only intervenes when a new decision is required.
- Independent read/search/check operations performed by the Main Agent should also be grouped into a sensible tool turn.

### Avoiding Unnecessary Worker Wakeups

After dispatching a worker, the Main Agent waits for it to finish or ask for help instead of repeatedly requesting status updates. It wakes the worker again only when there is new information, a repair request, or a new task, and sends only what changed.

## 1. Main Agent and Workers

| Role | Model | Primary Responsibility | Quantity |
| --- | --- | --- | ---: |
| **Main Agent** | Session-selected model | **Primary orchestrator.** Owns the core task context, makes high-level decisions, coordinates the workflow, and distributes the knowledge required by specialized subagents. | 1 |
| **Companion** | Luna · xhigh | **Persistent secretary and context assistant.** Reduces context pressure and operational overhead on the Main Agent by handling supporting context, organizing information, consolidating reports, and taking care of lightweight auxiliary work. | 1 |
| **Investigator** | Luna · xhigh | **Research, investigation, and discovery specialist.** Explores bounded questions, repositories, comparative surveys, technical evidence, documentation, prior art, and potential solutions using project material, the Internet, or both. Investigators can operate in parallel across independent lanes. | As needed |
| **Default Executor** | Luna · max | **Default implementation worker.** Handles normal production tasks delegated by the Main Agent, including coding, modifications, integration work, and other routine implementation activities. Multiple Default Executors may work in parallel when tasks can be safely decomposed. | As needed |
| **Senior Executor** | Sol · medium | **High-capability implementation specialist.** Reserved for exceptionally difficult or high-impact work where stronger reasoning is justified, such as project-core changes, complex algorithms, architectural modifications, or mathematically demanding tasks. | 1 maximum |
| **Tester** | Luna · max | **Independent verification specialist.** Designs, implements, and runs tests; validates requirements and acceptance criteria; identifies regressions or defects; and provides verification evidence before work is accepted. | As needed |
| **Archivist** | Luna · xhigh | **Documentation and closure specialist.** Handles assigned documentation outside the three main-owned deployment-state documents, performs the read-only Git handoff, and produces the end-of-deployment token report. | 1 per substantive deployment, plus as needed |

![Heavy Route structure](heavy_route_structure.png)

> `doc-writer` and `closure_steward` were merged into the `archivist` role in version 1.1.14.

## 2. Installed topology and state

### 2.1 User-level installation

```text
~/.codex/
├── AGENTS.md                         # workflow command block + unrelated user content
├── config.toml                       # workflow-owned keys + unrelated settings
├── agents/
│   ├── archivist.toml
│   ├── companion.toml
│   ├── default_executor.toml
│   ├── investigator.toml
│   ├── senior_executor.toml
│   └── tester.toml
├── skills/
│   └── deployment-token-report/
└── codex_workflow/
    ├── archivist.md
    ├── heavy_route.md
    ├── medium_route.md
    ├── install_state.json
    ├── operate/
    ├── resources/
    ├── runtime/
    ├── templates/
    │   ├── AGENTS.md
    │   ├── agents/
    │   ├── project_docs/
    │   └── skills/
    ├── .source_backup/<version>/
    └── .backups/<old-version>-<utc-timestamp>/
```

The user state file records:

```json
{
  "schema_version": 2,
  "version": "<installed-version>",
  "owned_runtime_files": ["<relative paths>"],
  "owned_workers": ["<worker names>"],
  "owned_skills": ["<skill names>"],
  "projects": ["<canonical absolute project roots>"]
}
```

Ownership lists permit later update and removal to distinguish workflow files
from unrelated user assets. Runtime-relative paths and skill names are
validated before they can identify deletion targets. The project registry lets
one update validate and update every installed project without scanning the
filesystem.

### 2.2 Project installation

```text
<project>/
├── AGENTS.md                         # present when enabled
├── .gitignore                       # optional marked workflow block
├── agent_docs/
│   ├── latest_session_work.md
│   ├── project_core_tech.md
│   ├── project_diary.md
│   ├── project_overview.md
│   ├── project_progress.md
│   ├── project_structure.md
│   └── <optional module documents>.md
└── .codex_workflow_hidden_resources/
    ├── .AGENTS.md                    # present instead of root AGENTS.md when disabled
    ├── personalization.md
    └── state.json
```

Enabled and disabled entry points are mutually exclusive. The project state
records schema version, entry format version, workflow version, and enabled
state. The recorded workflow version lets update validate a project entry
against the exact historical source that produced it rather than assuming all
projects already use the currently installed template.

## 3. Lifecycle commands

The user triggers lifecycle behavior with exact standalone prompts installed in
the marked region of `~/.codex/AGENTS.md`.

| Prompt | Scope | Behavior |
| --- | --- | --- |
| First bootstrap guide | User runtime + current project | Validates an extracted release, installs shared assets, initializes the project, and requires an Archivist documentation action |
| `codex_workflow --install` | Current project | Uses the existing user-level runtime, imports unrecognized local instructions, creates missing project assets, repairs recognized safe omissions, and requires documentation initialization or recovery when needed |
| `codex_workflow --personal` | Current project | Interactively validates and atomically applies all three personalization sections |
| `codex_workflow --check-update` | User runtime, read-only | Reports every newer installable release with compact release-note summaries; downloads and changes nothing |
| `codex_workflow --update` | User runtime + all registered projects | Stages and verifies the newest eligible release, hands control to its update guide, backs up owned state, and updates every registered project in one transaction |
| `codex_workflow --disable` | Current project | Atomically moves the recognized active entry point into hidden resources and updates state |
| `codex_workflow --enable` | Current project | Atomically moves the recognized hidden entry point back to project root and updates state |
| `codex_workflow --remove` | User runtime + current project | Produces a read-only destructive plan, requires one explicit confirmation, then removes only recognized workflow-owned surfaces while restoring local instructions |

All lifecycle commands require Python 3.11 or newer. Windows uses the
equivalent `py -3.11` invocation and native path syntax.

### 3.1 Bootstrap

Bootstrap expects a verified universal release ZIP with exactly one top-level
`codex_workflow/` directory. It validates the package, installs the user-level
runtime and current project in one composed plan, saves a versioned source copy,
and returns an Archivist action. The user restarts Codex only after both the
filesystem operation and required documentation action succeed.

### 3.2 Project install and repair

Install never reinstalls `~/.codex/`. It creates only project-level assets from
the installed templates. If an unrecognized root `AGENTS.md` exists, its exact
content enters the project-local marker region. A recognized healthy enabled or
disabled project is a no-op. Safe repairs include missing or stale project
state, a recoverable missing personalization resource, workflow-owned
`.gitignore` drift, leftover package staging, and missing or still-template
framework documents.

Ambiguous states stop with recovery guidance: both entry points present,
unrecognized hidden entry points, malformed markers, personalization mismatch,
or a recognized entry using an older or locally modified managed template.

### 3.3 Update

Update selects the highest non-draft semantic release containing both
`codex_workflow-<version>.zip` and `SHA256SUMS`. Prereleases remain eligible. It
verifies the checksum and archive structure and stages the release. The agent
then reads the incoming package's `operate/update.md` before running its
runtime. This lets each release define its own migrations and validate its own
schema instead of depending on an older installed guide or launcher.

The update plan:

- writes a timestamped backup of user instructions, configuration, runtime,
  worker TOMLs, owned skills, and relevant project workflow files;
- replaces route, worker, skill, template, guide, and runtime definitions;
- updates the user command region and owned Codex settings;
- preserves unrelated user settings, workers, skills, and instruction content;
- validates every registered project against its recorded version's source backup;
- preserves personalization, project-local instructions, project documentation,
  and enabled/disabled state;
- removes obsolete manifest-owned runtime files, workers, and skills after
  validating their ownership markers; and
- rejects equal versions and unapproved downgrades.

Bootstrap and project install record canonical project roots in the user-level
registry. The first registry-aware update from an older installation asks the
user for the complete project list and never searches the filesystem. Once the
registry exists, later updates require no project selection.

A historical entry containing merged local edits requires explicit reviewed
local instructions for one-time migration. The runtime does not infer them.
The public onboarding guidance treats version `1.1.3` as outside the supported
direct-upgrade path and requires removal before installing a current release.

### 3.4 Disable and enable

Disable and enable move the exact recognized entry-point bytes between root and
hidden locations and update only the `enabled` field in project state. An
already-correct state is a safe no-op. Missing, conflicting, or unrecognized
entry points are hard errors.

### 3.5 Remove

Removal is the only public lifecycle operation with a separate preview and
confirmed phase. The preview reports planned creates, replacements, deletions,
warnings, and preserved content with `applied: false`. Only an explicit second
confirmation runs the same validated plan.

Removal deletes the workflow wrapper or restores preserved project-local
instructions to root `AGENTS.md`; removes hidden project resources and the
workflow-owned `.gitignore` block; removes the marked user instruction region,
owned platform keys, marked worker TOMLs, manifest-owned marked skills, and the
dedicated runtime including backups. It preserves `agent_docs/` and unrelated
user content.

## 4. Deployment Token Report

The reporting skill is installed under `~/.codex/skills/` but is eligible only
for an Archivist assigned to substantive deployment closure.

After repository work is sealed, the parser:

1. Uses `CODEX_THREAD_ID` to identify the calling Archivist.
2. Verifies that the caller is a spawned Archivist and resolves its parent main
   session.
3. Finds the exact deployment marker in assistant message text in that main
   rollout.
4. Uses the latest user turn at or before the marker as the report start.
5. Indexes descendant sessions, omitting unrelated sessions such as guardians.
6. Aggregates recorded `last_token_usage` values through the parser start time.
7. Groups rows by agent role and appends the main-agent row last.

`Quantity` counts distinct task paths represented for a role, `Rollouts` counts
model generations with recorded last-token usage, `Input` includes its cached
subset, and `Output` is recorded generated-token usage. The cutoff excludes the
Archivist's post-parser response and the main's later final response.

The required result is:

```text
| Agent | Quantity | Rollouts | Cached input | Input | Output |
| --- | ---: | ---: | ---: | ---: | ---: |
| <agent role> | <count> | <count> | <tokens> | <tokens> | <tokens> |
```

Missing boundaries, malformed session data, invalid token counts, incomplete
ancestry, or unavailable caller metadata produce a limitation instead of an
estimate.

## 5. Repository, packaging, and release boundaries

The repository contains three classes of files:

```text
repository root/
├── codex_workflow/              # complete distributable package
├── scripts/                     # release builder and regression tests
├── .github/workflows/           # tagged-release automation
├── docs/                        # architecture and release notes
├── README.md                    # onboarding and product overview
├── workflow_breakdown.md        # this analysis
├── RELEASING.md                 # maintainer procedure
└── images and benchmarks        # presentation and evaluation assets
```

Only `codex_workflow/` enters the release ZIP. The builder uses Python's
standard library, enumerates members in deterministic order, fixes archive
timestamps and modes, rejects Python caches and symlinks, compresses the
payload, verifies the completed archive, and emits `SHA256SUMS`.

The release workflow runs both test suites, validates the package, builds and
verifies the archive from the tagged commit, and publishes the ZIP plus
checksum. Tag-triggered releases are prereleases under the current workflow;
manual dispatch exposes an explicit prerelease choice.
