<h3 align="center"><big><big><strong>SIMPLE&emsp;&emsp;───&emsp;&emsp;EASY&emsp;&emsp;───&emsp;&emsp;EFFICIENT</strong></big></big></h3>
<p align="center"><small>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(to use)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(to install)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(token consumption)</small></p>
<hr>

![Workflow illustration](illustration.png)

Built for token-efficient agent orchestration, with swarm execution, persistent context support, and compact knowledge handoffs between agents. `agent_docs/` provides durable project memory for goals, architecture, decisions, progress, and session handoffs.

> ⭐ For lightweight tasks, it won’t overdo things. Light route is default.

## 1. Quick installation ⚙️
### Open Codex CLI / Codex app from your project directory

Change permision to `approve for me` or `full access`.
▶️ Send:
```text
Download and extract the latest `codex_workflow-<version>.zip` asset from https://github.com/viettran-edgeAI/codex_workflow/releases. Verify it against `SHA256SUMS`, then read the bundled `codex_workflow/operate/bootstrap.md` and follow it to complete the initial installation.
```
> ⭐ Recommended: use 5.6 Luna xhigh for installation. 

🔄 Restart Codex after installation

The initial bootstrap will include creating the project documentation framework `agent_docs/` using `archivist` subagent. Once that bootstrap is complete, the current project is ready to use. Whenever you need to install this workflow for a new project, simply open Codex and send: `codex_workflow --install`

> Requires Python 3.11 or newer for deterministic lifecycle operations.

**Note:** If you are currently using 1.1.3 version, you cannot upgrade directly to a newer version(cause I removed --configure feature). Run `codex_workflow --remove` to uninstall it first, then install the newer version.

## 2. Workflow usage 

### This workflow has 3 routes:
- Light route : No subagents, no workflow, minimal context.
- Heavy route : Implement the full set of workers, including `companion`, `investigator`, `default executor`, `senior executor`, `tester`, and `archivist`. The main agent orchestrates the work.
- Medium route: Deploy `Companion`, `Investigator` and `Archivist` to assistance the Main agent. The main agent handles the deployment itself. Choose this route when you want workflow-mode context support without delegating production work, like front-end design, visualization, or 3D works, but it will burn tokens faster than Heavy route.

### How to use
- Normally, for simple work, general Q&A, you don't need to do anything. `light route` is the default route.

--------------------------------
- When starting a new task, tell Codex :
```text
use medium/heavy route. [your task description]
```
Or continue a task that was already underway in the previous session: 
```text
use medium/heavy route. Continue ongoing work.
```
> Codex stays on the selected route until you change it

---------------
> **⭐ Recommendation:** Assign very large and complex tasks to the `heavy route` to make the most of its capabilities and maximize token usage savings. Don't hesitate to choose Sol xhigh / Astra high for this route. Using much lower reasoning efforts will not actually save tokens and will severely reduce its coordination capabilities.

![Heavy Route structure](heavy_route_structure.png)

What's special about the system:

- Built-in project memory: `agent_docs/` keeps project goals, architecture, progress, decisions, and the latest handoff across sessions.
- Flexibility: The system doesn't force the main agent into a rigid process: requiring coordination in this way, that way... It provides it with resources and power (specialized agents) and fine-tuning and guidance based on hundreds of trials.
- Fine-tuned balance: Main agent's control <---> costs & task completion capabilities. based on analysis and observation, not on feeling. 
- Knowledge distribution: Each task package from the main agent to the workers includes a task completion guide.
- Batching guidelines prevent excessive main agent rollout.
- The **Senior Executor** serves as a fallback for exceptionally difficult problems where stronger reasoning is required.
- Addresses the issue of the main agent waking up workers too often.
- Built-in token report: End-of-session token statistics for each agent, allowing you to monitor how much each agent rolls out and how they use their tokens.
......

## Light benchmark
**Batching guidelines** techniques(since 1.1.3 version) significantly reduce the main agent's rollout, which in turn reduces the main agent's cached input tokens, a major component of the operation cost, see **New workflow** below :

![Light benchmark analysis](light_benchmark/analysis.png)

The current benchmark is an initial case study. See the
[benchmark coverage proposal](benchmarks/README.md) for ideas on testing more
tasks and AI providers.

## 3. More details 

Send these exact commands to Codex from the relevant project directory:

| Command | Purpose |
| --- | --- |
| `codex_workflow --install` | Install workflow in the current project and initialize its documentation framework. |
| `codex_workflow --personal` | Add or update project-specific workflow preferences. |
| `codex_workflow --check-update` | Check for a newer release without installing it. |
| `codex_workflow --update` | Download and verify the latest release, read its update guide, then update the shared runtime and every registered project. |
| `codex_workflow --disable` / `codex_workflow --enable` | Disable or re-enable the workflow for the current project. |
| `codex_workflow --remove` | Remove the installed workflow after a destructive dry-run and confirmation. |

For the complete architecture, route, lifecycle, ownership, safety, and release
analysis, see [workflow_breakdown.md](workflow_breakdown.md).
