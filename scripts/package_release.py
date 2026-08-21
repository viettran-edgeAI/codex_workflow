#!/usr/bin/env python3
"""Build and validate the codex_workflow GitHub Release assets.

The release payload is deliberately sourced from one directory only:
``codex_workflow/``.  The script uses only Python's standard library so it can
run on Linux, macOS, and Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator


PACKAGE_DIR_NAME = "codex_workflow"
VERSION_FILE = "VERSION"
USER_AGENTS_FILE = "user_AGENTS.md"
VERSION_MARKER = re.compile(r"codex-workflow-version:\s*([^\s<]+)")
IDENTIFIER = re.compile(r"^[0-9A-Za-z-]+$")
USER_ID_MARKER = "<!-- codex-workflow-user-id: viettran-edgeAI/codex_workflow -->"
USER_MANAGED_START = "<!-- codex-workflow-user-managed-start -->"
USER_MANAGED_END = "<!-- codex-workflow-user-managed-end -->"
BUILTIN_WORKERS = frozenset(
    {
        "default_executor",
        "senior_executor",
        "tester",
        "doc-writer",
        "companion",
        "investigator",
        "closure_steward",
    }
)


class ReleaseError(ValueError):
    """Raised when the source tree or an archive is not release-safe."""


@total_ordering
@dataclass(frozen=True, eq=False)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: str | None = None

    def _compare(self, other: object) -> int:
        if not isinstance(other, SemVer):
            return NotImplemented
        left_core = (self.major, self.minor, self.patch)
        right_core = (other.major, other.minor, other.patch)
        if left_core != right_core:
            return (left_core > right_core) - (left_core < right_core)
        if not self.prerelease and not other.prerelease:
            return 0
        if not self.prerelease:
            return 1
        if not other.prerelease:
            return -1
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            left_numeric = left.isdigit()
            right_numeric = right.isdigit()
            if left_numeric and right_numeric:
                return (int(left) > int(right)) - (int(left) < int(right))
            if left_numeric != right_numeric:
                return -1 if left_numeric else 1
            return (left > right) - (left < right)
        return (len(self.prerelease) > len(other.prerelease)) - (
            len(self.prerelease) < len(other.prerelease)
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SemVer) and self._compare(other) == 0

    def __lt__(self, other: object) -> bool:
        comparison = self._compare(other)
        if comparison is NotImplemented:
            return NotImplemented
        return comparison < 0

    def __str__(self) -> str:
        value = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            value += "-" + ".".join(self.prerelease)
        if self.build:
            value += "+" + self.build
        return value


def parse_semver(raw: str, *, allow_v: bool = False) -> SemVer:
    """Parse a SemVer 2.0.0 value, optionally accepting a leading ``v``."""

    value = raw.strip()
    if not value or value != raw:
        raise ReleaseError(f"invalid semantic version: {raw!r}")
    if allow_v and value[:1].lower() == "v":
        value = value[1:]
    if not value:
        raise ReleaseError(f"invalid semantic version: {raw!r}")

    build: str | None = None
    if "+" in value:
        value, build = value.split("+", 1)
        if not build:
            raise ReleaseError(f"invalid semantic version: {raw!r}")
        _validate_identifiers(build, raw, allow_leading_zero=True)

    prerelease: tuple[str, ...] = ()
    if "-" in value:
        value, prerelease_text = value.split("-", 1)
        if not prerelease_text:
            raise ReleaseError(f"invalid semantic version: {raw!r}")
        prerelease = tuple(prerelease_text.split("."))
        _validate_identifiers(prerelease_text, raw, allow_leading_zero=False)

    core = value.split(".")
    if len(core) != 3 or any(not part.isdigit() for part in core):
        raise ReleaseError(f"invalid semantic version: {raw!r}")
    if any(len(part) > 1 and part.startswith("0") for part in core):
        raise ReleaseError(f"invalid semantic version: {raw!r}")

    return SemVer(*(int(part) for part in core), prerelease, build)


def _validate_identifiers(
    value: str, raw: str, *, allow_leading_zero: bool
) -> None:
    for identifier in value.split("."):
        if not IDENTIFIER.fullmatch(identifier):
            raise ReleaseError(f"invalid semantic version: {raw!r}")
        if (
            not allow_leading_zero
            and identifier.isdigit()
            and len(identifier) > 1
            and identifier.startswith("0")
        ):
            raise ReleaseError(f"invalid semantic version: {raw!r}")


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_source_version(package_root: Path) -> tuple[str, SemVer]:
    version_path = package_root / VERSION_FILE
    if not version_path.is_file():
        raise ReleaseError(f"missing {version_path}")
    lines = version_path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 1 or not lines[0]:
        raise ReleaseError(f"{version_path} must contain exactly one version line")
    raw = lines[0]
    version = parse_semver(raw)
    return str(version), version


def validate_source(package_root: Path) -> tuple[str, SemVer]:
    if not package_root.is_dir():
        raise ReleaseError(f"missing package directory: {package_root}")

    version_text, version = read_source_version(package_root)
    user_agents = package_root / USER_AGENTS_FILE
    if not user_agents.is_file():
        raise ReleaseError(f"missing {user_agents}")
    marker = VERSION_MARKER.search(user_agents.read_text(encoding="utf-8"))
    if marker is None:
        raise ReleaseError(f"missing {VERSION_MARKER.pattern} in {user_agents}")
    marker_text = marker.group(1)
    marker_version = parse_semver(marker_text, allow_v=True)
    if marker_text.removeprefix("v") != version_text or marker_version != version:
        raise ReleaseError(
            f"VERSION ({version_text}) does not match the user marker ({marker_text})"
        )
    _validate_user_agents_text(user_agents.read_text(encoding="utf-8"), version_text)

    entries = list(_source_entries(package_root))
    if not entries:
        raise ReleaseError(f"package directory is empty: {package_root}")
    _validate_runtime(package_root)
    return version_text, version


def _validate_user_agents_text(text: str, version_text: str) -> None:
    if USER_ID_MARKER not in text:
        raise ReleaseError("user_AGENTS.md is missing its workflow identity marker")
    if f"<!-- codex-workflow-version: {version_text} -->" not in text:
        raise ReleaseError("user_AGENTS.md version marker does not match VERSION")
    if text.count(USER_MANAGED_START) != 1 or text.count(USER_MANAGED_END) != 1:
        raise ReleaseError("user_AGENTS.md must contain exactly one managed marker pair")


def _validate_runtime(package_root: Path) -> None:
    command = [
        sys.executable,
        "-B",
        str(package_root / "workflow.py"),
        "validate",
        "--package-root",
        str(package_root),
        "--json",
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise ReleaseError(f"could not run workflow package validation: {error}") from error
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise ReleaseError(f"workflow package validation failed: {detail}")


def _source_entries(package_root: Path) -> Iterator[tuple[Path, str, bool]]:
    """Yield source paths and archive names in deterministic order."""

    paths = [package_root, *package_root.rglob("*")]
    entries: list[tuple[Path, str, bool]] = []
    for path in paths:
        if path.is_symlink():
            raise ReleaseError(f"symlinks are not allowed in release payload: {path}")
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            raise ReleaseError(f"generated Python cache is not allowed in release payload: {path}")
        relative = path.relative_to(package_root.parent).as_posix()
        if path.is_dir():
            entries.append((path, relative + "/", True))
        elif path.is_file():
            entries.append((path, relative, False))
        else:
            raise ReleaseError(f"unsupported filesystem entry: {path}")
    yield from sorted(entries, key=lambda entry: (entry[1].rstrip("/"), not entry[2]))


def _archive_name(version_text: str, suffix: str) -> str:
    return f"{PACKAGE_DIR_NAME}-{version_text}{suffix}"


def build_zip(package_root: Path, destination: Path) -> None:
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path, archive_name, is_directory in _source_entries(package_root):
            info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = ((0o755 if is_directory else 0o644) & 0xFFFF) << 16
            if is_directory:
                info.external_attr |= 0x10
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, b"" if is_directory else path.read_bytes())


def _safe_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ReleaseError(f"unsafe archive member: {name}")
    if not (normalized == PACKAGE_DIR_NAME or normalized.startswith(PACKAGE_DIR_NAME + "/")):
        raise ReleaseError(f"archive contains a member outside {PACKAGE_DIR_NAME}/: {name}")
    return normalized


def _verify_member_names(names: Iterable[str]) -> list[str]:
    normalized = [_safe_member_name(name) for name in names]
    if not normalized:
        raise ReleaseError("archive is empty")
    if any(
        name in {f"{PACKAGE_DIR_NAME}/README.md", f"{PACKAGE_DIR_NAME}/illustration.png"}
        for name in normalized
    ):
        raise ReleaseError("repository presentation files must not be packaged")
    required = {
        f"{PACKAGE_DIR_NAME}/{VERSION_FILE}",
        f"{PACKAGE_DIR_NAME}/{USER_AGENTS_FILE}",
        f"{PACKAGE_DIR_NAME}/bootstrap.md",
        f"{PACKAGE_DIR_NAME}/install.md",
        f"{PACKAGE_DIR_NAME}/update.md",
        f"{PACKAGE_DIR_NAME}/check_update.md",
        f"{PACKAGE_DIR_NAME}/remove.md",
        f"{PACKAGE_DIR_NAME}/enable_auto_check_update.md",
        f"{PACKAGE_DIR_NAME}/enable_auto_update.md",
        f"{PACKAGE_DIR_NAME}/disable_auto_update.md",
        f"{PACKAGE_DIR_NAME}/disable_auto_check_update.md",
        f"{PACKAGE_DIR_NAME}/companion.md",
        f"{PACKAGE_DIR_NAME}/closure_steward.md",
        f"{PACKAGE_DIR_NAME}/investigation_team.md",
        f"{PACKAGE_DIR_NAME}/workflow.py",
        f"{PACKAGE_DIR_NAME}/runtime/__init__.py",
        f"{PACKAGE_DIR_NAME}/runtime/_toml.py",
        f"{PACKAGE_DIR_NAME}/runtime/backup.py",
        f"{PACKAGE_DIR_NAME}/runtime/errors.py",
        f"{PACKAGE_DIR_NAME}/runtime/layout.py",
        f"{PACKAGE_DIR_NAME}/runtime/lifecycle.py",
        f"{PACKAGE_DIR_NAME}/runtime/markers.py",
        f"{PACKAGE_DIR_NAME}/runtime/platform_settings.py",
        f"{PACKAGE_DIR_NAME}/runtime/personalization.py",
        f"{PACKAGE_DIR_NAME}/runtime/plan.py",
        f"{PACKAGE_DIR_NAME}/runtime/project_ops.py",
        f"{PACKAGE_DIR_NAME}/runtime/release.py",
        f"{PACKAGE_DIR_NAME}/runtime/runtime_ops.py",
        f"{PACKAGE_DIR_NAME}/runtime/transaction.py",
        f"{PACKAGE_DIR_NAME}/resources/personalization.md",
        f"{PACKAGE_DIR_NAME}/resources/auto_check_update.md",
    }
    required.update(
        f"{PACKAGE_DIR_NAME}/agents/{worker}.toml" for worker in BUILTIN_WORKERS
    )
    missing = sorted(required.difference(normalized))
    if missing:
        raise ReleaseError("archive is missing: " + ", ".join(missing))
    retired_workers = {
        f"{PACKAGE_DIR_NAME}/agents/executor_luna.toml",
        f"{PACKAGE_DIR_NAME}/agents/executor_sol.toml",
        f"{PACKAGE_DIR_NAME}/agents/executor_terra.toml",
        f"{PACKAGE_DIR_NAME}/agents/explorer.toml",
        f"{PACKAGE_DIR_NAME}/agents/end_of_session.toml",
    }
    present_retired = sorted(retired_workers.intersection(normalized))
    if present_retired:
        raise ReleaseError(
            "archive contains retired worker roles: " + ", ".join(present_retired)
        )
    expected_workers = {
        f"{PACKAGE_DIR_NAME}/agents/{worker}.toml" for worker in BUILTIN_WORKERS
    }
    present_workers = {
        name
        for name in normalized
        if name.startswith(f"{PACKAGE_DIR_NAME}/agents/")
        and name.endswith(".toml")
    }
    unexpected_workers = sorted(present_workers - expected_workers)
    if unexpected_workers:
        raise ReleaseError(
            "archive contains unsupported worker roles: "
            + ", ".join(unexpected_workers)
        )
    return normalized


def verify_archive(archive_path: Path, expected_version: SemVer | None = None) -> str:
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            names = _verify_member_names(member.filename for member in members)
            if len(names) != len(set(names)):
                raise ReleaseError("archive contains duplicate members")
            version_text = archive.read(f"{PACKAGE_DIR_NAME}/{VERSION_FILE}").decode(
                "utf-8"
            ).strip()
            user_agents = archive.read(f"{PACKAGE_DIR_NAME}/{USER_AGENTS_FILE}").decode(
                "utf-8"
            )
            _validate_user_agents_text(user_agents, version_text)
            with tempfile.TemporaryDirectory(prefix="codex-workflow-verify-") as temporary:
                extraction = Path(temporary)
                archive.extractall(extraction)
                _validate_runtime(extraction / PACKAGE_DIR_NAME)
    else:
        raise ReleaseError(f"unsupported archive type: {archive_path}")

    version = parse_semver(version_text)
    if expected_version is not None and str(version) != str(expected_version):
        raise ReleaseError(
            f"{archive_path} contains {version}, expected {expected_version}"
        )
    marker = VERSION_MARKER.search(user_agents)
    if marker is None or marker.group(1).removeprefix("v") != version_text:
        raise ReleaseError(f"archive metadata version mismatch: {archive_path}")
    return version_text


def write_checksums(archives: Iterable[Path], destination: Path) -> None:
    lines = []
    for archive in sorted(archives, key=lambda path: path.name):
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        lines.append(f"{digest}  {archive.name}")
    destination.write_text("\n".join(lines) + "\n", encoding="ascii")


def build_release(
    package_root: Path,
    output_dir: Path,
    release_tag: str | None,
    requested_version: str | None,
) -> list[Path]:
    version_text, version = validate_source(package_root)
    if (
        requested_version is not None
        and str(parse_semver(requested_version, allow_v=True)) != version_text
    ):
        raise ReleaseError(
            f"requested version {requested_version} does not match {version_text}"
        )
    if (
        release_tag is not None
        and str(parse_semver(release_tag, allow_v=True)) != version_text
    ):
        raise ReleaseError(f"release tag {release_tag} does not match {version_text}")

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / _archive_name(version_text, ".zip")
    build_zip(package_root, destination)
    verify_archive(destination, version)
    archives = [destination]
    write_checksums(archives, output_dir / "SHA256SUMS")
    return archives


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=repository_root() / "dist", help="asset directory"
    )
    parser.add_argument("--release-tag", help="validate a release tag such as v1.1.4")
    parser.add_argument("--version", help="validate an expected package version")
    parser.add_argument(
        "--verify",
        nargs="+",
        type=Path,
        metavar="ARCHIVE",
        help="validate existing release archives instead of building them",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        package_root = repository_root() / PACKAGE_DIR_NAME
        if args.verify:
            expected = parse_semver(args.version, allow_v=True) if args.version else None
            for archive in args.verify:
                version = verify_archive(archive, expected)
                print(f"verified {archive} ({version})")
            return 0

        archives = build_release(
            package_root,
            args.output_dir,
            args.release_tag,
            args.version,
        )
        print(f"built {len(archives)} release archives for {read_source_version(package_root)[0]}")
        for archive in archives:
            print(archive)
        print(args.output_dir / "SHA256SUMS")
        return 0
    except (OSError, ReleaseError, zipfile.BadZipFile) as error:
        print(f"release packaging failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
