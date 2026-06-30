# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-30

### Added
- GitHub actions CI workflows for automated linting and unit testing.
- Community templates: `CODEOWNERS`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`.
- Structured issue templates for bug reporting and feature requests.
- MIT open source software `LICENSE`.

### Changed
- Refactored entire Python codebase to integrate standardized hierarchical `logging` instead of raw print statement outputs.
- Enhanced type coverage (type hinting annotations) across all core module interfaces, specialist agents, and utilities.
- Upgraded documentation across the code with comprehensive Google/Sphinx style docstrings and code block explanations.
- Reorganized file architecture: moved test scripts from root to `tests/`, moved text briefs to `examples/output/`, and moved bug reports to `docs/`.

### Fixed
- Added a robust fallback mechanism to `ShortTermMemory` using an in-memory dictionary cache in the event that the Redis database server is offline.
