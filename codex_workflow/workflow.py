#!/usr/bin/env python3
"""Deterministic codex_workflow lifecycle CLI.

Lifecycle commands validate and apply their mutations directly. The destructive
``remove`` command is the exception: it plans first and applies only with its
hidden confirmation flag. The hidden ``--apply`` option remains accepted for
compatibility with older launchers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    raise SystemExit("codex_workflow requires Python 3.11 or newer")

from runtime.errors import WorkflowError
from runtime.layout import PROJECT_ID, USER_STATE
from runtime.lifecycle import (
    OperationPlan,
    PackageLayout,
    ProjectPaths,
    RuntimePaths,
    plan_bootstrap,
    plan_auto_check_update_setting,
    plan_enable,
    plan_personalize,
    plan_project_install,
    plan_remove,
    plan_update,
)
from runtime.release import (
    acquire,
    parse_semver,
    select_latest,
    select_releases,
    summarize_release_notes,
)


MIN_CODEX_VERSION = "0.147.0"
_CODEX_VERSION = re.compile(
    r"(?<![0-9A-Za-z])v?"
    r"((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?)"
)


def _default_codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def _add_common(parser: argparse.ArgumentParser, *, project: bool = True) -> None:
    parser.add_argument("--codex-home", type=Path, default=_default_codex_home())
    if project:
        parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--apply", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help="emit compact JSON")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    install = commands.add_parser("install")
    _add_common(install)
    # Retained for callers that have an extracted package available. This is
    # a read-only project-install source; install never bootstraps user files.
    install.add_argument("--package-root", type=Path, help=argparse.SUPPRESS)

    bootstrap = commands.add_parser("bootstrap", help=argparse.SUPPRESS)
    _add_common(bootstrap)
    bootstrap.add_argument(
        "--package-root", type=Path, default=Path(__file__).resolve().parent
    )

    update = commands.add_parser("update")
    _add_common(update)
    # Internal hand-off from an installed launcher; not a public prompt form.
    update.add_argument("--source", type=Path, help=argparse.SUPPRESS)
    update.add_argument("--allow-downgrade", action="store_true")
    update.add_argument(
        "--legacy-local-instructions",
        type=Path,
        help="reviewed local instructions extracted from a legacy merged entry point",
    )

    remove = commands.add_parser("remove")
    _add_common(remove)
    remove.add_argument("--confirm", action="store_true", help=argparse.SUPPRESS)

    auto_check = commands.add_parser("auto-check-update")
    _add_common(auto_check, project=False)

    check_update = commands.add_parser("check-update")
    _add_common(check_update, project=False)

    for name in (
        "enable-auto-check-update",
        "disable-auto-check-update",
        # Compatibility aliases retained from releases that called a
        # notification-only check an automatic update.
        "enable-auto-update",
        "disable-auto-update",
    ):
        command = commands.add_parser(name)
        _add_common(command, project=False)

    personalize = commands.add_parser("personalize")
    _add_common(personalize)
    personalize.add_argument("--resource", type=Path, required=True)

    for name in ("enable", "disable"):
        command = commands.add_parser(name)
        _add_common(command)

    validate = commands.add_parser("validate")
    _add_common(validate, project=False)
    validate.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parent)

    compatibility = commands.add_parser(
        "check-compatibility",
        help="verify that the installed Codex release supports this workflow",
    )
    _add_common(compatibility, project=False)
    return parser.parse_args()


def _paths(args: argparse.Namespace) -> tuple[RuntimePaths, ProjectPaths | None]:
    runtime = RuntimePaths(args.codex_home.expanduser().resolve())
    project = ProjectPaths(args.project.resolve()) if hasattr(args, "project") else None
    return runtime, project


def _emit(value: dict[str, object], *, compact: bool) -> None:
    if compact:
        print(json.dumps(value, separators=(",", ":"), sort_keys=True))
    else:
        print(json.dumps(value, indent=2, sort_keys=True))


def _require_compatible_codex() -> dict[str, object]:
    try:
        completed = subprocess.run(
            ["codex", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise WorkflowError(
            f"cannot determine the installed Codex version: {error}"
        ) from error
    output = "\n".join(
        value.strip() for value in (completed.stdout, completed.stderr) if value.strip()
    )
    if completed.returncode:
        raise WorkflowError(
            "cannot determine the installed Codex version"
            + (f": {output}" if output else "")
        )
    match = _CODEX_VERSION.search(output)
    if match is None:
        raise WorkflowError(f"cannot parse the installed Codex version from: {output!r}")
    detected_text = match.group(1)
    detected = parse_semver(detected_text)
    minimum = parse_semver(MIN_CODEX_VERSION)
    if detected < minimum:
        raise WorkflowError(
            f"Codex {detected_text} is incompatible; Codex {MIN_CODEX_VERSION} or "
            "newer is required for this workflow's tested subagent support"
        )
    return {
        "compatible": True,
        "codex_version": detected_text,
        "minimum_codex_version": MIN_CODEX_VERSION,
    }


def _finish(plan: OperationPlan, args: argparse.Namespace) -> int:
    summary = plan.summary()
    summary["applied"] = True
    plan.apply()
    _emit(summary, compact=args.json)
    return 0


def _project_workflow_entry(project: ProjectPaths) -> Path | None:
    """Return an existing recognized active or disabled project entry point."""

    for path in (project.active, project.disabled):
        if path.is_file() and PROJECT_ID in path.read_text(encoding="utf-8"):
            return path
    return None


def _package_root(path: Path) -> Path:
    """Resolve a package path without applying a version-specific schema."""

    root = path.expanduser().resolve()
    if not (root / "VERSION").is_file():
        nested = root / "codex_workflow"
        if (nested / "VERSION").is_file():
            root = nested
    return root


def _package_version(root: Path) -> object:
    """Read the minimal update-ordering metadata without applying a package schema."""

    version_path = root / "VERSION"
    try:
        lines = version_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise WorkflowError(f"cannot read incoming package VERSION: {error}") from error
    if len(lines) != 1 or not lines[0]:
        raise WorkflowError("incoming package VERSION must contain exactly one non-empty line")
    try:
        return parse_semver(lines[0])
    except Exception as error:
        raise WorkflowError(f"incoming package VERSION is invalid: {lines[0]!r}") from error


def _require_newer_update(
    incoming_root: Path, runtime: RuntimePaths, *, allow_downgrade: bool
) -> None:
    """Reject equal or unintended downgrade packages before handing them off."""

    incoming = _package_version(incoming_root)
    try:
        installed_text = (runtime.runtime / "VERSION").read_text(encoding="utf-8").strip()
        installed = parse_semver(installed_text)
    except OSError as error:
        raise WorkflowError(f"cannot read installed workflow VERSION: {error}") from error
    except Exception as error:
        raise WorkflowError("installed workflow VERSION is invalid") from error
    if incoming == installed:
        raise WorkflowError("incoming version matches the installed version; select a newer release")
    if incoming < installed and not allow_downgrade:
        raise WorkflowError("incoming version is older; pass --allow-downgrade after approval")


def _delegate_update(incoming_root: Path, args: argparse.Namespace) -> int:
    workflow = incoming_root / "workflow.py"
    if not workflow.is_file():
        raise WorkflowError(f"incoming package workflow.py is missing: {workflow}")
    command = [
        sys.executable,
        "-B",
        str(workflow),
        "update",
        "--source",
        str(incoming_root),
        "--codex-home",
        str(args.codex_home),
        "--project",
        str(args.project),
    ]
    if args.allow_downgrade:
        command.append("--allow-downgrade")
    if args.legacy_local_instructions:
        command.extend(
            ["--legacy-local-instructions", str(args.legacy_local_instructions)]
        )
    if args.apply:
        command.append("--apply")
    if args.json:
        command.append("--json")
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main() -> int:
    args = parse_args()
    temporary = None
    try:
        runtime, project = _paths(args)
        if args.command == "check-compatibility":
            _emit(_require_compatible_codex(), compact=args.json)
            return 0
        if args.command == "validate":
            package = PackageLayout.resolve(args.package_root)
            _emit(
                {
                    "valid": True,
                    "version": package.version,
                    "workers": sorted(package.worker_names),
                },
                compact=args.json,
            )
            return 0
        if args.command == "auto-check-update":
            state_path = runtime.runtime / USER_STATE
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise WorkflowError(f"cannot read workflow installation state: {error}") from error
            if not isinstance(state, dict):
                raise WorkflowError("workflow installation state must be a JSON object")
            auto_check_update = state.get("auto_check_update", False)
            if not isinstance(auto_check_update, bool):
                raise WorkflowError("install state auto_check_update must be boolean")
            if not auto_check_update:
                _emit(
                    {"status": "disabled", "installed": None, "available": None},
                    compact=args.json,
                )
                return 0
            installed_text = (runtime.runtime / "VERSION").read_text(encoding="utf-8").strip()
            installed = parse_semver(installed_text)
            selected = select_latest()
            status = "current" if selected.version == installed else (
                "update available" if selected.version > installed else "installed newer"
            )
            _emit(
                {
                    "status": status,
                    "installed": installed_text,
                    "available": selected.version_text,
                    "asset": selected.zip_name,
                },
                compact=args.json,
            )
            return 0
        if args.command == "check-update":
            installed_text = (runtime.runtime / "VERSION").read_text(encoding="utf-8").strip()
            installed = parse_semver(installed_text)
            releases = select_releases()
            newer = [release for release in releases if release.version > installed]
            latest = releases[0]
            updates = [
                {
                    "version": release.version_text,
                    "asset": release.zip_name,
                    "release_url": release.release_url,
                    "release_notes": release.release_notes,
                    "summary": summarize_release_notes(release.release_notes),
                }
                for release in newer
            ]
            if newer:
                status = "update available"
                summary = "\n".join(
                    f"{item['version']}: {item['summary']}" for item in updates
                )
            elif latest.version == installed:
                status = "current"
                summary = "The installed workflow is current."
            else:
                status = "installed newer"
                summary = "The installed workflow is newer than the latest release."
            _emit(
                {
                    "status": status,
                    "installed": installed_text,
                    "available": latest.version_text,
                    "asset": latest.zip_name,
                    "summary": summary,
                    "updates": updates,
                },
                compact=args.json,
            )
            return 0
        if args.command == "remove":
            assert project is not None
            plan = plan_remove(runtime, project)
            if not args.confirm:
                summary = plan.summary()
                summary["applied"] = False
                summary["confirmation_required"] = True
                _emit(summary, compact=args.json)
                return 0
            return _finish(plan, args)
        if args.command in {
            "enable-auto-check-update",
            "disable-auto-check-update",
            "enable-auto-update",
            "disable-auto-update",
        }:
            return _finish(
                plan_auto_check_update_setting(
                    runtime,
                    enabled=args.command in {
                        "enable-auto-check-update",
                        "enable-auto-update",
                    },
                ),
                args,
            )
        if args.command == "bootstrap":
            assert project is not None
            package = PackageLayout.resolve(args.package_root)
            return _finish(plan_bootstrap(package, runtime, project), args)
        if args.command == "install":
            assert project is not None
            if project.active.exists() and project.disabled.exists():
                raise WorkflowError("both active and disabled project entry points exist")
            if (runtime.runtime / "VERSION").is_file():
                package = PackageLayout.resolve(runtime.runtime)
            elif args.package_root is not None:
                package = PackageLayout.resolve(args.package_root)
            else:
                raise WorkflowError(
                    "the user-level workflow bootstrap is not installed; "
                    "complete the initial bootstrap before installing a project"
                )
            existing = _project_workflow_entry(project)
            if existing is not None:
                # Validate the recognized entry before reporting a no-op. This
                # turns stale, malformed, or personalization-drifted installs
                # into actionable errors instead of misreporting them as merely
                # disabled.
                existing_plan = plan_project_install(package, project)
                if existing_plan.agent_actions[0]["files"]:
                    return _finish(existing_plan, args)
                enabled = existing == project.active
                _emit(
                    {
                        "applied": False,
                        "status": "already enabled" if enabled else "already disabled",
                        "instruction": (
                            "No action is required."
                            if enabled
                            else "Run `codex_workflow --enable` to reactivate it."
                        ),
                    },
                    compact=args.json,
                )
                return 0
            return _finish(plan_project_install(package, project), args)
        if args.command == "update":
            assert project is not None
            if args.source:
                incoming_root = _package_root(args.source)
            else:
                selected = select_latest()
                temporary, package_path = acquire(selected)
                incoming_root = _package_root(package_path)
            _require_newer_update(
                incoming_root, runtime, allow_downgrade=args.allow_downgrade
            )
            if incoming_root != Path(__file__).resolve().parent:
                # The incoming runtime owns package validation. An installed
                # launcher may be older than the package it is updating to and
                # must not reject files removed by that newer package.
                return _delegate_update(incoming_root, args)
            incoming = PackageLayout.resolve(incoming_root)
            legacy_local = (
                args.legacy_local_instructions.read_text(encoding="utf-8")
                if args.legacy_local_instructions
                else None
            )
            return _finish(
                plan_update(
                    incoming,
                    runtime,
                    project,
                    legacy_local_instructions=legacy_local,
                ),
                args,
            )
        if args.command == "personalize":
            assert project is not None
            resource = args.resource.read_text(encoding="utf-8")
            return _finish(plan_personalize(project, resource), args)
        if args.command in {"enable", "disable"}:
            assert project is not None
            return _finish(plan_enable(project, enable=args.command == "enable"), args)
        raise WorkflowError(f"unsupported command: {args.command}")
    except (OSError, WorkflowError) as error:
        _emit({"error": str(error), "applied": False}, compact=getattr(args, "json", False))
        return 1
    finally:
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
