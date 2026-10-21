# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-10-21

### Added
- **Price suggestions**, which is a deliberate scope change: v0.1.0 and v0.2.0 excluded pricing.
  A new required `price_estimate` field holds the range, suggested value, scope
  (single item / per unit / lot), optional lot total, `basis` and assumptions.
  Three bases, in order of preference, are described in `references/pricing.md`:
  - prices the user pasted from comparable listings,
  - a cited current new price minus documented depreciation bands,
  - a labelled "ungeprüft (Modellwissen)" fallback range.

  ReLoop never fetches or scrapes Kleinanzeigen or eBay pages.
- Validator rules: `low <= suggested <= high`; the basis must match its evidence (a cited
  URL, a user statement or a tentative inference); no price while the item type is unknown.
- New fixture `price-from-comparables`, plus price tests (59 tests in total).

### Changed
- Section B is a single table: Titel, Kategorie, Eigenschaften und Versand, Beschreibung,
  Preis (Vorschlag), Title (EN), Description (EN). The title and description are inside
  the table, with `<br>` line breaks. The Gebot/Gesuch, Bilder and Ort/Name rows are removed.
- Photo cleanup hints, such as covering a serial number, moved to one "Hinweis zu Fotos"
  line under section A.
- Schema 0.3.0.
- Validation and test runs showed two problems, now fixed. A `model_knowledge` price may now cite pages that
  show no current new price, and `pricing.md` requires any lot total shown in the
  table to match `lot_total_suggested`.

## [0.2.0] - 2026-10-21

### Changed
- Section B of the default output is now **Kleinanzeigen-Formular**. It follows the field
  order of Kleinanzeigen's "Anzeige aufgeben" form: Gebot/Gesuch, Bilder, Titel, Kategorie,
  Eigenschaften und Versand, Beschreibung, Preis, Ort/Name. Title and description come as
  copy blocks, and the English version follows. Price, location and name are always left
  for the user.
- Schema 0.2.0: `listing_title` is capped at 65 characters and `listing_description` at
  4000, matching the form's field limits.

### Added
- `photo_upload_order` (required): recommended upload order, cover first, with at most
  20 photos. Notes flag photos that need attention, such as "Seriennummer abdecken".
- A form map in `references/kleinanzeigen-copy.md`, plus validator checks and tests for
  the new limits and upload-order integrity.

### Fixed
- The secrets and private-files check now scans only files Git could commit, so
  `.gitignore`d OS files such as `.DS_Store` no longer cause false failures.

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
