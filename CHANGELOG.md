# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Please add your functional changes to the appropriate section in the PR.
Keep it human-readable, your future self will thank you!

## 0.1.7 (2025-02-04)

<!-- Release notes generated using configuration in .github/release.yml at main -->

## What's Changed
### Other Changes 🔗
* feat: accept-datasets-with-no-statistics by @floriankrb in https://github.com/ecmwf/anemoi-registry/pull/41
* chore: synced file(s) with ecmwf-actions/reusable-workflows by @DeployDuck in https://github.com/ecmwf/anemoi-registry/pull/40

## New Contributors
* @DeployDuck made their first contribution in https://github.com/ecmwf/anemoi-registry/pull/40

**Full Changelog**: https://github.com/ecmwf/anemoi-registry/compare/0.1.6...0.1.7

## [Unreleased]

### Added

- Add anemoi-transform link to documentation
- CI workflows to check for updates in the changelog and the documentation.
- Support for "anemoi-datasets publish"
- Added set from file (python only)
- Added 'update' command
- Force full paths when registering
- Added naming conventions
- Fix docstring errors
- Fix import errors [#18](https://github.com/ecmwf/anemoi-registry/pull/18)
- Remove usage of obsolete upload function from anemoi-utils.
- Add worker to updated datsets.

### Changed
- Replaces the deploy workflow with cd-pypi
- Update copyright notice
- Fix `__version__` import in init

### Removed

## [0.1.0] Minor Release

### Added
- Implementation of follwoing commands upload (to S3), download

## [0.0.1] Initial Release

### Added
- Documentation
- Initial code release for anemoi-registry: Cataloguing for model checkpoints and datasets


## Git Diffs:
[0.1.0]: https://github.com/ecmwf/anemoi-registry/compare/0.0.1...0.1.0
[0.0.1]: https://github.com/ecmwf/anemoi-registry/releases/tag/0.0.1
