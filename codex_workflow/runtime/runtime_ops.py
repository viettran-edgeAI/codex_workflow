"""User-level runtime and fixed platform-setting operations."""

from __future__ import annotations

from pathlib import Path

from .platform_settings import (
    patch_codex_settings,
    remove_workflow_owned_settings,
)
from .errors import ValidationError
from .layout import USER_STATE, WORKER_MARKER, PackageLayout, RuntimePaths
from .markers import (
    AUTO_CHECK_UPDATE_PLACEHOLDER,
    USER_MANAGED,
    append_region,
    extract,
    remove_region,
    replace,
)
from .plan import read_json, read_string_list, text_mutation
from .transaction import Mutation


def plan_runtime_files(
    package: PackageLayout,
    runtime: RuntimePaths,
    auto_check_update: bool,
) -> tuple[list[Mutation], set[str]]:
    mutations: list[Mutation] = []
    owned: set[str] = set()
    excluded = {
        "AGENTS.md",
        "agents",
        "project_docs",
        "templates",
        ".source_backup",
        ".backups",
        USER_STATE,
    }
    for source in sorted(package.root.rglob("*")):
        relative = source.relative_to(package.root)
        if (
            relative.parts[0] in excluded
            or "__pycache__" in relative.parts
            or source.suffix == ".pyc"
            or not source.is_file()
        ):
            continue
        target = runtime.runtime / relative
        mutations.append(Mutation(target, source.read_bytes()))
        owned.add(relative.as_posix())
    template_targets = [(package.project_template, runtime.runtime / "templates" / "AGENTS.md")]
    template_targets.extend(
        (source, runtime.runtime / "templates" / "agents" / source.name)
        for source in sorted(package.agent_templates.glob("*.toml"))
    )
    template_targets.extend(
        (source, runtime.runtime / "templates" / "project_docs" / source.name)
        for source in package.project_docs.glob("*.md")
    )
    for source, target in template_targets:
        mutations.append(Mutation(target, source.read_bytes()))
        owned.add(target.relative_to(runtime.runtime).as_posix())
    mutations.extend(plan_user_agents(package, runtime, enabled=auto_check_update))
    mutations.extend(plan_platform_and_workers(runtime, package=package))
    backup = runtime.runtime / ".source_backup" / package.version
    for source in sorted(package.root.rglob("*")):
        if (
            source.is_file()
            and "__pycache__" not in source.parts
            and source.suffix != ".pyc"
            and ".source_backup" not in source.parts
            and ".backups" not in source.parts
        ):
            mutations.append(
                Mutation(backup / source.relative_to(package.root), source.read_bytes())
            )
    return mutations, owned


def _render_user_managed(source: str, instruction: str, *, enabled: bool) -> str:
    managed = extract(source, USER_MANAGED)
    if managed.count(AUTO_CHECK_UPDATE_PLACEHOLDER) != 1:
        raise ValidationError(
            "user_AGENTS.md auto-check placeholder is missing or duplicated"
        )
    before, after = managed.split(AUTO_CHECK_UPDATE_PLACEHOLDER)
    sections = [before.strip()]
    if enabled:
        sections.append(instruction.strip())
    sections.append(after.strip())
    return "\n\n".join(section for section in sections if section)


def _plan_user_agents_from_sources(
    source_path: Path,
    instruction_path: Path,
    runtime: RuntimePaths,
    *,
    enabled: bool,
) -> list[Mutation]:
    source = source_path.read_text(encoding="utf-8")
    instruction = instruction_path.read_text(encoding="utf-8")
    managed = _render_user_managed(source, instruction, enabled=enabled)
    if runtime.user_agents.is_file():
        current = runtime.user_agents.read_text(encoding="utf-8")
        if USER_MANAGED.start in current or USER_MANAGED.end in current:
            rendered = replace(current, USER_MANAGED, managed)
        else:
            rendered = append_region(current, USER_MANAGED, managed)
    else:
        rendered = append_region("", USER_MANAGED, managed)
    return [text_mutation(runtime.user_agents, rendered)]


def plan_user_agents(
    package: PackageLayout, runtime: RuntimePaths, *, enabled: bool
) -> list[Mutation]:
    return _plan_user_agents_from_sources(
        package.root / "user_AGENTS.md",
        package.root / "resources" / "auto_check_update.md",
        runtime,
        enabled=enabled,
    )


def plan_installed_user_agents(
    runtime: RuntimePaths, *, enabled: bool
) -> list[Mutation]:
    return _plan_user_agents_from_sources(
        runtime.runtime / "user_AGENTS.md",
        runtime.runtime / "resources" / "auto_check_update.md",
        runtime,
        enabled=enabled,
    )


