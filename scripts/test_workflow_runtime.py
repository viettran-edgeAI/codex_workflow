"""Regression tests for the lifecycle runtime."""

from __future__ import annotations

import json
import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "codex_workflow"
PACKAGE_VERSION = (PACKAGE / "operate" / "VERSION").read_text(encoding="utf-8").strip()


def next_patch_version(version: str) -> str:
    major, minor, patch = version.split(".")
    return f"{major}.{minor}.{int(patch) + 1}"


NEXT_PACKAGE_VERSION = next_patch_version(PACKAGE_VERSION)

sys.path.insert(0, str(PACKAGE))
sys.path.insert(0, str(PACKAGE / "runtime"))
sys.path.insert(0, str(ROOT / "scripts"))

import workflow as workflow_cli
from package_release import (
    ReleaseError as PackageReleaseError,
    _verify_member_names,
    build_zip,
    verify_archive,
)

from runtime.platform_settings import (
    patch_codex_settings,
    remove_workflow_owned_settings,
)
from runtime.backup import append_backup_mutations
from runtime.errors import TransactionError, ValidationError
from runtime.lifecycle import (
    PackageLayout,
    ProjectPaths,
    RuntimePaths,
    materialize_personalization,
    plan_bootstrap,
    plan_enable,
    plan_install,
    plan_personalize,
    plan_project_install,
    plan_remove,
    plan_update,
)
from runtime.registry import (
    migration_file,
    normalize_project_roots,
    read_project_list,
    read_registered_projects,
)
from runtime.markers import (
    PROJECT_LOCAL,
    PROJECT_PERSONALIZATION,
    USER_MANAGED,
    extract,
    render_project_entry,
)
from runtime.plan import OperationPlan, read_string_list, resolve_owned_runtime_path
from runtime.release import (
    ReleaseSelection,
    parse_semver,
    select_releases,
    summarize_release_notes,
)
from runtime.transaction import Mutation, apply


