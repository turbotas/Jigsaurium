# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initialized changelog for public release process tracking.
- Each promotion to prod attaches an SBOM report and a CycloneDX SBOM of the prod image to its GitHub Release (issue #107).
- Old container images are deleted weekly, keeping the last 5 that reached prod and the last 5 that reached test (issue #109).

### Changed

- Jigsaurium now uses the Lexend typeface instead of GOV.UK's GDS Transport (issue #85).

## [v0.1.0] - 2026-11-06

### Added

- Initial public-release preparation baseline (security/license/docs/quick-start hardening).