def plan_platform_and_workers(
    runtime: RuntimePaths,
    *,
    package: PackageLayout | None = None,
) -> list[Mutation]:
    templates = package.agent_templates if package else runtime.runtime / "templates" / "agents"
    mutations: list[Mutation] = []
    current_state = read_json(runtime.runtime / USER_STATE, default={})
    previous_owned = set(read_string_list(current_state, "owned_workers"))
    workers = {
        path.stem for path in templates.glob("*.toml") if path.is_file()
    }
    for worker in sorted(workers):
        source = templates / f"{worker}.toml"
        mutations.append(
            text_mutation(
                runtime.agents / f"{worker}.toml",
                source.read_text(encoding="utf-8"),
            )
        )
    for worker in sorted(previous_owned - workers):
        target = runtime.agents / f"{worker}.toml"
        if target.exists():
            validate_worker_owner(target, worker)
            mutations.append(Mutation(target, None))
    config_text = (
        runtime.config_toml.read_text(encoding="utf-8")
        if runtime.config_toml.is_file()
        else ""
    )
    mutations.append(
        text_mutation(runtime.config_toml, patch_codex_settings(config_text))
    )
    return mutations


def validate_worker_owner(path: Path, worker: str) -> None:
    text = path.read_text(encoding="utf-8")
    match = WORKER_MARKER.search(text)
    if match is None or match.group(1) != worker:
        raise ValidationError(f"refusing to remove non-owned worker file: {path}")


def plan_runtime_remove(
    runtime: RuntimePaths,
) -> tuple[list[Mutation], list[Path], list[str]]:
    """Plan removal of workflow-owned user-level runtime files."""

    mutations: list[Mutation] = []
    cleanup_dirs: list[Path] = []
    warnings = [
        "unrelated content in the user AGENTS.md and config.toml will be preserved",
        "unrelated worker TOMLs will be preserved",
    ]

    if runtime.user_agents.is_symlink() or (
        runtime.user_agents.exists() and not runtime.user_agents.is_file()
    ):
        raise ValidationError(f"user AGENTS path is not a regular file: {runtime.user_agents}")
    if runtime.user_agents.is_file():
        current = runtime.user_agents.read_text(encoding="utf-8")
        if USER_MANAGED.start in current or USER_MANAGED.end in current:
            rendered = remove_region(current, USER_MANAGED)
            mutations.append(
                Mutation(
                    runtime.user_agents,
                    rendered.encode("utf-8") if rendered else None,
                )
            )

    if runtime.config_toml.is_symlink() or (
        runtime.config_toml.exists() and not runtime.config_toml.is_file()
    ):
        raise ValidationError(f"Codex config path is not a regular file: {runtime.config_toml}")
    if runtime.config_toml.is_file():
        current = runtime.config_toml.read_text(encoding="utf-8")
        rendered = remove_workflow_owned_settings(current)
        if rendered != current:
            mutations.append(
                Mutation(
                    runtime.config_toml,
                    rendered.encode("utf-8") if rendered else None,
                )
            )

    if runtime.agents.is_symlink() or (
        runtime.agents.exists() and not runtime.agents.is_dir()
    ):
        raise ValidationError(f"worker directory is not a directory: {runtime.agents}")
    if runtime.agents.is_dir():
        for target in sorted(runtime.agents.glob("*.toml")):
            if target.is_symlink() or not target.is_file():
                raise ValidationError(f"worker path is not a regular file: {target}")
            match = WORKER_MARKER.search(target.read_text(encoding="utf-8"))
            if match is None:
                continue
            if match.group(1) != target.stem:
                raise ValidationError(
                    f"worker ownership marker does not match file name: {target}"
                )
            mutations.append(Mutation(target, None))
        cleanup_dirs.append(runtime.agents)

    if runtime.runtime.is_symlink() or (
        runtime.runtime.exists() and not runtime.runtime.is_dir()
    ):
        raise ValidationError(f"workflow runtime path is not a directory: {runtime.runtime}")
    if runtime.runtime.is_dir():
        for path in sorted(runtime.runtime.rglob("*")):
            if path.is_symlink():
                raise ValidationError(f"refusing to remove symlink in workflow runtime: {path}")
            if path.is_dir():
                cleanup_dirs.append(path)
            elif path.is_file():
                mutations.append(Mutation(path, None))
            elif path.exists():
                raise ValidationError(f"workflow runtime contains a non-file entry: {path}")
        cleanup_dirs.append(runtime.runtime)
        warnings.append(
            f"all files under {runtime.runtime} (including source and update backups) will be permanently deleted"
        )

    return mutations, cleanup_dirs, warnings