class MarkerTests(unittest.TestCase):
    def test_user_command_contract_exposes_only_supported_lifecycle_prompts(self) -> None:
        instructions = (PACKAGE / "operate" / "user_AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("codex_workflow --check-update", instructions)
        self.assertIn("codex_workflow --remove", instructions)

        personalization = (PACKAGE / "operate" / "personalization_guide.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("resources/personalization.md", personalization)
        self.assertIn("missing or invalid", personalization)
        self.assertIn("copy that section's complete", personalization)

        update = (PACKAGE / "operate" / "update.md").read_text(encoding="utf-8")
        self.assertIn("stage-update", update)
        self.assertIn("returned `guide` path", update)
        self.assertIn("## Apply this release", update)
        self.assertIn("Do not scan the filesystem", update)

    def test_template_renders_independent_project_regions(self) -> None:
        template = (PACKAGE / "AGENTS.md").read_text(encoding="utf-8")
        rendered = render_project_entry(
            template,
            personalization="Personal rule.",
            local_instructions="# Existing\nKeep this.",
        )
        self.assertEqual(extract(rendered, PROJECT_PERSONALIZATION), "Personal rule.")
        self.assertEqual(extract(rendered, PROJECT_LOCAL), "# Existing\nKeep this.")

    def test_operational_policies_are_compact_and_knowledge_aware(self) -> None:
        names = (
            "AGENTS.md",
            "medium_route.md",
            "heavy_route.md",
        )
        policies = {
            name: (PACKAGE / name).read_text(encoding="utf-8") for name in names
        }
        line_limits = {
            "AGENTS.md": 115,
            "medium_route.md": 140,
            "heavy_route.md": 200,
        }
        for name, text in policies.items():
            self.assertLess(len(text.splitlines()), line_limits[name], name)

        heavy = policies["heavy_route.md"]
        heavy_flat = " ".join(heavy.split())
        self.assertIn("## Main Role and Optimization Target", heavy)
        self.assertIn("You are the main agent and central knowledge director", heavy)
        self.assertIn("do not become a production Executor", heavy_flat)
        self.assertIn("Aggregate subagent token use is not an optimization target", heavy)
        self.assertIn("exception is Senior Executor", heavy)
        self.assertIn("## Agents and Ownership", heavy)
        self.assertIn("One required persistent read-only secretary", heavy)
        self.assertIn("bounded project or Internet investigation", heavy)
        self.assertIn("## Shared Deployment-State Entry", heavy)
        self.assertIn("complete the shared first-entry", heavy)
        self.assertIn("Companion and `agent_docs/` contract in `AGENTS.md`", heavy)
        self.assertIn("Do not repeat that intake", heavy)
        self.assertNotIn("directly read the complete current `agent_docs/`", heavy_flat)
        self.assertIn("## Context Routing After Intake", heavy)
        self.assertIn("create a compact working-context map", heavy_flat)
        self.assertIn("**Direct**: decision-critical code", heavy)
        self.assertIn("**Companion**: supporting modules, tools, configuration", heavy)
        self.assertIn("**Investigator**: one bounded project or Internet", heavy)
        self.assertIn("comparative survey, repository exploration", heavy)
        self.assertIn("Do not directly explore a Companion", heavy)
        self.assertIn("unless it becomes decision-critical", heavy)
        self.assertIn("## Deployment Boundary", heavy)
        self.assertNotIn('agent_type="companion"', heavy)
        self.assertNotIn('task_name="companion"', heavy)
        self.assertIn("<!-- codex-workflow-deployment-start", heavy)
        self.assertIn("## Role-Specific Work Packages", heavy)
        self.assertIn("**Task ID**", heavy)
        self.assertIn("**Project Context Scope**", heavy)
        self.assertIn("**Investigation Task + Goal**", heavy)
        self.assertIn("**Implementation Context + Ownership**", heavy)
        self.assertIn("**Verification Context**", heavy)
        self.assertIn("**Documentation Context + Audience**", heavy)
        self.assertIn("## Main-Agent Execution Boundary", heavy)
        self.assertIn("must not write production code or\ntests", heavy)
        self.assertIn("defining gates, assigning execution", heavy)
        self.assertIn("main may reason about root cause", heavy)
        self.assertIn("Worker unavailability does not authorize", heavy)
        self.assertIn("## Orchestration, Repair, and Lifecycle", heavy)
        self.assertIn("Do not poll workers", heavy)
        self.assertIn("status-only updates", heavy)
        self.assertIn("instead of starting a main-agent diagnostic loop", heavy)
        self.assertIn("owning Executor for repair", heavy)
        self.assertIn("same\n  Tester for recheck", heavy)
        self.assertNotIn("at most 20 active subagents", heavy)
        self.assertIn("no workflow-imposed aggregate active-subagent limit", heavy_flat)
        self.assertIn("exactly one persistent Companion", heavy)
        self.assertIn("at most one Senior Executor", heavy)
        self.assertIn("Create and coordinate every worker directly", heavy)
        self.assertIn("direct fast path", heavy)
        self.assertIn("Do not use it for a subtask", heavy)
        self.assertIn("keeping them concise and canonical", heavy)
        for main_owned_document in (
            "`agent_docs/project_progress.md`",
            "`agent_docs/project_diary.md`",
            "`agent_docs/latest_session_work.md`",
        ):
            self.assertIn(main_owned_document, heavy)
        self.assertIn("`$deployment-token-report`", heavy)
        for retired_contract in (
            "investigation_team.md",
            "repair_needed",
            "five core",
            "split intake",
        ):
            self.assertNotIn(retired_contract, heavy.lower())

        medium = policies["medium_route.md"]
        medium_flat = " ".join(medium.split())
        self.assertIn("direct fast path", medium)
        self.assertIn("You are the main agent", medium)
        self.assertIn("Own planning, root-cause reasoning, implementation", medium)
        self.assertIn("Medium does not delegate production or verification", medium)
        self.assertIn("## Shared Deployment-State Entry", medium)
        self.assertIn("complete the shared first-entry", medium)
        self.assertIn("Companion and `agent_docs/` contract in `AGENTS.md`", medium)
        self.assertIn("Do not repeat that intake", medium)
        self.assertNotIn("directly read the complete current `agent_docs/`", medium_flat)
        self.assertIn("## Context Routing After Intake", medium)
        self.assertIn("create a compact working-context map", medium_flat)
        self.assertIn("**Direct**: code, contracts, interfaces", medium)
        self.assertIn("**Companion**: supporting modules, tools, configuration", medium)
        self.assertIn("**Investigator**: one bounded project or Internet", medium)
        self.assertIn("comparative survey, repository exploration", medium)
        self.assertIn("Do not directly explore a Companion", medium)
        self.assertIn("necessary for main-owned production", medium)
        self.assertIn("## Deployment Boundary", medium)
        self.assertIn("## Support Packages and Investigation", medium)
        self.assertNotIn('agent_type="companion"', medium)
        self.assertNotIn('task_name="companion"', medium)
        self.assertIn("<!-- codex-workflow-deployment-start", medium)
        self.assertIn("**Task ID**", medium)
        self.assertIn("**Project Context Scope**", medium)
        self.assertIn("**Main-Agent Context Guidance**", medium)
        self.assertIn("**Investigation Context**", medium)
        self.assertIn("**Main-Agent Investigation Guidance**", medium)
        self.assertIn("comparative project surveys, repository", medium)
        self.assertIn("## Rollout-Efficient Support", medium)
        self.assertIn("synthesize once", medium)
        self.assertIn("Do not poll support workers", medium)
        self.assertNotIn("at most 20 active subagents", medium)
        self.assertIn("no workflow-imposed aggregate active-subagent limit", medium_flat)
        self.assertIn("Use exactly one persistent Companion", medium)
        self.assertIn("Before the final response", medium)
        self.assertIn("keeping them concise and canonical", medium)
        for main_owned_document in (
            "`agent_docs/project_progress.md`",
            "`agent_docs/project_diary.md`",
            "`agent_docs/latest_session_work.md`",
        ):
            self.assertIn(main_owned_document, medium)
        self.assertIn("`$deployment-token-report`", medium)
        for retired_contract in (
            "investigation_team.md",
            "medium_companion.md",
        ):
            self.assertNotIn(retired_contract, medium.lower())

        agents_policy = policies["AGENTS.md"]
        self.assertIn("## Design Principles", agents_policy)
        self.assertIn("## Rollout Efficiency", agents_policy)
        self.assertIn("Batch independent reads, searches, metadata checks", agents_policy)
        self.assertIn("wait for the\nrelevant set", agents_policy)
        self.assertIn("synthesize their reports once", agents_policy)
        self.assertIn("## Working State", agents_policy)
        self.assertIn("## Project Documentation", agents_policy)
        self.assertIn(
            "you own `project_progress.md`, `project_diary.md`, and\n"
            "`latest_session_work.md`",
            agents_policy,
        )
        self.assertIn("## Route Selection", agents_policy)
        self.assertIn("## Platform Paths", agents_policy)
        self.assertIn("codex_workflow/medium_route.md", agents_policy)
        self.assertIn("codex_workflow/heavy_route.md", agents_policy)
        self.assertIn("Select one of these routes", agents_policy)
        self.assertIn("Follow the user's route selection", agents_policy)
        self.assertIn("immediately\ncreate one persistent Companion", agents_policy)
        self.assertIn("directly read the\ncomplete current `agent_docs/`", agents_policy)
        self.assertIn("Never repeat it later in the session", agents_policy)
        self.assertIn("Give its first assignment the current route", agents_policy)
        self.assertIn("Each rollout reloads its persistent context", agents_policy)
        self.assertIn("avoid status-only requests", agents_policy)
        self.assertIn(
            "directly record the current goal and\ncontinuation state",
            agents_policy,
        )
        self.assertNotIn("session-model requirement", agents_policy)
        for route_owned_contract in (
            "## Medium and Heavy Contracts",
            "codex-workflow-deployment-start",
            "**Task ID**",
            "directly creates and coordinates",
            "`$deployment-token-report`",
        ):
            self.assertNotIn(route_owned_contract, agents_policy)
        for retired_guide in (
            "medium_companion.md",
            "heavy_companion.md",
            "investigation_team.md",
        ):
            self.assertNotIn(retired_guide, agents_policy)
            self.assertFalse((PACKAGE / retired_guide).exists())
        self.assertNotIn("There are three routes", agents_policy)

        token_report_skill = (
            PACKAGE / "skills" / "deployment-token-report" / "SKILL.md"
        ).read_text(encoding="utf-8")
        token_report_header = (
            "| Agent | Quantity | Rollouts | Cached input | Input | Output |"
        )
        self.assertIn("The required table template is exactly", token_report_skill)
        self.assertEqual(token_report_skill.count(token_report_header), 1)
        self.assertIn(
            "| --- | ---: | ---: | ---: | ---: | ---: |", token_report_skill
        )
        self.assertIn("Keep the columns exactly as shown", token_report_skill)
        self.assertIn("main agent placed this exact hidden comment", token_report_skill)
        self.assertIn("assistant message text there", token_report_skill)
        self.assertIn("find the exact marker in", token_report_skill)

        handoff_contract = (PACKAGE / "archivist.md").read_text(
            encoding="utf-8"
        )
        handoff_worker = (PACKAGE / "agents" / "archivist.toml").read_text(
            encoding="utf-8"
        )
        handoff_contract_flat = " ".join(handoff_contract.split())
        handoff_worker_flat = " ".join(handoff_worker.split())
        self.assertIn('agent_type="archivist"', handoff_contract)
        self.assertIn('fork_turns="200"', handoff_contract)
        self.assertIn("Reuse an Archivist", handoff_contract)
        self.assertIn("one reporting owner", handoff_contract)
        self.assertIn("Keep those files outside Archivist's write", handoff_contract)
        self.assertIn("You are Archivist.", handoff_worker)
        self.assertIn("`agent_docs/project_diary.md`", handoff_worker)
        self.assertIn("Do not\nedit those files during a deployment", handoff_worker)
        self.assertIn("`$deployment-token-report`", handoff_worker)
        self.assertIn("at most 200 words", handoff_worker)
        for framework_file in ("project_progress.md", "latest_session_work.md"):
            self.assertIn(framework_file, handoff_worker)
            framework_template = (
                PACKAGE / "project_docs" / framework_file
            ).read_text(encoding="utf-8")
            self.assertNotIn("updates this document", framework_template)
            self.assertNotIn("Keep only", framework_template)
            self.assertNotIn("Keep one concise", framework_template)
        for policy in (
            heavy,
            medium,
            agents_policy,
            handoff_contract,
            handoff_worker,
        ):
            self.assertNotIn("end this session", policy.lower())

        tester = (PACKAGE / "agents" / "tester.toml").read_text(encoding="utf-8")
        executor = (PACKAGE / "agents" / "default_executor.toml").read_text(
            encoding="utf-8"
        )
        senior = (PACKAGE / "agents" / "senior_executor.toml").read_text(
            encoding="utf-8"
        )
        doc_writer = (PACKAGE / "agents" / "archivist.toml").read_text(
            encoding="utf-8"
        )
        bootstrap = (PACKAGE / "operate" / "bootstrap.md").read_text(encoding="utf-8")
        install = (PACKAGE / "operate" / "install.md").read_text(encoding="utf-8")
        companion_worker = (PACKAGE / "agents" / "companion.toml").read_text(
            encoding="utf-8"
        )
        investigator = (PACKAGE / "agents" / "investigator.toml").read_text(
            encoding="utf-8"
        )
        current_instruction_surfaces = {
            **policies,
            "archivist.md": handoff_contract,
            **{
                f"agents/{path.name}": path.read_text(encoding="utf-8")
                for path in sorted((PACKAGE / "agents").glob("*.toml"))
            },
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        }
        retired_architecture_phrases = (
            "wave barrier",
            "investigation wave",
            "execution wave",
            "evidence ledger",
            "evidence manifest",
            "evidence-manifest",
            "verification_ledger",
            "repair packet",
            "repair loop",
            "root-cause gate",
            "split intake",
            "lifecycle parent",
            "five-file intake",
            "universal executor-tester",
            "universal implementation checklist",
            "fixed execution pipeline",
            "predefined pipeline",
        )
        for name, text in current_instruction_surfaces.items():
            lowered = text.lower()
            for retired_phrase in retired_architecture_phrases:
                self.assertNotIn(retired_phrase, lowered, name)

        tester_flat = " ".join(tester.split())
        self.assertIn("Receive the intended behavior", tester)
        self.assertIn("Design the specific tests", tester_flat)
        self.assertIn("do not repair production\ncode", tester)
        self.assertIn("Leave repair and re-verification decisions", tester)
        self.assertIn("bounded local discovery, implementation, self-check", executor)
        self.assertIn("ordinary repair", executor)
        self.assertIn("unresolved hard decision", senior)
        for worker in (
            companion_worker,
            investigator,
            executor,
            senior,
            tester,
        ):
            normalized_worker = " ".join(worker.split())
            self.assertIn("You are", worker)
            self.assertIn("`Task ID`", worker)
            self.assertIn("follow-up to repeat task id", normalized_worker.lower())
            self.assertIn("Task ID in every", normalized_worker)
            self.assertIn("complete capsule structure", normalized_worker)
            for descriptive_instruction in (
                "The initial package",
                "An initial package",
                "The main owns",
                "The main supplies",
            ):
                self.assertNotIn(descriptive_instruction, worker)
        self.assertIn("`Project Context Scope`", companion_worker)
        self.assertIn("`Main-Agent Context Guidance`", companion_worker)
        self.assertIn("`Investigation Context`", investigator)
        self.assertIn("`Investigation Task + Goal`", investigator)
        self.assertIn("`Main-Agent Investigation Guidance`", investigator)
        for worker in (executor, senior):
            self.assertIn("`Implementation Context + Ownership`", worker)
            self.assertIn("`Implementation Task + Goal`", worker)
            self.assertIn("`Main-Agent Implementation Guidance`", worker)
        self.assertIn("`Verification Context`", tester)
        self.assertIn("`Verification Goal`", tester)
        self.assertIn("`Main-Agent Verification Guidance`", tester)
        self.assertIn("`Documentation Context + Audience`", doc_writer)
        self.assertIn("`Documentation Task + Goal`", doc_writer)
        self.assertIn("`Main-Agent Documentation Guidance`", doc_writer)
        for worker in (executor, senior, tester):
            self.assertNotIn("evidence-manifest", worker)
            self.assertNotIn("verification_ledger", worker)
        for worker in (executor, senior, tester):
            self.assertIn("intermediate update only when new evidence changes", worker)
            self.assertIn("at most 100 words", worker)
            self.assertIn("routine report at most 120 words", worker)
            self.assertIn("material escalation", worker)
            self.assertIn("at most 200 words", worker)
        self.assertIn("at most 100 words", companion_worker)
        self.assertIn("assignment report at\nmost 220 words", companion_worker)
        self.assertIn("at most 100 words", investigator)
        self.assertIn("final report at most 120 words", investigator)
        self.assertIn("at most 180 words", investigator)
        self.assertIn("at most 80 words", doc_writer)
        self.assertIn("routine reports at most 120 words", doc_writer)
        self.assertIn("at most 200 words", doc_writer)
        self.assertIn('model = "gpt-5.6-luna"', executor)
        self.assertIn('model = "gpt-5.6-sol"', senior)
        self.assertFalse((PACKAGE / "agents" / "executor_terra.toml").exists())
        self.assertIn("# model_context_window = 520000", companion_worker)
        self.assertIn(
            "# model_auto_compact_token_limit = 450000", companion_worker
        )
        self.assertIn("secretary, and office wrapper", companion_worker)
        self.assertIn("source domain is the project ecosystem", companion_worker)
        self.assertIn("sibling project", companion_worker)
        self.assertIn("sources beyond the project ecosystem", companion_worker)
        self.assertIn("establish compact, source-linked operational context", companion_worker)
        self.assertIn("each later rollout reloads it", companion_worker)
        self.assertIn("assigns diary/module intake", companion_worker)
        self.assertIn("log triage", companion_worker)
        self.assertNotIn("deployment-start: <deployment_id>", companion_worker)
        self.assertNotIn("`$deployment-token-report`", companion_worker)
        self.assertIn('model = "gpt-5.6-luna"', investigator)
        self.assertNotIn("terra", investigator.lower())
        self.assertIn('sandbox_mode = "read-only"', investigator)
        self.assertIn("disposable read-only investigation and discovery", investigator)
        self.assertIn("project material, Internet sources, or both", investigator)
        self.assertIn("exploratory\ndiscovery, comparative surveys", investigator)
        self.assertIn("bounded source surface", investigator)
        self.assertIn("prefer primary or authoritative sources when\nappropriate", investigator)
        self.assertIn("exact project references and direct source links", investigator)
        self.assertIn("independent validation or comparison", investigator)
        self.assertIn("Do not modify project files", investigator)
        self.assertIn("Keep those documents concise enough", doc_writer)
        self.assertIn("fewest words that preserve decisions", doc_writer)
        self.assertNotIn("known bugs", investigator.lower())
        self.assertNotIn("package version", investigator.lower())
        self.assertNotIn("arm64", investigator.lower())
        for worker_policy in (executor, senior, tester, doc_writer, investigator):
            self.assertNotIn("terminal receipt", worker_policy)
            self.assertNotIn("report-batch", worker_policy)
            self.assertTrue(
                "concise" in worker_policy or "smallest decision-ready" in worker_policy
            )
        self.assertIn("verified facts", doc_writer)
        diary_template = (PACKAGE / "project_docs" / "project_diary.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("prevents repeated mistakes", diary_template)
        self.assertIn("Do not record\nsession chronology", diary_template)
        self.assertIn("Expect one required", bootstrap)
        self.assertIn("## Installation Documentation", doc_writer)
        self.assertIn("means the workflow installer has just", doc_writer)
        self.assertIn("the absolute `documentation_root`", doc_writer)
        self.assertIn("the installer\'s\n`files`, `created_files`", doc_writer)
        self.assertIn("`Task ID`", doc_writer)
        self.assertIn("`agent_docs/project_diary.md`", doc_writer)
        self.assertFalse((PACKAGE / "verification_ledger.py").exists())
        self.assertFalse((PACKAGE / "agents" / "wave_barrier.toml").exists())
        for required_context in (
            "project_structure.md",
            "project_overview.md",
            "project_core_tech.md",
        ):
            self.assertIn(required_context, bootstrap)
            self.assertIn(required_context, install)

    def test_reserved_marker_collision_is_rejected_during_import(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            (project / "AGENTS.md").write_text(PROJECT_LOCAL.start, encoding="utf-8")
            with self.assertRaises(ValidationError):
                plan_bootstrap(
                    PackageLayout.resolve(PACKAGE),
                    RuntimePaths(root / "home"),
                    ProjectPaths(project),
                )

    def test_package_requires_exact_user_managed_region(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "codex_workflow"
            shutil.copytree(
                PACKAGE,
                root,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            path = root / "operate" / "user_AGENTS.md"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(USER_MANAGED.start, "", 1), encoding="utf-8"
            )
            with self.assertRaises(ValidationError):
                PackageLayout.resolve(root)

    def test_package_requires_complete_builtin_worker_set(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "codex_workflow"
            shutil.copytree(
                PACKAGE,
                root,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            (root / "agents" / "tester.toml").unlink()
            (root / "agents" / "archivist.toml").unlink()
            with self.assertRaisesRegex(
                ValidationError, "package worker set is incomplete"
            ):
                PackageLayout.resolve(root)

    def test_package_requires_builtin_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "codex_workflow"
            shutil.copytree(
                PACKAGE,
                root,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            shutil.rmtree(root / "skills" / "deployment-token-report")
            with self.assertRaisesRegex(ValidationError, "package skill set"):
                PackageLayout.resolve(root)

    def test_update_help_does_not_publish_local_source_option(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(PACKAGE / "runtime" / "workflow.py"), "update", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("--source", completed.stdout)
        self.assertNotIn("--apply", completed.stdout)

    def test_check_update_command_is_available(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(PACKAGE / "runtime" / "workflow.py"), "check-update", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_removed_tuning_command_is_unavailable(self) -> None:
        retired = "con" + "figure"
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(PACKAGE / "runtime" / "workflow.py"),
                retired,
                "--help",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid choice", completed.stderr)

    def test_remove_help_hides_internal_confirmation_flag(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(PACKAGE / "runtime" / "workflow.py"), "remove", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("--confirm", completed.stdout)


class SafetyTests(unittest.TestCase):
    def test_owned_runtime_manifest_is_confined_and_typed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = Path(temporary) / "runtime"
            with self.assertRaises(ValidationError):
                resolve_owned_runtime_path(runtime_root, "../../outside.txt")
            with self.assertRaises(ValidationError):
                resolve_owned_runtime_path(runtime_root, "/tmp/outside.txt")
        with self.assertRaises(ValidationError):
            read_string_list({"owned_runtime_files": None}, "owned_runtime_files")
        with self.assertRaisesRegex(ValidationError, "must be absolute"):
            normalize_project_roots(["relative/project"])

    def test_backup_skips_missing_optional_user_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            mutations: list[Mutation] = []
            append_backup_mutations(
                mutations,
                root / "backup",
                RuntimePaths(root / "home"),
                ProjectPaths(project),
            )
            self.assertEqual(mutations, [])


class PlatformSettingsTests(unittest.TestCase):
    def test_toml_patch_preserves_unrelated_content(self) -> None:
        original = 'model = "custom"\n\n[agents]\nenabled = false\nother = 7\n'
        rendered = patch_codex_settings(original)
        self.assertIn('model = "custom"', rendered)
        self.assertIn("other = 7", rendered)
        self.assertIn("[agents]", rendered)
        self.assertNotIn("max_concurrent_threads_per_session", rendered)
        self.assertIn("[features]", rendered)
        self.assertIn("multi_agent = true", rendered)
        self.assertNotIn("[features.multi_agent_v2]", rendered)
        self.assertNotIn("hide_spawn_agent_metadata", rendered)
        self.assertNotIn("min_wait_timeout_ms", rendered)

    def test_toml_patch_migrates_legacy_multi_agent_settings(self) -> None:
        original = (
            "[features.multi_agent_v2]\n"
            "enabled = true\n"
            "max_concurrent_threads_per_session = 8\n"
            "hide_spawn_agent_metadata = false\n"
            'keep_legacy = "keep"\n'
        )
        rendered = patch_codex_settings(original)
        self.assertIn("[features.multi_agent_v2]", rendered)
        self.assertIn('keep_legacy = "keep"', rendered)
        self.assertNotIn("hide_spawn_agent_metadata", rendered)
        self.assertIn("[agents]", rendered)
        self.assertNotIn("max_concurrent_threads_per_session", rendered)
        self.assertIn("[features]", rendered)
        self.assertIn("multi_agent = true", rendered)
        v2_section = rendered.split("[features.multi_agent_v2]", 1)[1].split(
            "[agents]", 1
        )[0]
        self.assertNotIn("enabled = true", v2_section)

    def test_toml_patch_removes_legacy_agents_alias(self) -> None:
        original = (
            "[agents]\n"
            "max_concurrent_threads_per_session = 20\n"
            "max_threads = 8\n"
            "max_depth = 1\n"
            "job_max_runtime_seconds = 1800\n"
        )
        rendered = patch_codex_settings(original)
        self.assertNotIn("max_threads", rendered)
        self.assertIn("max_depth = 1", rendered)
        self.assertIn("job_max_runtime_seconds = 1800", rendered)
        self.assertNotIn("max_concurrent_threads_per_session", rendered)

    def test_toml_patch_removes_owned_v2_gate(self) -> None:
        rendered = patch_codex_settings(
            "[features.multi_agent_v2]\nenabled = false\n"
        )
        self.assertNotIn("[features.multi_agent_v2]", rendered)
        self.assertNotIn("enabled = false", rendered)
        self.assertIn("[agents]", rendered)
        self.assertIn("[features]", rendered)

    def test_toml_remove_preserves_unrelated_content(self) -> None:
        original = (
            'model = "custom"\n\n'
            "[agents]\n"
            "enabled = true\n"
            "max_concurrent_threads_per_session = 20\n"
            "keep_agent = true\n\n"
            "[features]\n"
            "multi_agent = true\n"
            'keep_feature = "keep"\n\n'
            "[features.multi_agent_v2]\n"
            "enabled = true\n"
            "default_wait_timeout_ms = 300_000\n"
            'keep_legacy = "keep"\n'
        )
        rendered = remove_workflow_owned_settings(original)
        self.assertIn('model = "custom"', rendered)
        self.assertIn("keep_agent = true", rendered)
        self.assertIn('keep_feature = "keep"', rendered)
        self.assertIn('keep_legacy = "keep"', rendered)
        self.assertNotIn("max_concurrent_threads_per_session", rendered)
        self.assertIn("[agents]", rendered)
        self.assertNotIn("enabled = true", rendered)
        self.assertNotIn("multi_agent = true", rendered)
        self.assertNotIn("default_wait_timeout_ms", rendered)

    def test_fixed_route_and_worker_need_no_settings_rendering(self) -> None:
        heavy = (PACKAGE / "heavy_route.md").read_text(encoding="utf-8")
        default = (PACKAGE / "agents" / "default_executor.toml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("codex-workflow-effective-config", heavy)
        self.assertNotIn("Fixed Workflow Settings", heavy)
        self.assertIn('model_reasoning_effort = "max"', default)
        self.assertIn(
            'fork_turns="200"',
            (PACKAGE / "archivist.md").read_text(encoding="utf-8"),
        )


class ReleaseTests(unittest.TestCase):
    def _archive_without(self, relative: str) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name) / "source.zip"
        target = Path(temporary.name) / "modified.zip"
        build_zip(PACKAGE, source)
        excluded = f"codex_workflow/{relative}"
        with zipfile.ZipFile(source) as input_archive, zipfile.ZipFile(
            target, "w", compression=zipfile.ZIP_DEFLATED
        ) as output_archive:
            for member in input_archive.infolist():
                if member.filename == excluded:
                    continue
                output_archive.writestr(member, input_archive.read(member.filename))
        return target

    def test_archive_requires_complete_builtin_worker_set(self) -> None:
        names = ["codex_workflow"]
        names.extend(
            f"codex_workflow/{path.relative_to(PACKAGE).as_posix()}"
            for path in PACKAGE.rglob("*")
        )
        names = [
            name
            for name in names
            if name
            not in {
                "codex_workflow/agents/tester.toml",
                "codex_workflow/agents/archivist.toml",
            }
        ]
        with self.assertRaisesRegex(PackageReleaseError, "archive is missing"):
            _verify_member_names(names)

    def test_archive_rejects_unsupported_worker_role(self) -> None:
        names = ["codex_workflow"]
        names.extend(
            f"codex_workflow/{path.relative_to(PACKAGE).as_posix()}"
            for path in PACKAGE.rglob("*")
        )
        names.append("codex_workflow/agents/unexpected.toml")
        with self.assertRaisesRegex(
            PackageReleaseError, "archive contains unsupported worker roles"
        ):
            _verify_member_names(names)

    def test_archive_verification_runs_the_full_package_validator(self) -> None:
        for missing in ("AGENTS.md", "project_docs/project_diary.md"):
            with self.subTest(missing=missing):
                with self.assertRaisesRegex(
                    PackageReleaseError, "workflow package validation failed"
                ):
                    verify_archive(self._archive_without(missing))

    def test_archive_rejects_retired_wave_barrier(self) -> None:
        names = ["codex_workflow"]
        names.extend(
            f"codex_workflow/{path.relative_to(PACKAGE).as_posix()}"
            for path in PACKAGE.rglob("*")
        )
        names.append("codex_workflow/agents/wave_barrier.toml")
        with self.assertRaisesRegex(PackageReleaseError, "retired worker roles"):
            _verify_member_names(names)

    def test_archive_does_not_require_retired_orchestration_guides(self) -> None:
        names = ["codex_workflow"]
        names.extend(
            f"codex_workflow/{path.relative_to(PACKAGE).as_posix()}"
            for path in PACKAGE.rglob("*")
        )
        for guide in (
            "medium_companion.md",
            "heavy_companion.md",
            "investigation_team.md",
        ):
            self.assertNotIn(f"codex_workflow/{guide}", names)
        _verify_member_names(names)

    def test_archive_verification_rejects_duplicate_members(self) -> None:
        archive = self._archive_without("not-present")
        with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("codex_workflow/operate/VERSION", PACKAGE_VERSION + "\n")
        with self.assertRaisesRegex(PackageReleaseError, "duplicate members"):
            verify_archive(archive)

    def test_update_rejects_equal_or_older_package_before_delegation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "codex-home" / "codex_workflow"
            runtime.mkdir(parents=True)
            (runtime / "VERSION").write_text("1.1.4\n", encoding="utf-8")
            incoming = root / "incoming"
            incoming.mkdir()
            project = root / "project"
            project.mkdir()
            for version, expected_error in (
                ("1.1.4", "matches the installed version"),
                ("1.1.3", "incoming version is older"),
            ):
                with self.subTest(version=version):
                    (incoming / "VERSION").write_text(version + "\n", encoding="utf-8")
                    output = io.StringIO()
                    argv = [
                        "workflow.py",
                        "update",
                        "--source",
                        str(incoming),
                        "--codex-home",
                        str(root / "codex-home"),
                        "--project",
                        str(project),
                        "--json",
                    ]
                    with (
                        mock.patch.object(sys, "argv", argv),
                        mock.patch.object(
                            workflow_cli,
                            "_delegate_update",
                            side_effect=AssertionError("delegation must not occur"),
                        ),
                        contextlib.redirect_stdout(output),
                    ):
                        self.assertEqual(workflow_cli.main(), 1)
                    self.assertIn(expected_error, json.loads(output.getvalue())["error"])

    def test_check_update_reports_new_release_notes_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "codex-home"
            runtime = home / "codex_workflow"
            runtime.mkdir(parents=True)
            (runtime / "VERSION").write_text("1.1.1\n", encoding="utf-8")
            release = ReleaseSelection(
                "1.2.0",
                parse_semver("1.2.0"),
                "codex_workflow-1.2.0.zip",
                "https://example/1.2.0.zip",
                "https://example/SHA256SUMS",
                "## Changes\n- Add release-note summaries.",
                "https://example/releases/1.2.0",
            )
            output = io.StringIO()
            argv = ["workflow.py", "check-update", "--codex-home", str(home), "--json"]
            with (
                mock.patch.object(workflow_cli, "select_releases", return_value=[release]),
                mock.patch.object(sys, "argv", argv),
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(workflow_cli.main(), 0)
            summary = json.loads(output.getvalue())
            self.assertEqual(summary["status"], "update available")
            self.assertEqual(summary["updates"][0]["version"], "1.2.0")
            self.assertIn("release-note summaries", summary["summary"])
            self.assertEqual((runtime / "VERSION").read_text(), "1.1.1\n")

    def test_select_releases_keeps_installable_versions_and_notes(self) -> None:
        records = [
            {
                "tag_name": "v1.3.0",
                "draft": False,
                "body": "## Changes\n- Add explicit update summaries.",
                "html_url": "https://github.com/example/releases/1.3.0",
                "assets": [
                    {
                        "name": "codex_workflow-1.3.0.zip",
                        "browser_download_url": "https://example/1.3.0.zip",
                    },
                    {"name": "SHA256SUMS", "browser_download_url": "https://example/sums"},
                ],
            },
            {
                "tag_name": "v1.2.0",
                "draft": False,
                "body": "- Older change",
                "assets": [
                    {
                        "name": "codex_workflow-1.2.0.zip",
                        "browser_download_url": "https://example/1.2.0.zip",
                    },
                    {"name": "SHA256SUMS", "browser_download_url": "https://example/sums"},
                ],
            },
            {"tag_name": "v1.4.0", "draft": True, "assets": []},
        ]
        with mock.patch("runtime.release._read_json_url", return_value=records):
            releases = select_releases()
        self.assertEqual([release.version_text for release in releases], ["1.3.0", "1.2.0"])
        self.assertIn("explicit update summaries", releases[0].release_notes)

    def test_release_note_summary_strips_markdown_and_limits_length(self) -> None:
        summary = summarize_release_notes(
            "## Changes\n- `check-update` now reports [notes](https://example)."
        )
        self.assertEqual(summary, "Changes check-update now reports notes.")
        self.assertEqual(
            summarize_release_notes("", max_length=10),
            "No release notes were provided.",
        )


class TransactionTests(unittest.TestCase):
    def test_failed_transaction_restores_all_targets(self) -> None:
        from runtime import transaction

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"
            first.write_bytes(b"old")
            original_write = transaction._atomic_write
            calls = 0

            def fail_once(path: Path, content: bytes, mode: int) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected failure")
                original_write(path, content, mode)

            with mock.patch("runtime.transaction._atomic_write", side_effect=fail_once):
                with self.assertRaises(TransactionError):
                    apply([Mutation(first, b"new"), Mutation(second, b"created")])
            self.assertEqual(first.read_bytes(), b"old")
            self.assertFalse(second.exists())


class LifecycleIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.codex_home = self.root / "codex-home"
        self.project_root = self.root / "project"
        self.project_root.mkdir()
        self.runtime = RuntimePaths(self.codex_home)
        self.project = ProjectPaths(self.project_root)
        self.package = PackageLayout.resolve(PACKAGE)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def bootstrap(self, *, existing_agents: str | None = None) -> OperationPlan:
        if existing_agents is not None:
            self.project.active.write_text(existing_agents, encoding="utf-8")
        plan = plan_bootstrap(self.package, self.runtime, self.project)
        self.assertFalse(self.codex_home.exists())
        plan.apply()
        return plan

    def incoming_package(self, directory: str, version: str | None = None) -> PackageLayout:
        version = version or PACKAGE_VERSION
        incoming_root = self.root / directory / "codex_workflow"
        shutil.copytree(
            PACKAGE,
            incoming_root,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        (incoming_root / "operate" / "VERSION").write_text(f"{version}\n", encoding="utf-8")
        user_agents = (incoming_root / "operate" / "user_AGENTS.md").read_text(encoding="utf-8")
        (incoming_root / "operate" / "user_AGENTS.md").write_text(
            user_agents.replace(
                f"codex-workflow-version: {PACKAGE_VERSION}",
                f"codex-workflow-version: {version}",
            ),
            encoding="utf-8",
        )
        return PackageLayout.resolve(incoming_root)

    def test_bootstrap_imports_existing_agents_and_materializes_runtime(self) -> None:
        plan = self.bootstrap(
            existing_agents="# Existing instructions\nKeep local policy.\n"
        )
        entry = self.project.active.read_text(encoding="utf-8")
        self.assertEqual(
            extract(entry, PROJECT_LOCAL),
            "# Existing instructions\nKeep local policy.",
        )
        self.assertTrue((self.runtime.runtime / "runtime" / "workflow.py").is_file())
        self.assertTrue((self.runtime.runtime / "templates" / "AGENTS.md").is_file())
        self.assertTrue((self.runtime.agents / "default_executor.toml").is_file())
        self.assertTrue((self.runtime.agents / "senior_executor.toml").is_file())
        self.assertTrue((self.runtime.agents / "investigator.toml").is_file())
        self.assertFalse((self.runtime.agents / "wave_barrier.toml").exists())
        self.assertFalse((self.runtime.agents / "executor_terra.toml").exists())
        self.assertTrue((self.runtime.agents / "archivist.toml").is_file())
        self.assertTrue((self.runtime.agents / "companion.toml").is_file())
        self.assertTrue(
            (
                self.runtime.skills
                / "deployment-token-report"
                / "scripts"
                / "report_tokens.py"
            ).is_file()
        )
        self.assertTrue(
            (
                self.runtime.runtime
                / "templates"
                / "skills"
                / "deployment-token-report"
                / "SKILL.md"
            ).is_file()
        )
        self.assertNotIn(
            "max_concurrent_threads_per_session",
            self.runtime.config_toml.read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "[features.multi_agent_v2]",
            self.runtime.config_toml.read_text(encoding="utf-8"),
        )
        self.assertEqual(len(plan.agent_actions), 1)
        action = plan.agent_actions[0]
        self.assertEqual(action["role"], "archivist")
        self.assertTrue(action["required"])
        self.assertEqual(
            action["documentation_root"],
            str((self.project.root / "agent_docs").resolve()),
        )
        self.assertEqual(set(action["files"]), set(action["framework"]))
        self.assertEqual(
            action["required_context_files"],
            [
                "project_structure.md",
                "project_overview.md",
                "project_core_tech.md",
            ],
        )

        repeated = plan_project_install(self.package, self.project)
        self.assertEqual(len(repeated.agent_actions), 1)
        self.assertTrue(repeated.agent_actions[0]["required"])
        self.assertEqual(
            set(repeated.agent_actions[0]["files"]),
            set(repeated.agent_actions[0]["framework"]),
        )
        self.assertEqual(repeated.agent_actions[0]["created_files"], [])
        self.assertEqual(
            set(repeated.agent_actions[0]["recovery_files"]),
            set(repeated.agent_actions[0]["framework"]),
        )

    def test_bootstrap_rejects_unowned_skill_collision(self) -> None:
        collision = self.runtime.skills / "deployment-token-report"
        collision.mkdir(parents=True)
        (collision / "SKILL.md").write_text(
            "---\nname: deployment-token-report\ndescription: local\n---\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValidationError, "unowned skill directory"):
            plan_bootstrap(self.package, self.runtime, self.project)

    def test_bootstrap_cleans_staging_and_keeps_agent_docs_trackable(self) -> None:
        staging = self.project_root / "Codex_Workflow"
        (staging / "nested").mkdir(parents=True)
        (staging / "nested" / "package.txt").write_text("staged", encoding="utf-8")
        (self.project_root / ".gitignore").write_text("# local rules\n", encoding="utf-8")

        self.bootstrap()

        self.assertFalse(staging.exists())
        gitignore = (self.project_root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("# local rules\n", gitignore)
        self.assertNotIn("agent_docs/", gitignore)
        for entry in (
            ".codex_workflow_hidden_resources/",
            "AGENTS.md",
        ):
            self.assertEqual(gitignore.splitlines().count(entry), 1)
        self.assertIn("# codex-workflow-managed-start", gitignore)
        self.assertIn("# codex-workflow-managed-end", gitignore)

        # A repeated project install is idempotent and does not duplicate rules.
        plan_project_install(self.package, self.project).apply()
        repeated = (self.project_root / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("agent_docs/", repeated)
        for entry in (
            ".codex_workflow_hidden_resources/",
            "AGENTS.md",
        ):
            self.assertEqual(repeated.splitlines().count(entry), 1)

    def test_remove_restores_project_local_instructions_and_gitignore(self) -> None:
        self.bootstrap(existing_agents="# Original project instructions\nKeep this.\n")
        self.project.docs.mkdir(exist_ok=True)
        preserved_document = self.project.docs / "project_overview.md"
        preserved_document.write_text("Project documentation\n", encoding="utf-8")
        gitignore = self.project_root / ".gitignore"
        gitignore.write_text(
            "# local rule\nlocal-output/\n\n"
            + gitignore.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        plan_remove(self.runtime, self.project).apply()

        self.assertEqual(
            self.project.active.read_text(encoding="utf-8"),
            "# Original project instructions\nKeep this.\n",
        )
        self.assertTrue(preserved_document.is_file())
        remaining_gitignore = gitignore.read_text(encoding="utf-8")
        self.assertIn("# local rule\nlocal-output/\n", remaining_gitignore)
        self.assertNotIn("# codex-workflow-managed-start", remaining_gitignore)
        for entry in (
            "agent_docs/",
            ".codex_workflow_hidden_resources/",
            "AGENTS.md",
        ):
            self.assertNotIn(entry, remaining_gitignore)

    def test_install_preserves_user_owned_agent_docs_ignore(self) -> None:
        self.project.gitignore.write_text("agent_docs/\n", encoding="utf-8")

        self.bootstrap()

        gitignore = self.project.gitignore.read_text(encoding="utf-8")
        self.assertEqual(gitignore.splitlines().count("agent_docs/"), 1)
        self.assertLess(
            gitignore.splitlines().index("agent_docs/"),
            gitignore.splitlines().index("# codex-workflow-managed-start"),
        )

    def test_new_install_preserves_user_owned_legacy_shaped_ignore(self) -> None:
        self.project.gitignore.write_text(
            "agent_docs/\n.codex_workflow_hidden_resources/\nAGENTS.md\n",
            encoding="utf-8",
        )

        self.bootstrap()

        gitignore = self.project.gitignore.read_text(encoding="utf-8")
        for entry in (
            "agent_docs/",
            ".codex_workflow_hidden_resources/",
            "AGENTS.md",
        ):
            self.assertEqual(gitignore.splitlines().count(entry), 1)
        self.assertNotIn("# codex-workflow-managed-start", gitignore)

    def test_install_retires_legacy_unmarked_agent_docs_ignore(self) -> None:
        self.bootstrap()
        self.project.gitignore.write_text(
            "# local\nagent_docs/\n.codex_workflow_hidden_resources/\nAGENTS.md\n",
            encoding="utf-8",
        )

        plan_project_install(self.package, self.project).apply()

        gitignore = self.project.gitignore.read_text(encoding="utf-8")
        self.assertIn("# local\n", gitignore)
        self.assertNotIn("agent_docs/", gitignore)
        self.assertIn("# codex-workflow-managed-start", gitignore)
        self.assertIn("# codex-workflow-managed-end", gitignore)

    def test_remove_restores_project_local_instructions_from_disabled_entry(self) -> None:
        self.bootstrap(existing_agents="# Original project instructions\nKeep this.\n")
        plan_enable(self.project, enable=False).apply()
        self.assertFalse(self.project.active.exists())
        self.assertTrue(self.project.disabled.exists())

        plan_remove(self.runtime, self.project).apply()

        self.assertEqual(
            self.project.active.read_text(encoding="utf-8"),
            "# Original project instructions\nKeep this.\n",
        )
        self.assertFalse(self.project.disabled.exists())
        self.assertFalse(self.project.workflow_dir.exists())

    def test_unactivated_workers_are_materialized_for_codex(self) -> None:
        self.bootstrap()
        for worker in self.package.worker_names:
            self.assertTrue((self.runtime.agents / f"{worker}.toml").is_file())
            self.assertTrue(
                (self.runtime.runtime / "templates" / "agents" / f"{worker}.toml").is_file()
            )
        state = json.loads((self.runtime.runtime / "install_state.json").read_text())
        self.assertEqual(set(state["owned_workers"]), self.package.worker_names)
        self.assertEqual(set(state["owned_skills"]), self.package.skill_names)
        self.assertEqual(state["projects"], [str(self.project_root.resolve())])

    def test_project_install_registers_each_project(self) -> None:
        self.bootstrap()
        second_root = self.root / "second-project"
        second_root.mkdir()
        second = ProjectPaths(second_root)

        plan_install(self.package, self.runtime, second).apply()

        registered = read_registered_projects(self.runtime)
        self.assertIsNotNone(registered)
        self.assertEqual(
            {project.root for project in registered or []},
            {self.project_root.resolve(), second_root.resolve()},
        )

    def test_registry_rejects_empty_project_sets(self) -> None:
        self.bootstrap()
        state_path = self.runtime.runtime / "install_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["projects"] = []
        state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")

        with self.assertRaisesRegex(ValidationError, "at least one project"):
            read_registered_projects(self.runtime)

        supplied = migration_file(self.runtime)
        supplied.write_text("\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "at least one absolute path"):
            read_project_list(supplied)

    def test_one_update_updates_every_registered_project(self) -> None:
        self.bootstrap()
        second_root = self.root / "second-project"
        second_root.mkdir()
        second = ProjectPaths(second_root)
        plan_install(self.package, self.runtime, second).apply()

        incoming = self.incoming_package("all-projects-incoming", "1.2.0")
        template = incoming.project_template.read_text(encoding="utf-8")
        incoming.project_template.write_text(
            template.replace("## Working State", "## Working State (all projects)"),
            encoding="utf-8",
        )
        incoming = PackageLayout.resolve(incoming.root)
        registered = read_registered_projects(self.runtime)
        assert registered is not None

        plan = plan_update(incoming, self.runtime, registered)
        plan.apply()

        self.assertEqual(
            set(plan.details["projects"]),
            {str(self.project_root.resolve()), str(second_root.resolve())},
        )
        for project in (self.project, second):
            self.assertIn(
                "## Working State (all projects)",
                project.active.read_text(encoding="utf-8"),
            )
            state = json.loads(project.state.read_text(encoding="utf-8"))
            self.assertEqual(state["workflow_version"], "1.2.0")

    def test_registry_migration_requires_user_project_paths(self) -> None:
        self.bootstrap()
        state_path = self.runtime.runtime / "install_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.pop("projects")
        state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
        incoming = self.incoming_package(
            "registry-input-incoming", NEXT_PACKAGE_VERSION
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(incoming.root / "runtime" / "workflow.py"),
                "update",
                "--source",
                str(incoming.root),
                "--codex-home",
                str(self.codex_home),
                "--project",
                str(self.project_root),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 1)
        result = json.loads(completed.stdout)
        self.assertTrue(result["input_required"])
        self.assertTrue(result["requires_fresh_user_reply"])
        self.assertIn("Stop this turn", result["agent_instruction"])
        self.assertIn("Do not infer", result["agent_instruction"])
        self.assertIn("every project", result["prompt"])
        self.assertEqual(result["input_file"], str(migration_file(self.runtime)))

    def test_registry_migration_updates_supplied_projects_and_removes_input(self) -> None:
        self.bootstrap()
        second_root = self.root / "second-project"
        second_root.mkdir()
        second = ProjectPaths(second_root)
        plan_project_install(self.package, second).apply()
        state_path = self.runtime.runtime / "install_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.pop("projects")
        state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
        supplied = migration_file(self.runtime)
        supplied.write_text(
            f"{self.project_root.resolve()}\n{second_root.resolve()}\n",
            encoding="utf-8",
        )
        incoming = self.incoming_package(
            "registry-migration-incoming", NEXT_PACKAGE_VERSION
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(incoming.root / "runtime" / "workflow.py"),
                "update",
                "--source",
                str(incoming.root),
                "--codex-home",
                str(self.codex_home),
                "--project",
                str(self.project_root),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertFalse(supplied.exists())
        result = json.loads(completed.stdout)
        self.assertEqual(
            set(result["details"]["projects"]),
            {str(self.project_root.resolve()), str(second_root.resolve())},
        )

    def test_stage_update_persists_verified_package_and_returns_guide(self) -> None:
        self.bootstrap()
        download = tempfile.TemporaryDirectory()
        downloaded_package = Path(download.name) / "codex_workflow"
        shutil.copytree(
            PACKAGE,
            downloaded_package,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        selection = ReleaseSelection(
            NEXT_PACKAGE_VERSION,
            parse_semver(NEXT_PACKAGE_VERSION),
            f"codex_workflow-{NEXT_PACKAGE_VERSION}.zip",
            "https://example.invalid/workflow.zip",
            "https://example.invalid/SHA256SUMS",
        )

        with mock.patch.object(
            workflow_cli, "acquire", return_value=(download, downloaded_package)
        ):
            staged, guide = workflow_cli._stage_update(selection, self.runtime)

        self.assertTrue(staged.is_dir())
        self.assertEqual(guide, staged / "operate" / "update.md")
        self.assertTrue(guide.is_file())
        self.assertFalse(Path(download.name).exists())

    def test_multi_project_update_rejects_unknown_target_before_writes(self) -> None:
        self.bootstrap()
        unknown_root = self.root / "unknown-project"
        unknown_root.mkdir()
        incoming = self.incoming_package("unknown-project-incoming", "1.2.0")
        installed_version = (
            self.runtime.runtime / "operate" / "VERSION"
        ).read_text(encoding="utf-8")

        with self.assertRaisesRegex(ValidationError, "registered project"):
            plan_update(
                incoming,
                self.runtime,
                [self.project, ProjectPaths(unknown_root)],
            )

        self.assertEqual(
            (self.runtime.runtime / "operate" / "VERSION").read_text(
                encoding="utf-8"
            ),
            installed_version,
        )

    def test_personalize_and_enable_disable_preserve_regions(self) -> None:
        self.bootstrap(existing_agents="Local policy.\n")
        customized = (PACKAGE / "resources" / "personalization.md").read_text(
            encoding="utf-8"
        ).replace(
            "Status: default\nDecision: Preserve the workflow-managed default Design Principles.",
            "Status: customized\nDecision: Prefer explicit ports and adapters.",
        )
        plan_personalize(self.project, customized).apply()
        entry = self.project.active.read_text(encoding="utf-8")
        self.assertEqual(extract(entry, PROJECT_PERSONALIZATION), "Prefer explicit ports and adapters.")
        self.assertEqual(extract(entry, PROJECT_LOCAL), "Local policy.")
        plan_enable(self.project, enable=False).apply()
        self.assertFalse(self.project.active.exists())
        self.assertTrue(self.project.disabled.exists())
        plan_enable(self.project, enable=True).apply()
        self.assertTrue(self.project.active.exists())
        self.assertFalse(self.project.disabled.exists())

        self.project.personalization.unlink()
        defaults = (PACKAGE / "resources" / "personalization.md").read_text(
            encoding="utf-8"
        )
        plan_personalize(self.project, defaults).apply()
        self.assertEqual(self.project.personalization.read_text(encoding="utf-8"), defaults)
        self.assertEqual(
            extract(self.project.active.read_text(encoding="utf-8"), PROJECT_PERSONALIZATION),
            "",
        )

    def test_install_rejects_personalization_resource_drift(self) -> None:
        self.bootstrap()
        resource = self.project.personalization.read_text(encoding="utf-8")
        self.project.personalization.write_text(
            resource.replace(
                "Status: default\nDecision: Preserve the workflow-managed default Design Principles.",
                "Status: customized\nDecision: Prefer explicit ports and adapters.",
            ),
            encoding="utf-8",
        )
        with self.assertRaises(ValidationError):
            plan_project_install(self.package, self.project)

    def test_update_restores_workers_and_preserves_project_state(self) -> None:
        self.bootstrap(existing_agents="Local policy.\n")
        gitignore = self.project.gitignore
        gitignore.write_text(
            gitignore.read_text(encoding="utf-8").replace(
                "# codex-workflow-managed-start\n",
                "# codex-workflow-managed-start\nagent_docs/\n",
            ),
            encoding="utf-8",
        )
        (self.runtime.agents / "default_executor.toml").write_text(
            "# local worker override\n", encoding="utf-8"
        )
        incoming_root = self.root / "incoming" / "codex_workflow"
        shutil.copytree(PACKAGE, incoming_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (incoming_root / "operate" / "VERSION").write_text(
            f"{NEXT_PACKAGE_VERSION}\n", encoding="utf-8"
        )
        user_agents = (incoming_root / "operate" / "user_AGENTS.md").read_text(encoding="utf-8")
        (incoming_root / "operate" / "user_AGENTS.md").write_text(
            user_agents.replace(
                f"codex-workflow-version: {PACKAGE_VERSION}",
                f"codex-workflow-version: {NEXT_PACKAGE_VERSION}",
            ),
            encoding="utf-8",
        )
        incoming = PackageLayout.resolve(incoming_root)
        plan_update(incoming, self.runtime, self.project).apply()
        entry = self.project.active.read_text(encoding="utf-8")
        self.assertEqual(extract(entry, PROJECT_LOCAL), "Local policy.")
        self.assertEqual(
            (self.runtime.runtime / "operate" / "VERSION").read_text(),
            f"{NEXT_PACKAGE_VERSION}\n",
        )
        self.assertNotIn(
            "local worker override",
            (self.runtime.agents / "default_executor.toml").read_text(encoding="utf-8"),
        )
        updated_gitignore = gitignore.read_text(encoding="utf-8")
        self.assertNotIn("agent_docs/", updated_gitignore)
        self.assertIn(".codex_workflow_hidden_resources/", updated_gitignore)
        self.assertIn("AGENTS.md", updated_gitignore)
        installed_skill = self.runtime.skills / "deployment-token-report"
        self.assertEqual(
            (installed_skill / "SKILL.md").read_text(encoding="utf-8"),
            (PACKAGE / "skills" / "deployment-token-report" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
        )
        self.assertTrue(any((self.runtime.runtime / ".backups").iterdir()))

    def test_update_removes_retired_orchestration_guides(self) -> None:
        self.bootstrap()
        retired = (
            "companion.md",
            "medium_companion.md",
            "heavy_companion.md",
            "investigation_team.md",
        )
        for relative in retired:
            (self.runtime.runtime / relative).write_text(
                "# Retired orchestration guide\n", encoding="utf-8"
            )
        state_path = self.runtime.runtime / "install_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["owned_runtime_files"].extend(retired)
        state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")

        incoming = self.incoming_package("capability-routes-incoming", "1.2.0")
        plan_update(incoming, self.runtime, self.project).apply()

        for relative in retired:
            self.assertFalse((self.runtime.runtime / relative).exists())

    def test_update_restores_owned_skill_and_removes_stale_skill_files(self) -> None:
        self.bootstrap()
        installed_skill = self.runtime.skills / "deployment-token-report"
        (installed_skill / "SKILL.md").write_text(
            (installed_skill / "SKILL.md")
            .read_text(encoding="utf-8")
            .replace("Compile per-agent", "Locally changed per-agent"),
            encoding="utf-8",
        )
        stale = installed_skill / "stale.txt"
        stale.write_text("stale", encoding="utf-8")
        incoming = self.incoming_package("skill-update-incoming", "1.2.0")
        plan = plan_update(incoming, self.runtime, self.project)
        backup = Path(plan.details["backup"])
        plan.apply()
        self.assertEqual(
            (installed_skill / "SKILL.md").read_text(encoding="utf-8"),
            (incoming.skill_templates / "deployment-token-report" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
        )
        self.assertFalse(stale.exists())
        self.assertTrue(
            (
                backup
                / "user"
                / "skills"
                / "deployment-token-report"
                / "SKILL.md"
            ).is_file()
        )

    def test_projects_update_against_their_recorded_historical_sources(self) -> None:
        self.bootstrap()
        second_root = self.root / "second-project"
        second_root.mkdir()
        second = ProjectPaths(second_root)
        plan_project_install(self.package, second).apply()

        incoming = self.incoming_package("multi-project-incoming", "1.2.0")
        incoming_template = incoming.project_template.read_text(encoding="utf-8")
        incoming.project_template.write_text(
            incoming_template.replace("## Working State", "## Working State (1.2)"),
            encoding="utf-8",
        )
        incoming = PackageLayout.resolve(incoming.root)

        plan_update(incoming, self.runtime, self.project).apply()
        second_plan = plan_update(incoming, self.runtime, second)
        self.assertEqual(second_plan.details["from_version"], "1.2.0")
        self.assertEqual(second_plan.details["project_from_version"], PACKAGE_VERSION)
        second_plan.apply()
        self.assertIn(
            "## Working State (1.2)", second.active.read_text(encoding="utf-8")
        )

    def test_update_removes_retired_architecture_assets(self) -> None:
        self.bootstrap()
        state_path = self.runtime.runtime / "install_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        retired_verification_utility = self.runtime.runtime / "verification_ledger.py"
        retired_verification_utility.write_text("# retired\n", encoding="utf-8")
        state["owned_runtime_files"].append("verification_ledger.py")
        for legacy_worker in (
            "executor_luna",
            "executor_sol",
            "executor_terra",
            "explorer",
            "end_of_session",
            "wave_barrier",
        ):
            (self.runtime.agents / f"{legacy_worker}.toml").write_text(
                f"# codex-workflow-worker: {legacy_worker}\n",
                encoding="utf-8",
            )
            (self.runtime.runtime / "templates" / "agents" / f"{legacy_worker}.toml").write_text(
                f"# codex-workflow-worker: {legacy_worker}\n",
                encoding="utf-8",
            )
            state["owned_workers"].append(legacy_worker)
        state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")

        incoming = self.incoming_package("worker-migration-incoming", "1.2.0")
        plan_update(incoming, self.runtime, self.project).apply()
        self.assertFalse(retired_verification_utility.exists())
        for legacy_worker in (
            "executor_luna",
            "executor_sol",
            "executor_terra",
            "explorer",
            "end_of_session",
            "wave_barrier",
        ):
            self.assertFalse((self.runtime.agents / f"{legacy_worker}.toml").exists())
            self.assertFalse(
                (
                    self.runtime.runtime
                    / "templates"
                    / "agents"
                    / f"{legacy_worker}.toml"
                ).exists()
            )
        PackageLayout.resolve(self.runtime.runtime)

    def test_cli_install_reports_enabled_disabled_and_stale_states(self) -> None:
        self.bootstrap()
        command = [
            sys.executable,
            "-B",
            str(self.runtime.runtime / "runtime" / "workflow.py"),
            "install",
            "--codex-home",
            str(self.codex_home),
            "--project",
            str(self.project_root),
            "--json",
        ]
        recovery = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(recovery.returncode, 0, recovery.stderr)
        recovery_summary = json.loads(recovery.stdout)
        self.assertTrue(recovery_summary["applied"])
        self.assertEqual(
            set(recovery_summary["agent_actions"][0]["recovery_files"]),
            set(recovery_summary["agent_actions"][0]["framework"]),
        )
        for document in self.project.docs.glob("*.md"):
            document.write_text(
                document.read_text(encoding="utf-8").replace(
                    "<!-- codex-workflow-bootstrap-template -->\n", ""
                ),
                encoding="utf-8",
            )

        enabled = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(enabled.returncode, 0, enabled.stderr)
        self.assertEqual(json.loads(enabled.stdout)["status"], "already enabled")
        self.assertEqual(json.loads(enabled.stdout)["instruction"], "No action is required.")

        self.project.state.unlink()
        self.project.personalization.unlink()
        self.project.gitignore.unlink()
        repaired = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(repaired.returncode, 0, repaired.stderr)
        repaired_summary = json.loads(repaired.stdout)
        self.assertTrue(repaired_summary["applied"])
        self.assertEqual(repaired_summary["agent_actions"][0]["files"], [])
        self.assertTrue(self.project.state.is_file())
        self.assertTrue(self.project.personalization.is_file())
        self.assertTrue(self.project.gitignore.is_file())

        plan_enable(self.project, enable=False).apply()
        disabled = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(disabled.returncode, 0, disabled.stderr)
        self.assertEqual(json.loads(disabled.stdout)["status"], "already disabled")
        self.assertIn("--enable", json.loads(disabled.stdout)["instruction"])

        plan_enable(self.project, enable=True).apply()
        text = self.project.active.read_text(encoding="utf-8")
        self.project.active.write_text(
            text.replace("## Working State", "## Locally Changed Working State"),
            encoding="utf-8",
        )
        stale = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(stale.returncode, 1)
        self.assertIn("--update", json.loads(stale.stdout)["error"])

    def test_update_preserves_disabled_project_state(self) -> None:
        self.bootstrap()
        plan_enable(self.project, enable=False).apply()
        plan_update(
            self.incoming_package("disabled-incoming"),
            self.runtime,
            self.project,
        ).apply()
        self.assertFalse(self.project.active.exists())
        self.assertTrue(self.project.disabled.exists())
        state = json.loads(self.project.state.read_text(encoding="utf-8"))
        self.assertFalse(state["enabled"])

    def test_cli_install_applies_without_confirmation_flag(self) -> None:
        project_root = self.root / "cli-project"
        project_root.mkdir()
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(PACKAGE / "runtime" / "workflow.py"),
                "install",
                "--package-root",
                str(PACKAGE),
                "--codex-home",
                str(self.codex_home),
                "--project",
                str(project_root),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertTrue(summary["applied"])
        self.assertEqual(len(summary["agent_actions"]), 1)
        self.assertTrue(summary["agent_actions"][0]["required"])
        self.assertEqual(
            summary["agent_actions"][0]["required_context_files"],
            [
                "project_structure.md",
                "project_overview.md",
                "project_core_tech.md",
            ],
        )
        self.assertTrue((project_root / "AGENTS.md").is_file())

    def test_remove_requires_second_confirmation_and_cleans_owned_files(self) -> None:
        self.bootstrap(existing_agents="Local policy.\n")
        legacy_resource = (
            self.project.hidden_dir
            / "deployments"
            / "feature_a"
            / "verification"
            / "record.json"
        )
        legacy_resource.parent.mkdir(parents=True)
        legacy_resource.write_text("{}\n", encoding="utf-8")
        user_agents = self.runtime.user_agents.read_text(encoding="utf-8")
        self.runtime.user_agents.write_text(
            "# Keep this user policy.\n\n" + user_agents,
            encoding="utf-8",
        )
        config = self.runtime.config_toml.read_text(encoding="utf-8")
        config = config.replace(
            "[agents]\nenabled = true",
            "[agents]\nenabled = true\nkeep_agent = true",
        )
        config = config.replace(
            "[features]\nmulti_agent = true",
            '[features]\nmulti_agent = true\nkeep_feature = "keep"',
        )
        self.runtime.config_toml.write_text(
            'model = "keep"\n\n' + config,
            encoding="utf-8",
        )
        unrelated_worker = self.runtime.agents / "unrelated.toml"
        unrelated_worker.write_text('model = "keep"\n', encoding="utf-8")
        unrelated_skill = self.runtime.skills / "unrelated-skill"
        unrelated_skill.mkdir(parents=True)
        (unrelated_skill / "SKILL.md").write_text(
            "---\nname: unrelated-skill\ndescription: keep\n---\n",
            encoding="utf-8",
        )

        command = [
            sys.executable,
            "-B",
            str(self.runtime.runtime / "runtime" / "workflow.py"),
            "remove",
            "--codex-home",
            str(self.codex_home),
            "--project",
            str(self.project_root),
            "--json",
        ]
        planned = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(planned.returncode, 0, planned.stderr)
        planned_summary = json.loads(planned.stdout)
        self.assertFalse(planned_summary["applied"])
        self.assertTrue(planned_summary["confirmation_required"])
        self.assertTrue(
            any("legacy project workflow resources" in warning for warning in planned_summary["warnings"])
        )
        self.assertTrue(self.project.active.is_file())
        self.assertTrue(self.runtime.runtime.is_dir())

        confirmed = subprocess.run(
            [*command[:-1], "--confirm", "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
        self.assertTrue(json.loads(confirmed.stdout)["applied"])
        self.assertEqual(self.project.active.read_text(encoding="utf-8"), "Local policy.\n")
        self.assertFalse(self.project.hidden_dir.exists())
        self.assertTrue((self.project.docs / "project_overview.md").is_file())
        self.assertFalse(self.runtime.runtime.exists())
        self.assertTrue(unrelated_worker.is_file())
        self.assertTrue((unrelated_skill / "SKILL.md").is_file())
        self.assertFalse(
            (self.runtime.skills / "deployment-token-report").exists()
        )
        self.assertEqual(
            self.runtime.user_agents.read_text(encoding="utf-8"),
            "# Keep this user policy.\n",
        )
        remaining_config = self.runtime.config_toml.read_text(encoding="utf-8")
        self.assertIn('model = "keep"', remaining_config)
        self.assertIn("keep_agent = true", remaining_config)
        self.assertIn('keep_feature = "keep"', remaining_config)
        self.assertNotIn("max_concurrent_threads_per_session", remaining_config)

    def test_update_allows_missing_optional_codex_config(self) -> None:
        self.bootstrap()
        self.runtime.config_toml.unlink()
        plan = plan_update(
            self.incoming_package("missing-config-incoming"),
            self.runtime,
            self.project,
        )
        self.assertEqual(plan.operation, "update")

    def test_update_rejects_unsafe_owned_runtime_state(self) -> None:
        self.bootstrap()
        outside = self.root / "outside.txt"
        outside.write_text("keep", encoding="utf-8")
        state_path = self.runtime.runtime / "install_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["owned_runtime_files"] = ["../../outside.txt"]
        state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
        with self.assertRaises(ValidationError):
            plan_update(
                self.incoming_package("unsafe-state-incoming"),
                self.runtime,
                self.project,
            )
        self.assertTrue(outside.is_file())

    def test_update_rejects_unsafe_owned_skill_state(self) -> None:
        self.bootstrap()
        state_path = self.runtime.runtime / "install_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["owned_skills"] = ["../../outside"]
        state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "unsafe name"):
            plan_update(
                self.incoming_package("unsafe-skill-state-incoming"),
                self.runtime,
                self.project,
            )

    def test_legacy_entry_with_edits_requires_reviewed_local_instructions(self) -> None:
        self.bootstrap()
        installed_template_path = self.runtime.runtime / "templates" / "AGENTS.md"
        legacy_template = installed_template_path.read_text(encoding="utf-8")
        legacy_template = legacy_template.replace(
            "<!-- codex-workflow-managed-start -->\n", ""
        ).replace("<!-- codex-workflow-managed-end -->\n\n", "")
        legacy_template = legacy_template.replace(
            "\n<!-- codex-workflow-project-local-instructions-start -->\n"
            "<!-- codex-workflow-project-local-instructions-end -->\n",
            "\n",
        )
        installed_template_path.write_text(legacy_template, encoding="utf-8")
        self.project.active.write_text(
            legacy_template + "\nLocal legacy addition.\n", encoding="utf-8"
        )
        incoming = self.incoming_package("legacy-incoming")
        with self.assertRaises(ValidationError):
            plan_update(incoming, self.runtime, self.project)
        plan_update(
            incoming,
            self.runtime,
            self.project,
            legacy_local_instructions="Local legacy addition.",
        ).apply()
        self.assertEqual(
            extract(self.project.active.read_text(encoding="utf-8"), PROJECT_LOCAL),
            "Local legacy addition.",
        )

    def test_update_rejects_drift_in_workflow_managed_region(self) -> None:
        self.bootstrap()
        entry = self.project.active.read_text(encoding="utf-8")
        self.project.active.write_text(
            entry.replace("## Working State", "## Locally Changed Working State"),
            encoding="utf-8",
        )
        incoming = self.incoming_package("drift-incoming")
        with self.assertRaises(ValidationError):
            plan_update(incoming, self.runtime, self.project)

    def test_installed_launcher_delegates_to_incoming_update_runtime(self) -> None:
        self.bootstrap()
        incoming_root = self.root / "delegated-incoming" / "codex_workflow"
        shutil.copytree(
            PACKAGE,
            incoming_root,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        (incoming_root / "operate" / "VERSION").write_text(
            f"{NEXT_PACKAGE_VERSION}\n", encoding="utf-8"
        )
        user_agents = (incoming_root / "operate" / "user_AGENTS.md").read_text(encoding="utf-8")
        (incoming_root / "operate" / "user_AGENTS.md").write_text(
            user_agents.replace(
                f"codex-workflow-version: {PACKAGE_VERSION}",
                f"codex-workflow-version: {NEXT_PACKAGE_VERSION}",
            ),
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(self.runtime.runtime / "runtime" / "workflow.py"),
                "update",
                "--source",
                str(incoming_root),
                "--codex-home",
                str(self.codex_home),
                "--project",
                str(self.project_root),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["details"]["to_version"], NEXT_PACKAGE_VERSION)
        self.assertTrue(summary["applied"])

    def test_external_update_delegates_before_launcher_validation(self) -> None:
        self.bootstrap()
        incoming_root = self.root / "unvalidated-incoming" / "codex_workflow"
        shutil.copytree(
            PACKAGE,
            incoming_root,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        (incoming_root / "operate" / "VERSION").write_text(
            f"{NEXT_PACKAGE_VERSION}\n", encoding="utf-8"
        )

        argv = [
            str(PACKAGE / "runtime" / "workflow.py"),
            "update",
            "--source",
            str(incoming_root),
            "--codex-home",
            str(self.codex_home),
            "--project",
            str(self.project_root),
            "--json",
        ]
        with (
            mock.patch.object(
                workflow_cli.PackageLayout,
                "resolve",
                side_effect=AssertionError(
                    "external package was validated by launcher"
                ),
            ) as resolve,
            mock.patch.object(
                workflow_cli, "_delegate_update", return_value=0
            ) as delegate,
            mock.patch.object(sys, "argv", argv),
        ):
            self.assertEqual(workflow_cli.main(), 0)

        resolve.assert_not_called()
        delegate.assert_called_once()
        self.assertEqual(delegate.call_args.args[0], incoming_root.resolve())


class PersonalizationTests(unittest.TestCase):
    def test_only_customized_decisions_are_materialized(self) -> None:
        text = (PACKAGE / "resources" / "personalization.md").read_text(encoding="utf-8")
        self.assertEqual(materialize_personalization(text), "")
        customized = text.replace(
            "Status: default\nDecision: No additional frontend profile.",
            "Status: customized\nDecision: Use the frontend profile.",
        )
        self.assertEqual(materialize_personalization(customized), "Use the frontend profile.")


if __name__ == "__main__":
    unittest.main()
