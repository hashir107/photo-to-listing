# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-21

### Added
- `reloop` Agent Skill (display name ReLoop). It turns item photos and an optional note into
  structured resale metadata, German Kleinanzeigen-style listing copy and an English version,
  and refines the result through multi-turn clarification.
- Versioned JSON Schema (`schema.json`, schema version 0.1.0, JSON Schema 2020-12).
- Reference rules for extraction, evidence, null semantics and listing copy.
- Nine text-based behavioural fixtures with schema-valid expected outputs.
- Standard-library validation (`scripts/validate.py`) and reproducible release build
  (`scripts/build_releases.py`) with unit tests.
- Release packages: Claude custom-skill ZIP, Codex local marketplace plus Agent Plugins
  package, and Claude Code local marketplace plus plugin, with `SHA256SUMS.txt`.
- GitHub Actions workflow that validates, tests and builds artifacts without publishing.
