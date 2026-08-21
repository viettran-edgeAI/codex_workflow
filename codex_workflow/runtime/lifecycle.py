"""Composition layer for user-level and project lifecycle plans."""

from __future__ import annotations

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
)
from .release import parse_semver
from .runtime_ops import (
    plan_installed_user_agents,
    plan_runtime_files,
    plan_runtime_remove,
)
from .transaction import Mutation


def plan_bootstrap(
    package: PackageLayout, runtime: RuntimePaths, project: ProjectPaths
) -> OperationPlan:
    mutations, owned_runtime = plan_runtime_files(package, runtime, False)
    project_plan = plan_project_install(package, project)
    mutations.extend(project_plan.mutations)
    state = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "version": package.version,
        "owned_runtime_files": sorted(owned_runtime),
        "owned_workers": sorted(package.worker_names),
        "auto_check_update": False,
    }
    mutations.append(json_mutation(runtime.runtime / USER_STATE, state))
    return OperationPlan(
        "bootstrap",
        deduplicate(mutations),
        project_plan.warnings,
        project_plan.agent_actions,
        {"version": package.version},
        cleanup_dirs=project_plan.cleanup_dirs,
    )


def plan_auto_check_update_setting(
    runtime: RuntimePaths, *, enabled: bool
) -> OperationPlan:
    state_path = runtime.runtime / USER_STATE
    if not state_path.is_file():
        raise ValidationError("workflow installation state is missing")
    state = read_json(state_path, default={})
    state["auto_check_update"] = enabled
    mutations = [json_mutation(state_path, state)]
    mutations.extend(plan_installed_user_agents(runtime, enabled=enabled))
    return OperationPlan(
        "set-auto-check-update",
        mutations,
        [],
        [],
        {"auto_check_update": enabled},
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
            ],
        },
        cleanup_dirs=runtime_dirs + project_dirs,
    )


def plan_update(
    incoming: PackageLayout,
    runtime: RuntimePaths,
    project: ProjectPaths,
    *,
    legacy_local_instructions: str | None = None,
) -> OperationPlan:
    installed = PackageLayout.resolve(runtime.runtime, allow_legacy=True)
    project_installed = _project_installed_package(installed, runtime, project)
    previous_state = read_json(runtime.runtime / USER_STATE, default={})
    auto_check_update = _auto_check_update(
        previous_state,
        legacy_config=runtime.runtime / "workflow_config.json",
    )
    backup_root = (
        runtime.runtime
        / ".backups"
        / f"{installed.version}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    )
    mutations: list[Mutation] = []
    append_backup_mutations(mutations, backup_root, runtime, project)
    runtime_mutations, owned_runtime = plan_runtime_files(
        incoming, runtime, auto_check_update
    )
    mutations.extend(runtime_mutations)
    project_mutations, warnings = plan_project_update(
        project_installed,
        incoming,
        project,
        legacy_local_instructions=legacy_local_instructions,
    )
    mutations.extend(project_mutations)
    incoming_targets = {
        mutation.path.resolve(strict=False) for mutation in runtime_mutations
    }
    for relative in read_string_list(previous_state, "owned_runtime_files"):
        obsolete = resolve_owned_runtime_path(runtime.runtime, relative)
        if obsolete not in incoming_targets and obsolete.exists():
            mutations.append(Mutation(obsolete, None))
    # The legacy configuration was workflow-owned, even for installations
    # whose older ownership manifest predates its entry.  Retire it after the
    # preference has been migrated so it cannot become a second source of
    # truth.
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
        "auto_check_update": auto_check_update,
    }
    mutations.append(json_mutation(runtime.runtime / USER_STATE, state))
    return OperationPlan(
        "update",
        deduplicate(mutations),
        warnings,
        [],
        {
            "from_version": installed.version,
            "to_version": incoming.version,
            "project_from_version": project_installed.version,
            "backup": str(backup_root),
        },
    )


def _auto_check_update(
    state: dict[str, object], *, legacy_config: Path | None = None
) -> bool:
    """Resolve the update-check preference across the state-file migration.

    Releases that predate the fixed-settings runtime stored this preference in
    ``workflow_config.json``.  A missing state field therefore means "read the
    legacy source", not "disable the preference".  Once the new state field is
    present it remains authoritative, including an explicit ``false`` value.
    """

    if "auto_check_update" in state:
        value = state["auto_check_update"]
    elif legacy_config is not None and legacy_config.is_file():
        legacy_state = read_json(legacy_config, default={})
        value = legacy_state.get("auto_check_update", False)
    else:
        value = False
    if not isinstance(value, bool):
        raise ValidationError("install state auto_check_update must be boolean")
    return value


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
