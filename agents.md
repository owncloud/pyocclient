# agents.md -- pyocclient

## Repository Overview

Archived/legacy Python client library for the ownCloud API. Licensed under MIT. Provides file, share, user, and group operations.

## Architecture & Key Paths

- `owncloud/` -- Python package source
- `docs/` -- Documentation
- `setup.py` -- Package setup
- `setup.cfg` -- Package configuration
- `runtests.sh` -- Test runner script
- `CHANGES.rst` -- Changelog
- `CONTRIBUTORS.rst` -- Contributors list

## Development Conventions

- Python package with setup.py
- reStructuredText documentation

## Build & Test Commands

```bash
pip install -e .              # Install in development mode
bash runtests.sh              # Run tests
```

## Important Constraints

- Licensed under MIT. The OSPO target is Apache 2.0.
- Do not introduce new **copyleft-licensed dependencies** (GPL, AGPL, LGPL, MPL) without explicit discussion in an issue first. This is especially important for repos that are migrating to or already under Apache 2.0, as copyleft dependencies would block or complicate that migration.
- Archived/legacy -- no longer actively maintained.
- Supports ownCloud 8.2, 9.0, 9.1 and newer (classic server).
- All contributions require a DCO sign-off.


## OSPO Policy Constraints

### GitHub Actions
- **Only** use actions owned by `owncloud`, created by GitHub (`actions/*`), verified on the GitHub Marketplace, or verified by the ownCloud Maintainers.
- Pin all actions to their full commit SHA (not tags): `uses: actions/checkout@<SHA> # vX.Y.Z`
- Never introduce actions from unverified third parties.

### Dependency Management
- Dependabot is configured for automated dependency updates.
- Review and merge Dependabot PRs as part of regular maintenance.
- Do not introduce new dependencies without discussion in an issue first.

### Git Workflow
- **Rebase policy**: Always rebase; never create merge commits. Use `git pull --rebase` and `git rebase` before pushing.
- **Signed commits**: All commits **must** be PGP/GPG signed (`git commit -S -s`).
- **DCO sign-off**: Every commit needs a `Signed-off-by` line (`git commit -s`).
- **Conventional Commits & Squash Merge**: Use the [Conventional Commits](https://www.conventionalcommits.org/) format where the repository enforces it. Many repos use squash merge, where the PR title becomes the commit message on the default branch — apply Conventional Commits format to PR titles as well. A reusable GitHub Actions workflow enforces this.

## Context for AI Agents

This is a pure Python library with no C extensions. It abstracts HTTP and WebDAV calls for ownCloud server operations. The `owncloud/` directory contains the client implementation. This library is for the classic ownCloud server, not oCIS.
