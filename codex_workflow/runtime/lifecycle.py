"""Composition layer for user-level and project lifecycle plans."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from . import RUNTIME_SCHEMA_VERSION
from .backup import append_backup_mutations
from .errors import ValidationError
from .layout import USER_STATE, PackageLayout, ProjectPaths, RuntimePaths
from .personalization import materialize_personalization
from .plan import (
    OperationPlan,
    deduplicate,
    json_mutation,
    read_json,
    read_string_list,
    resolve_owned_runtime_path,
)
from .project_ops import (
    plan_enable,
    plan_personalize,
    plan_project_install,
    plan_project_remove,
    plan_project_update,
    recognized_entry,
)
from .registry import render_registered_projects
from .release import parse_semver
from .runtime_ops import (
    plan_runtime_files,
    plan_runtime_remove,
)
from .transaction import Mutation


def plan_bootstrap(
    package: PackageLayout, runtime: RuntimePaths, project: ProjectPaths
) -> OperationPlan:
    mutations, owned_runtime, skill_cleanup = plan_runtime_files(package, runtime)
    project_plan = plan_project_install(package, project)
    mutations.extend(project_plan.mutations)
    state = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "version": package.version,
        "owned_runtime_files": sorted(owned_runtime),
        "owned_workers": sorted(package.worker_names),
        "owned_skills": sorted(package.skill_names),
        "projects": render_registered_projects([project]),
    }
    mutations.append(json_mutation(runtime.runtime / USER_STATE, state))
    return OperationPlan(
        "bootstrap",
        deduplicate(mutations),
        project_plan.warnings,
        project_plan.agent_actions,
        {"version": package.version},
        cleanup_dirs=project_plan.cleanup_dirs + skill_cleanup,
    )


def plan_install(
    package: PackageLayout,
    runtime: RuntimePaths,
    project: ProjectPaths,
    *,
    register: bool = True,
) -> OperationPlan:
    """Install or repair one project and register it for user-level updates."""

    project_plan = plan_project_install(package, project)
    if not register:
        return project_plan
    state_path = runtime.runtime / USER_STATE
    state = read_json(state_path, default={})
    if not state_path.is_file():
        raise ValidationError("user-level workflow installation state is missing")
    registered = read_string_list(state, "projects") if "projects" in state else []
    projects = render_registered_projects(
        [ProjectPaths(Path(root)) for root in registered] + [project]
    )
    if state.get("projects") != projects:
        state["schema_version"] = RUNTIME_SCHEMA_VERSION
        state["projects"] = projects
        project_plan.mutations.append(json_mutation(state_path, state))
    project_plan.details["registered_project"] = str(project.root.resolve())
    return OperationPlan(
        project_plan.operation,
        deduplicate(project_plan.mutations),
        project_plan.warnings,
        project_plan.agent_actions,
        project_plan.details,
        project_plan.cleanup_dirs,
    )


def plan_remove(
    runtime: RuntimePaths,
    project: ProjectPaths,
) -> OperationPlan:
    runtime_mutations, runtime_dirs, runtime_warnings = plan_runtime_remove(runtime)
    project_mutations, project_dirs, project_warnings = plan_project_remove(project)
    return OperationPlan(
        "remove",
        deduplicate(runtime_mutations + project_mutations),
        runtime_warnings + project_warnings,
        [],
        {
            "confirmation_required": True,
            "preserves": [
                "project agent_docs/ files",
                "unrelated user AGENTS.md content",
                "unrelated Codex config.toml keys",
                "unrelated worker TOMLs",
                "unrelated skills",
            ],
        },
        cleanup_dirs=runtime_dirs + project_dirs,
    )


def plan_update(
    incoming: PackageLayout,
    runtime: RuntimePaths,
    projects: ProjectPaths | Iterable[ProjectPaths],
    *,
    legacy_local_instructions: str | None = None,
    legacy_project: ProjectPaths | None = None,
    project_list_cleanup: Path | None = None,
) -> OperationPlan:
    project_list = [projects] if isinstance(projects, ProjectPaths) else list(projects)
    project_list = [
        ProjectPaths(root)
        for root in {
            project.root.resolve(): None for project in project_list
        }
    ]
    if legacy_local_instructions is not None and legacy_project is None:
        if len(project_list) != 1:
            raise ValidationError(
                "legacy local instructions require one explicit legacy project"
            )
        legacy_project = project_list[0]
    installed = PackageLayout.resolve(runtime.runtime, allow_legacy=True)
    previous_state = read_json(runtime.runtime / USER_STATE, default={})
    backup_root = (
        runtime.runtime
        / ".backups"
        / f"{installed.version}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    )
    mutations: list[Mutation] = []
    runtime_mutations, owned_runtime, skill_cleanup = plan_runtime_files(
        incoming, runtime
    )
    project_versions: dict[str, str] = {}
    installed_projects: list[tuple[ProjectPaths, PackageLayout]] = []
    for project in project_list:
        try:
            recognized_entry(project)
        except ValidationError as error:
            raise ValidationError(
                f"registered project {project.root}: {error}"
            ) from error
        project_installed = _project_installed_package(installed, runtime, project)
        project_versions[str(project.root.resolve())] = project_installed.version
        installed_projects.append((project, project_installed))

    append_backup_mutations(mutations, backup_root, runtime, project_list)
    mutations.extend(runtime_mutations)
    warnings: list[str] = []
    for project, project_installed in installed_projects:
        project_mutations, project_warnings = plan_project_update(
            project_installed,
            incoming,
            project,
            legacy_local_instructions=(
                legacy_local_instructions
                if legacy_project is None
                or project.root.resolve() == legacy_project.root.resolve()
                else None
            ),
        )
        mutations.extend(project_mutations)
        warnings.extend(
            f"{project.root}: {warning}" for warning in project_warnings
        )
    incoming_targets = {
        mutation.path.resolve(strict=False) for mutation in runtime_mutations
    }
    for relative in read_string_list(previous_state, "owned_runtime_files"):
        obsolete = resolve_owned_runtime_path(runtime.runtime, relative)
        if obsolete not in incoming_targets and obsolete.exists():
            mutations.append(Mutation(obsolete, None))
    # The retired legacy configuration was workflow-owned even when an older
    # ownership manifest predates its entry, so updates still remove it.
    legacy_config = runtime.runtime / "workflow_config.json"
    if (
        legacy_config.is_file()
        and legacy_config.resolve(strict=False) not in incoming_targets
    ):
        mutations.append(Mutation(legacy_config, None))
    state = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "version": incoming.version,
        "owned_runtime_files": sorted(owned_runtime),
        "owned_workers": sorted(incoming.worker_names),
        "owned_skills": sorted(incoming.skill_names),
        "projects": render_registered_projects(project_list),
    }
    mutations.append(json_mutation(runtime.runtime / USER_STATE, state))
    if project_list_cleanup is not None and project_list_cleanup.is_file():
        mutations.append(Mutation(project_list_cleanup, None))
    details: dict[str, object] = {
        "from_version": installed.version,
        "to_version": incoming.version,
        "projects": render_registered_projects(project_list),
        "project_from_versions": project_versions,
        "backup": str(backup_root),
    }
    if len(project_versions) == 1:
        details["project_from_version"] = next(iter(project_versions.values()))
    return OperationPlan(
        "update",
        deduplicate(mutations),
        warnings,
        [],
        details,
        cleanup_dirs=skill_cleanup,
    )


def _project_installed_package(
    installed: PackageLayout,
    runtime: RuntimePaths,
    project: ProjectPaths,
) -> PackageLayout:
    """Resolve the package version that produced this project's entry point."""

    if not project.active.exists() and not project.disabled.exists():
        return installed
    state = read_json(project.state, default={})
    version = state.get("workflow_version")
    if version is None:
        # Pre-state installations can only be compared with the currently
        # installed source, retaining the legacy migration behavior.
        return installed
    if not isinstance(version, str) or not version:
        raise ValidationError("project workflow_version state must be a non-empty string")
    parse_semver(version)
    if version == installed.version:
        return installed
    source_backups = (runtime.runtime / ".source_backup").resolve()
    historical_root = (source_backups / version).resolve()
    try:
        historical_root.relative_to(source_backups)
    except ValueError as error:
        raise ValidationError("project workflow_version resolves outside source backups") from error
    if not historical_root.is_dir():
        raise ValidationError(
            "the historical workflow source for this project is missing: "
            f"{historical_root}; restore it from backup before updating the project"
        )
    historical = PackageLayout.resolve(historical_root, allow_legacy=True)
    if historical.version != version:
        raise ValidationError(
            "project workflow state and historical source backup versions disagree"
        )
    return historical
