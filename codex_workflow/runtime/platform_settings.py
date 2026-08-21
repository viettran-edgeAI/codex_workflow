"""Fixed Codex platform settings owned by the workflow."""

from __future__ import annotations

import re

from ._toml import tomllib
from .errors import ValidationError


MAX_CONCURRENT_WORKERS = 20


def patch_codex_settings(text: str) -> str:
    """Apply the workflow's fixed platform settings without replacing user settings."""

    if text.strip():
        try:
            tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise ValidationError(f"existing Codex config is invalid TOML: {error}") from error
    sections: dict[str, dict[str, str]] = {
        "agents": {
            "enabled": "true",
            "max_concurrent_threads_per_session": str(MAX_CONCURRENT_WORKERS),
        },
        "features": {"multi_agent": "true"},
    }
    lines = _remove_owned_keys(text.splitlines(), _LEGACY_OWNED_KEYS)
    for section, values in sections.items():
        lines = _patch_section(lines, section, values)
    rendered = "\n".join(lines).rstrip() + "\n"
    try:
        tomllib.loads(rendered)
    except tomllib.TOMLDecodeError as error:
        raise ValidationError(f"generated Codex config is invalid TOML: {error}") from error
    return rendered


_SECTION = re.compile(r"^\s*\[([^]]+)]\s*(?:#.*)?$")
_KEY = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*=")


def _patch_section(lines: list[str], section: str, values: dict[str, str]) -> list[str]:
    headers = [
        index
        for index, line in enumerate(lines)
        if (_SECTION.match(line) and _SECTION.match(line).group(1) == section)
    ]
    if len(headers) > 1:
        raise ValidationError(f"duplicate TOML section [{section}]")
    if not headers:
        result = list(lines)
        if result and result[-1].strip():
            result.append("")
        result.append(f"[{section}]")
        result.extend(f"{key} = {value}" for key, value in values.items())
        return result
    start = headers[0]
    end = next(
        (index for index in range(start + 1, len(lines)) if _SECTION.match(lines[index])),
        len(lines),
    )
    found: dict[str, int] = {}
    result = list(lines)
    for index in range(start + 1, end):
        match = _KEY.match(result[index])
        if match and match.group(1) in values:
            key = match.group(1)
            if key in found:
                raise ValidationError(f"duplicate workflow-owned TOML key [{section}].{key}")
            found[key] = index
            result[index] = f"{key} = {values[key]}"
    missing = [key for key in values if key not in found]
    result[end:end] = [f"{key} = {values[key]}" for key in missing]
    return result


_LEGACY_OWNED_KEYS: dict[str, set[str]] = {
    "features.multi_agent_v2": {
        "enabled",
        "max_concurrent_threads_per_session",
        "hide_spawn_agent_metadata",
        "tool_namespace",
        "min_wait_timeout_ms",
        "default_wait_timeout_ms",
        "max_wait_timeout_ms",
    },
}


_OWNED_KEYS: dict[str, set[str]] = {
    "agents": {"enabled", "max_concurrent_threads_per_session"},
    "features": {"multi_agent"},
    **_LEGACY_OWNED_KEYS,
}


def _remove_owned_keys(
    lines: list[str], owned_keys: dict[str, set[str]]
) -> list[str]:
    """Remove selected keys while retaining unrelated keys in the same tables."""

    result: list[str] = []
    index = 0
    while index < len(lines):
        header = _SECTION.match(lines[index])
        if header is None or header.group(1) not in owned_keys:
            result.append(lines[index])
            index += 1
            continue

        section = header.group(1)
        end = next(
            (
                position
                for position in range(index + 1, len(lines))
                if _SECTION.match(lines[position])
            ),
            len(lines),
        )
        owned = owned_keys[section]
        retained = [
            line
            for line in lines[index + 1 : end]
            if (match := _KEY.match(line)) is None or match.group(1) not in owned
        ]
        if any(line.strip() for line in retained):
            result.append(lines[index])
            result.extend(retained)
        index = end
    return result


def remove_workflow_owned_settings(text: str) -> str:
    """Remove only the Codex platform settings owned by this workflow."""

    if not text.strip():
        return ""
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ValidationError(f"existing Codex config is invalid TOML: {error}") from error

    result = _remove_owned_keys(text.splitlines(), _OWNED_KEYS)
    rendered = "\n".join(result).rstrip()
    if rendered:
        rendered += "\n"
    try:
        tomllib.loads(rendered)
    except tomllib.TOMLDecodeError as error:
        raise ValidationError(f"generated Codex config is invalid TOML: {error}") from error
    return rendered
