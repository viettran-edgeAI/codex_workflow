"""User-level registry for projects that have installed codex_workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .errors import ValidationError
from .layout import USER_STATE, ProjectPaths, RuntimePaths
from .plan import read_json


PROJECTS_KEY = "projects"
MIGRATION_FILE = "project_registry_migration.txt"


def normalize_project_roots(values: Iterable[str | Path]) -> list[Path]:
    """Return unique canonical absolute project roots in stable order."""

    roots: list[Path] = []
    seen: set[Path] = set()
    for value in values:
        raw = Path(value).expanduser()
        if not raw.is_absolute():
            raise ValidationError(f"project registry path must be absolute: {value}")
        root = raw.resolve(strict=False)
        if root in seen:
            continue
        seen.add(root)
        roots.append(root)
    return roots


def read_registered_projects(runtime: RuntimePaths) -> list[ProjectPaths] | None:
    """Read the registry, returning ``None`` for installations that predate it."""

    state = read_json(runtime.runtime / USER_STATE, default={})
    if PROJECTS_KEY not in state:
        return None
    value = state[PROJECTS_KEY]
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValidationError(
            f"state field {PROJECTS_KEY!r} must be a list of non-empty absolute paths"
        )
    if not value:
        raise ValidationError("project registry must contain at least one project")
    return [ProjectPaths(root) for root in normalize_project_roots(value)]


def render_registered_projects(projects: Iterable[ProjectPaths]) -> list[str]:
    return [
        str(root)
        for root in normalize_project_roots(project.root for project in projects)
    ]


def read_project_list(path: Path) -> list[ProjectPaths]:
    """Read a complete user-provided legacy project list, one path per line."""

    if path.is_symlink() or not path.is_file():
        raise ValidationError(f"project list is not a regular file: {path}")
    values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    values = [value for value in values if value]
    if not values:
        raise ValidationError("project list must contain at least one absolute path")
    return [ProjectPaths(root) for root in normalize_project_roots(values)]


def migration_file(runtime: RuntimePaths) -> Path:
    return runtime.runtime / MIGRATION_FILE
