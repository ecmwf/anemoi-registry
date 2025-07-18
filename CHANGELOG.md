# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Please add your functional changes to the appropriate section in the PR.
Keep it human-readable, your future self will thank you!

## [0.2.2](https://github.com/ecmwf/anemoi-registry/compare/0.2.1...0.2.2) (2025-06-30)


### Features

* Add trainings subcommand ([#70](https://github.com/ecmwf/anemoi-registry/issues/70)) ([1f92d0b](https://github.com/ecmwf/anemoi-registry/commit/1f92d0b9965588823aea940ff055e26001efd637))
* Implement worker to delete datasets on s3 ([#85](https://github.com/ecmwf/anemoi-registry/issues/85)) ([8de1f71](https://github.com/ecmwf/anemoi-registry/commit/8de1f710bae2abed017e1e9b9ed51affb4c27587))
* Simplify getting settings from catalogue ([#81](https://github.com/ecmwf/anemoi-registry/issues/81)) ([cada143](https://github.com/ecmwf/anemoi-registry/commit/cada143bb61e9c806c8e9100074adda860a0d994))
* Transfering datasets improvement ([#93](https://github.com/ecmwf/anemoi-registry/issues/93)) ([c33330e](https://github.com/ecmwf/anemoi-registry/commit/c33330e61536b0d6146cb727c6418a8d2318a8f9))
* Use settings from server ([#77](https://github.com/ecmwf/anemoi-registry/issues/77)) ([1633674](https://github.com/ecmwf/anemoi-registry/commit/1633674ce4004098618c32ffcbdc7c916cccbce2))


### Bug Fixes

* Datasets deletion improvement ([#94](https://github.com/ecmwf/anemoi-registry/issues/94)) ([50700b6](https://github.com/ecmwf/anemoi-registry/commit/50700b6f82fc8f1761bad7edebb98d6924afe8f9))
* Fix deleting datasets ([#95](https://github.com/ecmwf/anemoi-registry/issues/95)) ([64e70c8](https://github.com/ecmwf/anemoi-registry/commit/64e70c800dd2bcff78b83e01ff536040493aca78))


### Documentation

* Minor updates ([#83](https://github.com/ecmwf/anemoi-registry/issues/83)) ([ffeabc5](https://github.com/ecmwf/anemoi-registry/commit/ffeabc5f8cae118daf6ff8057dfca5b3e2846159))

## [0.2.1](https://github.com/ecmwf/anemoi-registry/compare/0.2.0...0.2.1) (2025-05-20)


### Features

* use latest version of anemoi-datasets ([#76](https://github.com/ecmwf/anemoi-registry/issues/76)) ([aa4ab87](https://github.com/ecmwf/anemoi-registry/commit/aa4ab87486381ba4d8fcc56d15c94d87adcb729d))


### Bug Fixes

* remove pinning on botocore and update anemoi-utils ([7665a23](https://github.com/ecmwf/anemoi-registry/commit/7665a23112e61f91aed0e657aab37146967dc40a))

## [0.2.0](https://github.com/ecmwf/anemoi-registry/compare/0.1.8...0.2.0) (2025-04-10)


### Features

* add robust connection to server ([#66](https://github.com/ecmwf/anemoi-registry/issues/66)) ([c0f735c](https://github.com/ecmwf/anemoi-registry/commit/c0f735ccf132e924c476539e3ae808575c60c324))
* adding set-get-remove metadata ([#63](https://github.com/ecmwf/anemoi-registry/issues/63)) ([15633fe](https://github.com/ecmwf/anemoi-registry/commit/15633feb2bf9664b64026729aa763c666991c6e3))


### Documentation

* new logo ([#69](https://github.com/ecmwf/anemoi-registry/issues/69)) ([4e40632](https://github.com/ecmwf/anemoi-registry/commit/4e406322e3a74bb9263fb791523b41fce10508ac))


### Miscellaneous Chores

* Manual version bump ([c2f0b8f](https://github.com/ecmwf/anemoi-registry/commit/c2f0b8f26deb089385df8ba5b35cc5b69ea06ffa))

## [0.1.8](https://github.com/ecmwf/anemoi-registry/compare/0.1.7...0.1.8) (2025-03-04)


### Features

* better dataset deletion ([#49](https://github.com/ecmwf/anemoi-registry/issues/49)) ([449bf8c](https://github.com/ecmwf/anemoi-registry/commit/449bf8ca9156f7f6538ff3d0c26a9a72b8143f6f))
* fix readthedoc ([#59](https://github.com/ecmwf/anemoi-registry/issues/59)) ([27b5661](https://github.com/ecmwf/anemoi-registry/commit/27b5661ab75b308ccc6ac46e2ae444fac6bbdc84))
* pin boto3 before 1.36 ([#61](https://github.com/ecmwf/anemoi-registry/issues/61)) ([42d4832](https://github.com/ecmwf/anemoi-registry/commit/42d48320857114d0eabba0519261295b09da3ac1))
* self timeout for workers ([#53](https://github.com/ecmwf/anemoi-registry/issues/53)) ([377d9ef](https://github.com/ecmwf/anemoi-registry/commit/377d9ef1f27b76cb524e60f11c746a254f14a1e6))


### Documentation

* use new logo ([#51](https://github.com/ecmwf/anemoi-registry/issues/51)) ([1641b5a](https://github.com/ecmwf/anemoi-registry/commit/1641b5ac8a36bcd1ff8ea01df65a1804a56f9deb))

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
