"""Strict marker parsing and rendering."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ValidationError


@dataclass(frozen=True)
class Marker:
    start: str
    end: str


USER_MANAGED = Marker(
    "<!-- codex-workflow-user-managed-start -->",
    "<!-- codex-workflow-user-managed-end -->",
)
AUTO_CHECK_UPDATE_PLACEHOLDER = (
    "<!-- codex-workflow-auto-check-update-instruction -->"
)
WORKFLOW_MANAGED = Marker(
    "<!-- codex-workflow-managed-start -->",
    "<!-- codex-workflow-managed-end -->",
)
PROJECT_PERSONALIZATION = Marker(
    "<!-- codex-workflow-project-personalization-start -->",
    "<!-- codex-workflow-project-personalization-end -->",
)
PROJECT_LOCAL = Marker(
    "<!-- codex-workflow-project-local-instructions-start -->",
    "<!-- codex-workflow-project-local-instructions-end -->",
)
def _bounds(text: str, marker: Marker) -> tuple[int, int]:
    if text.count(marker.start) != 1 or text.count(marker.end) != 1:
        raise ValidationError(
            f"expected exactly one marker pair: {marker.start} / {marker.end}"
        )
    start = text.index(marker.start) + len(marker.start)
    end = text.index(marker.end)
    if start > end:
        raise ValidationError(f"marker end precedes start: {marker.start}")
    return start, end


def extract(text: str, marker: Marker) -> str:
    start, end = _bounds(text, marker)
    body = text[start:end]
    if body.startswith("\n"):
        body = body[1:]
    if body.endswith("\n"):
        body = body[:-1]
    return body


def replace(text: str, marker: Marker, body: str) -> str:
    start, end = _bounds(text, marker)
    normalized = body.strip("\n")
    replacement = "\n" + normalized + "\n" if normalized else "\n"
    return text[:start] + replacement + text[end:]


def remove_region(text: str, marker: Marker) -> str:
    start, end = _bounds(text, marker)
    start -= len(marker.start)
    end += len(marker.end)
    remaining = text[:start] + text[end:]
    if not remaining.strip():
        return ""
    return remaining.rstrip("\n") + "\n"


def append_region(text: str, marker: Marker, body: str) -> str:
    if marker.start in text or marker.end in text:
        raise ValidationError(f"partial or unexpected marker already present: {marker.start}")
    prefix = text.rstrip() + "\n\n" if text.strip() else ""
    normalized = body.strip("\n")
    middle = f"\n{normalized}\n" if normalized else "\n"
    return prefix + marker.start + middle + marker.end + "\n"


def validate_project_template(text: str) -> None:
    for marker in (WORKFLOW_MANAGED, PROJECT_PERSONALIZATION, PROJECT_LOCAL):
        _bounds(text, marker)
    if extract(text, PROJECT_PERSONALIZATION) or extract(text, PROJECT_LOCAL):
        raise ValidationError("default project template protected regions must be empty")
    order = [
        text.index(WORKFLOW_MANAGED.start),
        text.index(WORKFLOW_MANAGED.end),
        text.index(PROJECT_PERSONALIZATION.start),
        text.index(PROJECT_PERSONALIZATION.end),
        text.index(PROJECT_LOCAL.start),
        text.index(PROJECT_LOCAL.end),
    ]
    if order != sorted(order):
        raise ValidationError("project template marker regions overlap or are out of order")


def render_project_entry(
    template: str, *, personalization: str = "", local_instructions: str = ""
) -> str:
    validate_project_template(template)
    rendered = replace(template, PROJECT_PERSONALIZATION, personalization)
    rendered = replace(rendered, PROJECT_LOCAL, local_instructions)
    return rendered
