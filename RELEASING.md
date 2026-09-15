# Release Process

This repository publishes the workflow as GitHub Release assets. The release
payload is intentionally independent of the repository presentation and
development files.

## Repository and asset layout

The repository-only release machinery is:

```text
.github/workflows/release.yml
scripts/package_release.py
RELEASING.md
```

Every archive contains exactly this top-level directory and nothing beside it:

```text
codex_workflow/
├── AGENTS.md
├── operate/
│   ├── VERSION
│   ├── user_AGENTS.md
│   └── lifecycle guides
├── runtime/
│   ├── workflow.py
├── resources/                              # immutable package defaults
├── agents/
└── project_docs/
```

The package does not contain `README.md`, `illustration.png`,
`workflow_breakdown.md`, `RELEASING.md`, `.github/`, `scripts/`, `.git/`, or any
other repository-only file. All files below `codex_workflow/` are included so
the installed workflow remains self-contained.

Each GitHub Release publishes one universal asset for every supported operating
system:

- `codex_workflow-<version>.zip`;
- `SHA256SUMS` for the ZIP asset.

## Versioning

Use SemVer 2.0.0. Keep the plain version in
`codex_workflow/operate/VERSION` and the `codex-workflow-version` marker in
`codex_workflow/operate/user_AGENTS.md` identical.
The release tag is the same value with an optional leading `v`, for example
`VERSION=1.1.18` and tag `v1.1.18`. GitHub's prerelease flag is independent of
the SemVer string; the initial releases are marked as prereleases by the
workflow.
The command examples below use the current package version, `1.1.18`; replace
that value consistently when preparing a later release.

## Local build and validation

Run these commands from the repository root. The builder uses only Python's
standard library, requires Python 3.11 or newer, and works on Linux, macOS, and
Windows.

Linux/macOS:

```sh
python3 -B scripts/test_workflow_runtime.py -v
python3 -B scripts/test_deployment_token_report.py -v
python3 scripts/package_release.py --release-tag v1.1.18 --output-dir dist
python3 scripts/package_release.py --verify dist/codex_workflow-1.1.18.zip --version 1.1.18
```

Windows PowerShell:

```powershell
py -3.11 -B scripts\test_workflow_runtime.py -v
py -3.11 -B scripts\test_deployment_token_report.py -v
py -3.11 scripts/package_release.py --release-tag v1.1.18 --output-dir dist
py -3.11 scripts/package_release.py --verify dist\codex_workflow-1.1.18.zip --version 1.1.18
```

The build validates the version, marker, lifecycle runtime, and required
resources; rejects generated Python caches; creates a deterministic ZIP asset;
and writes `dist/SHA256SUMS`. Run the runtime tests before packaging and inspect
the archive listing when package contents change.

## Publishing — approval required

Do not run the following commands until the release structure, contents, tag,
and prerelease setting have been approved:

```sh
git status --short
git tag -a v1.1.18 -m "codex_workflow v1.1.18"
git push origin v1.1.18
```

Pushing a semantic `v*` tag starts `.github/workflows/release.yml`. It rebuilds
and validates the archives from that tagged commit, then publishes the GitHub
Release with `--prerelease` and generated notes. The workflow also supports a
manual dispatch with a tag; manual runs check out that tag before packaging and
publish against the checked-out commit. Manual dispatch defaults to prerelease
publication. The prerelease flag should be removed or disabled only after a
separate decision to promote the project to stable releases.

If the workflow is unavailable, the equivalent manual publication command is:

```sh
gh release create v1.1.18 \
  dist/codex_workflow-1.1.18.zip \
  dist/SHA256SUMS \
  --title "codex_workflow v1.1.18" \
  --generate-notes \
  --prerelease
```

The manual command is also approval-gated and must use assets built from the
same tagged commit.

## Consumer commands

- Initial installation reads the extracted release package's
  `codex_workflow/operate/bootstrap.md`; the bundled lifecycle CLI validates and
  applies the user-level bootstrap transaction directly.
- `codex_workflow --install` reads the installed `operate/install.md` and creates only
  project-level workflow assets from the existing bootstrap.
- `codex_workflow --check-update` explicitly checks GitHub Releases without
  downloading or installing an update.
- `codex_workflow --update` selects the latest appropriate ZIP asset, downloads
  it from its GitHub Release URL, verifies it, reads the incoming package's
  `operate/update.md`, and follows that package's update procedure for the
  shared runtime and all registered projects. It never clones the repository.
- `codex_workflow --remove` first displays a destructive dry-run summary and
  requires one explicit second confirmation before deleting workflow-owned
  files.
